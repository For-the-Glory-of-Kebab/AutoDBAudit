"""
Prepare Status Service

Provides a clean API for other layers (audit/remediation/sync) to:
- Query cached/persisted PS remoting availability for a server
- Trigger preparation and return a structured ServerConnectionInfo snapshot
"""

from typing import Optional, Dict, Any, List

from autodbaudit.domain.config import ServerConnectionInfo
from autodbaudit.domain.config.models.enums import ConnectionMethod, OSType
from autodbaudit.infrastructure.psremoting.connection_manager import (
    PSRemotingConnectionManager,
)
from autodbaudit.infrastructure.psremoting.repository import PSRemotingRepository
from autodbaudit.infrastructure.psremoting.models import PSRemotingResult, ConnectionProfile
from .cache.cache_manager import ConnectionCacheManager


class PrepareStatusService:
    """API surface for querying and refreshing PS remoting readiness."""

    def __init__(
        self,
        cache_manager: ConnectionCacheManager,
        ps_repo: PSRemotingRepository,
        connection_manager: PSRemotingConnectionManager,
    ) -> None:
        self.cache = cache_manager
        self.ps_repo = ps_repo
        self.connection_manager = connection_manager

    def get_status(self, server: str) -> Optional[ServerConnectionInfo]:
        """
        Fetch cached/persisted connection info for a server.

        Returns None if no information is available.
        """
        cached = self.cache.get(server)
        if cached:
            return cached

        profile = self.ps_repo.get_connection_profile(server)
        if profile:
            info = self._build_info_from_profile(profile)
            self.cache.put(server, info)
            return info

        return None

    def prepare_and_get(
        self,
        server: str,
        credentials: Dict[str, Any],
        allow_config: bool = True,
    ) -> ServerConnectionInfo:
        """
        Trigger preparation (full PS remoting flow) and return snapshot.
        """
        ps_result: PSRemotingResult = self.connection_manager.connect_to_server(
            server,
            credentials,
            allow_config=allow_config,
        )

        available_methods: List[ConnectionMethod] = []
        for attempt in ps_result.attempts_made:
            if attempt.success and attempt.connection_method:
                available_methods.append(self._map_method(attempt.connection_method))
        # Always include PS remoting if a session was established
        if ps_result.is_success() and ConnectionMethod.POWERSHELL_REMOTING not in available_methods:
            available_methods.append(ConnectionMethod.POWERSHELL_REMOTING)

        info = ServerConnectionInfo(
            server_name=server,
            os_type=OSType.UNKNOWN,  # OS detector can fill this separately
            available_methods=available_methods,
            preferred_method=available_methods[0] if available_methods else None,
            is_available=ps_result.is_success(),
            last_checked=self.connection_manager._get_timestamp(),  # noqa: SLF001
            connection_details={
                "ps_success": ps_result.is_success(),
                "ps_error": ps_result.error_message,
                "attempts": [a.model_dump() for a in ps_result.attempts_made],
            },
        )

        self.cache.put(server, info)
        return info

    @staticmethod
    def _build_info_from_profile(profile: ConnectionProfile) -> ServerConnectionInfo:
        """Construct a connection snapshot from a stored profile."""
        available_methods: List[ConnectionMethod] = []
        if profile.successful:
            available_methods.append(ConnectionMethod.POWERSHELL_REMOTING)

        return ServerConnectionInfo(
            server_name=profile.server_name,
            os_type=OSType.UNKNOWN,
            available_methods=available_methods,
            preferred_method=available_methods[0] if available_methods else None,
            is_available=profile.successful,
            last_checked=profile.last_successful_attempt or profile.last_attempt,
            connection_details={
                "protocol": profile.protocol,
                "port": profile.port,
                "auth_method": profile.auth_method,
            },
        )

    @staticmethod
    def _map_method(method) -> ConnectionMethod:
        """Map infra ConnectionMethod to domain enum."""
        try:
            return ConnectionMethod(method.value)  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover
            try:
                return ConnectionMethod(str(method))
            except Exception:
                return ConnectionMethod.POWERSHELL_REMOTING
