"""
Connection flow orchestrator for PS remoting.

Handles the layered strategy (direct, client config, target config, fallbacks, manual)
using injected dependencies so files stay small and responsibilities clear.
"""

import time
import logging
from typing import List, Dict, Any

from ..models import ConnectionAttempt, PSRemotingResult, CredentialBundle
from ..layers.revert_tracker import RevertTracker
from ..layers.manual_layer import run_manual_layer
from ..layers.localhost_prep import LocalhostPreparer
from ..credentials import CredentialHandler
from ..repository import PSRemotingRepository
from ..layers.direct_runner import DirectAttemptRunner
from ..layers.layer2_client import ClientLayerRunner
from ..layers.layer3_target import TargetLayerRunner
from ..manager.profiles import (
    save_successful_profile,
    save_profile_from_attempt,
    try_stored_profile,
)
from ..manager.fallback_runner import run_advanced_fallbacks
from ..elevation import ShellElevationService
from ..config.client_config import ClientConfigurator
from ..config.target import TargetConfigurator

logger = logging.getLogger(__name__)
# pylint: disable=too-many-instance-attributes,too-many-branches,too-many-return-statements,line-too-long,too-many-arguments,too-many-positional-arguments


class ConnectionFlow:
    """Orchestrates the full layered connection strategy."""

    def __init__(
        self,
        repository: PSRemotingRepository,
        credential_handler: CredentialHandler,
        client_config: ClientConfigurator,
        target_config: TargetConfigurator,
        direct_runner: DirectAttemptRunner,
        client_layer: ClientLayerRunner,
        target_layer: TargetLayerRunner,
        revert_tracker: RevertTracker,
        localhost_preparer: LocalhostPreparer,
        elevation_service: ShellElevationService,
        timestamp_provider,
        is_windows: bool,
    ):
        self.repository = repository
        self.credential_handler = credential_handler
        self.client_config = client_config
        self.target_config = target_config
        self.direct_runner = direct_runner
        self.client_layer = client_layer
        self.target_layer = target_layer
        self.revert_tracker = revert_tracker
        self.localhost_preparer = localhost_preparer
        self._elevation_service = elevation_service
        self._timestamp = timestamp_provider
        self._is_windows = is_windows

    def connect_to_server(
        self, server_name: str, credentials: Dict[str, Any], allow_config: bool = True
    ) -> PSRemotingResult:
        """Establish PS remoting connection using the full layered strategy."""
        start_time = time.time()
        attempts: List[ConnectionAttempt] = []
        self.revert_tracker.reset()

        is_elevated = not self._is_windows or self._elevation_service.is_shell_elevated()
        allow_config_effective = allow_config and is_elevated
        if allow_config and not is_elevated:
            logger.warning(
                "Elevation required for configuration steps; proceeding with connection-only attempts."
            )

        credential_bundle = self.credential_handler.prepare_credentials(credentials)
        profile_id = self.repository.ensure_profile(server_name)

        if self._is_localhost(server_name):
            result = self.localhost_preparer.prepare_and_validate(
                server_name,
                credential_bundle,
                start_time,
                profile_id,
            )
            result.duration_ms = int((time.time() - start_time) * 1000)
            return result

        stored_profile = self.repository.get_connection_profile(server_name)
        if stored_profile:
            result = try_stored_profile(
                stored_profile,
                credential_bundle,
                attempts,
                profile_id,
                self.direct_runner,
                self.credential_handler,
                self._timestamp,
                self.revert_tracker.scripts,
            )
            if result.is_success():
                self.repository.log_attempts(attempts, profile_id=getattr(stored_profile, "id", None))
                result.duration_ms = int((time.time() - start_time) * 1000)
                return result

        result = self._layer1_direct_attempts(server_name, credential_bundle, attempts, profile_id)
        if result.is_success():
            self._persist_success(result, attempts, start_time)
            return result

        if self._is_ip_address(server_name):
            alt_host = self.direct_runner.reverse_dns(server_name)
            if alt_host is not None and alt_host.lower() != server_name.lower():
                logger.info(
                    "Reverse DNS resolved %s -> %s. Retrying direct attempts.",
                    server_name,
                    alt_host,
                )
                result = self._layer1_direct_attempts(
                    alt_host, credential_bundle, attempts, profile_id
                )
            if result.is_success():
                self._persist_success(result, attempts, start_time)
                return result

        if allow_config_effective:
            result = self._layer2_client_config(
                server_name, credential_bundle, attempts, profile_id
            )
            if result.is_success():
                self._persist_success(result, attempts, start_time)
                return result

        if allow_config_effective:
            result = self._layer3_target_config(
                server_name, credential_bundle, attempts, profile_id
            )
            if result.is_success():
                self._persist_success(result, attempts, start_time)
                return result

        if allow_config_effective:
            result = run_advanced_fallbacks(
                server_name,
                credential_bundle,
                attempts,
                self.credential_handler,
                self._timestamp,
                self.revert_tracker.scripts,
            )
            if result.is_success():
                self._persist_success(result, attempts, start_time, fallback_attempts=attempts)
                return result

        result = run_manual_layer(
            server_name, attempts, self._timestamp, self.revert_tracker.scripts
        )
        result.duration_ms = int((time.time() - start_time) * 1000)
        self.repository.log_attempts(attempts, profile_id=profile_id)
        return result

    def _persist_success(
        self,
        result: PSRemotingResult,
        attempts: List[ConnectionAttempt],
        start_time: float,
        fallback_attempts: List[ConnectionAttempt] | None = None,
    ) -> None:
        """Persist successful session or fallback attempt and log attempts."""
        session = result.get_session()
        if session:
            saved_id = save_successful_profile(
                session.connection_profile, self.repository, self._timestamp
            )
            self.repository.log_attempts(attempts, profile_id=saved_id)
        elif fallback_attempts:
            saved_id = save_profile_from_attempt(
                fallback_attempts[-1],
                None,
                fallback_attempts[-1].server_name or "",
                self.repository,
                self._timestamp,
            )
            self.repository.log_attempts(attempts, profile_id=saved_id)
        result.duration_ms = int((time.time() - start_time) * 1000)

    def _layer1_direct_attempts(
        self,
        server_name: str,
        bundle: CredentialBundle,
        attempts: List[ConnectionAttempt],
        profile_id: int,
    ) -> PSRemotingResult:
        """Layer 1: Try all possible direct connection methods."""
        return self.direct_runner.layer1_direct_attempts(server_name, bundle, attempts, profile_id)

    def _layer2_client_config(
        self,
        server_name: str,
        bundle: CredentialBundle,
        attempts: List[ConnectionAttempt],
        profile_id: int,
    ) -> PSRemotingResult:
        """Layer 2: Apply client-side configuration changes."""
        return self.client_layer.run(server_name, bundle, attempts, profile_id)

    def _layer3_target_config(
        self,
        server_name: str,
        bundle: CredentialBundle,
        attempts: List[ConnectionAttempt],
        profile_id: int,
    ) -> PSRemotingResult:
        """Layer 3: Comprehensive target server configuration."""
        logger.info("Layer 3: Configuring target server %s", server_name)
        return self.target_layer.run(server_name, bundle, attempts, profile_id)

    @staticmethod
    def _is_localhost(server_name: str) -> bool:
        """Determine if the target refers to localhost."""
        normalized = server_name.strip().lower()
        return normalized in {"localhost", "127.0.0.1", "::1"}

    @staticmethod
    def _is_ip_address(hostname: str) -> bool:
        """Check if hostname is an IP address."""
        try:
            import ipaddress  # pylint: disable=import-outside-toplevel
            ipaddress.ip_address(hostname)
            return True
        except ValueError:
            return False
