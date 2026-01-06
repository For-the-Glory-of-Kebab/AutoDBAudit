"""
Direct connection attempt runner for PowerShell remoting.

Encapsulates Layer 1 direct connection attempts so the main connection manager
can stay focused on orchestration. All timing, attempt logging, and profile
construction live here.
"""

import time
import subprocess
import logging
from typing import List, Optional, Callable
import socket

from ..models import (
    AuthMethod,
    Protocol,
    ConnectionMethod,
    ConnectionProfile,
    ConnectionAttempt,
    PSSession,
    PSRemotingResult,
    CredentialBundle,
)
from ..credentials import CredentialHandler
from .direct import ConnectionPlan
from .direct.profile_builder import build_connection_profile
from .direct.executor import execute_connection_attempt
from .direct.utils import (
    auth_priority,
    credential_variants,
    enum_to_value,
    is_ip_address,
)

logger = logging.getLogger(__name__)
# pylint: disable=too-many-locals,too-many-arguments,too-many-positional-arguments,line-too-long


class DirectAttemptRunner:
    """Executes direct (Layer 1) PowerShell remoting attempts."""

    def __init__(
        self,
        credential_handler: CredentialHandler,
        timestamp_provider: Callable[[], str],
        is_windows: bool,
    ):
        self.credential_handler = credential_handler
        self._timestamp = timestamp_provider
        self._is_windows = is_windows

    def layer1_direct_attempts(
        self,
        server_name: str,
        bundle: CredentialBundle,
        attempts: List[ConnectionAttempt],
        profile_id: int,
    ) -> PSRemotingResult:
        """Try all direct connection permutations."""
        base_auth_methods = auth_priority()
        protocol_port_pairs = [
            (Protocol.HTTP, 5985),
            (Protocol.HTTPS, 5986),
        ]
        variants = credential_variants(bundle)
        if not variants:
            return PSRemotingResult(
                success=False,
                session=None,
                error_message="No usable credentials provided for PS remoting. Supply explicit Windows credentials.",
                attempts_made=attempts,
                duration_ms=0,
                troubleshooting_report=None,
                manual_setup_scripts=None,
                revert_scripts=None,
            )
        is_ip_target = is_ip_address(server_name)

        for auth_method in base_auth_methods:
            for protocol, port in protocol_port_pairs:
                for username, password in variants:
                    # Avoid credential-less attempts against IPs (NTLM/IP requires explicit creds)
                    if is_ip_target and not (username or bundle.windows_explicit):
                        continue
                    plan = ConnectionPlan(
                        server_name=server_name,
                        auth_method=auth_method,
                        protocol=protocol,
                        port=port,
                    )
                    result = self.try_single_connection(
                        plan, bundle, attempts, profile_id, username, password
                    )
                    if result.is_success():
                        return result

        return PSRemotingResult(
            success=False,
            session=None,
            error_message="Layer 1: All direct attempts failed",
            attempts_made=attempts,
            duration_ms=0,
            troubleshooting_report=None,
            manual_setup_scripts=None,
            revert_scripts=None,
        )

    def try_single_connection(
        self,
        plan: ConnectionPlan,
        bundle: CredentialBundle,
        attempts: List[ConnectionAttempt],
        profile_id: int,
        username_override: str | None = None,
        password_override: str | None = None,
    ) -> PSRemotingResult:
        """Try a single connection configuration."""
        username_variant = None
        if username_override:
            username_variant = username_override
        elif bundle.windows_explicit:
            username_variant = bundle.windows_explicit.get("username")

        attempt = ConnectionAttempt(
            profile_id=profile_id,
            server_name=plan.server_name,
            auth_method=enum_to_value(plan.auth_method),
            protocol=enum_to_value(plan.protocol),
            port=plan.port,
            credential_type=enum_to_value(self.credential_handler.get_credential_type(bundle)),
            error_message=None,
            attempted_at=self._timestamp(),
            attempt_timestamp=self._timestamp(),
            layer="direct",
            connection_method=ConnectionMethod.POWERSHELL_REMOTING,
            created_at=self._timestamp(),
            duration_ms=0,
            config_changes=None,
            rollback_actions=None,
            manual_script_path=None,
        )

        start_time = time.time()
        try:
            profile = build_connection_profile(plan, bundle, self.credential_handler)
            session = execute_connection_attempt(
                profile,
                bundle,
                self.credential_handler,
                self._timestamp,
                self._is_windows,
                username_override=username_override,
                password_override=password_override,
            )
            if session:
                attempt.duration_ms = int((time.time() - start_time) * 1000)
                attempt.success = True
                attempts.append(attempt)
                return PSRemotingResult(
                    success=True,
                    session=session,
                    error_message=None,
                    attempts_made=attempts,
                    duration_ms=attempt.duration_ms or 0,
                    troubleshooting_report=None,
                    manual_setup_scripts=None,
                    revert_scripts=None,
                    successful_permutations=[
                        {
                            "auth_method": attempt.auth_method,
                            "protocol": attempt.protocol,
                            "port": attempt.port,
                            "credential_type": attempt.credential_type,
                            "username_variant": username_variant,
                        }
                    ],
                )

        except Exception as exc:  # pylint: disable=broad-except
            attempt.error_message = str(exc)
            logger.debug("Direct attempt failed for %s: %s", plan.server_name, exc)

        attempt.duration_ms = int((time.time() - start_time) * 1000)
        attempts.append(attempt)

        return PSRemotingResult(
            success=False,
            session=None,
            error_message=attempt.error_message,
            attempts_made=attempts,
            duration_ms=attempt.duration_ms or 0,
            troubleshooting_report=None,
            manual_setup_scripts=None,
            revert_scripts=None,
        )

    def connect_with_profile(
        self, profile: ConnectionProfile, bundle: CredentialBundle
    ) -> Optional[PSSession]:
        """
        Execute a connection attempt using an existing profile.

        Exposed for callers that persist successful profiles and want to reuse
        them without rebuilding the command logic here.
        """
        return execute_connection_attempt(profile, bundle, self.credential_handler, self._timestamp, self._is_windows)

    @staticmethod
    def reverse_dns(hostname: str) -> Optional[str]:
        """Attempt reverse DNS lookup for an IP to retrieve a hostname."""
        try:
            return socket.gethostbyaddr(hostname)[0]
        except Exception:  # pylint: disable=broad-except
            return None
