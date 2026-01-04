"""
PS Remoting Facade (orchestrator).

Provides a structured API for status/prepare/command execution/revert that
downstream modules (prepare/audit/remediate/sync/hotfix) can reuse.
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from autodbaudit.application.prepare.cache.cache_manager import ConnectionCacheManager
from autodbaudit.application.prepare.status_service import PrepareStatusService
from ..connection_manager import PSRemotingConnectionManager
from ..models import CommandResult, PSRemotingResult, ConnectionMethod
from ..repository import PSRemotingRepository
from .executor import CommandExecutor


class PSRemotingFacade:
    """
    Facade exposing:
    - get_status
    - ensure_prepared
    - run_command
    - run_script
    - revert
    """

    def __init__(
        self,
        connection_manager: Optional[PSRemotingConnectionManager] = None,
        status_service: Optional[PrepareStatusService] = None,
        repository: Optional[PSRemotingRepository] = None,
        executor: Optional[CommandExecutor] = None,
    ) -> None:
        self.connection_manager = connection_manager or PSRemotingConnectionManager()
        self.repository = repository or self.connection_manager.repository
        cache_manager = ConnectionCacheManager()
        self.status_service = status_service or PrepareStatusService(
            cache_manager=cache_manager,
            ps_repo=self.repository,
            connection_manager=self.connection_manager,
        )
        self.executor = executor or CommandExecutor(self.connection_manager, self.repository)

    def get_status(self, server: str):
        """Fetch cached/persisted status snapshot if available."""
        return self.status_service.get_status(server)

    def ensure_prepared(self, server: str, credentials: Dict[str, Any]):
        """Run the prepare flow (idempotent) and return a structured status snapshot."""
        return self.status_service.prepare_and_get(server, credentials, allow_config=True)

    def run_command(
        self,
        server: str,
        command: str,
        credentials: Dict[str, Any],
        prefer_method: Optional[ConnectionMethod] = None,
    ) -> CommandResult:
        """Execute a single PowerShell command on the target using the best available method."""
        return self.executor.run_command(server, command, credentials, prefer_method)

    def run_script(
        self,
        server: str,
        script: str,
        credentials: Dict[str, Any],
        prefer_method: Optional[ConnectionMethod] = None,
    ) -> CommandResult:
        """Execute a PowerShell script (inline content or file path) on the target."""
        return self.executor.run_script(server, script, credentials, prefer_method)

    def revert(
        self,
        server: str,
        credentials: Dict[str, Any],
        dry_run: bool = False
    ) -> PSRemotingResult:
        """Invoke the connection manager revert routine."""
        return self.connection_manager.revert_server(server, credentials, dry_run=dry_run)
