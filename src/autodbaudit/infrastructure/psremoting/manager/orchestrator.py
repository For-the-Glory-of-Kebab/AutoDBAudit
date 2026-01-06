"""
PS Remoting Connection Orchestrator.

Thin facade wiring dependencies and delegating to ConnectionFlow and RevertService.
"""

import logging
import platform
import subprocess
from typing import Optional, Dict, Any

from ..config.client_config import ClientConfigurator
from ..config.target import TargetConfigurator
from ..layers.direct_runner import DirectAttemptRunner
from ..layers.layer2_client import ClientLayerRunner
from ..layers.layer3_target import TargetLayerRunner
from ..layers.revert_tracker import RevertTracker
from ..models import PSRemotingResult, CredentialBundle
from ..credentials import CredentialHandler
from ..repository import PSRemotingRepository
from ..elevation import ShellElevationService
from ..layers.localhost_prep import LocalhostPreparer
from ..layers.direct.utils import is_ip_address
from .revert_service import RevertService
from .connect_flow import ConnectionFlow

logger = logging.getLogger(__name__)


class PSRemotingConnectionManager:  # pylint: disable=too-many-instance-attributes
    """Comprehensive PS remoting connection manager facade."""

    def __init__(self, repository: Optional[PSRemotingRepository] = None):
        self.repository: PSRemotingRepository = repository or PSRemotingRepository()
        self.credential_handler: CredentialHandler = CredentialHandler()
        self.client_config: ClientConfigurator = ClientConfigurator()
        self.target_config: TargetConfigurator = TargetConfigurator()
        self._is_windows = platform.system() == "Windows"
        self.revert_tracker: RevertTracker = RevertTracker(self._get_timestamp)
        self.direct_runner: DirectAttemptRunner = DirectAttemptRunner(
            self.credential_handler,
            self._get_timestamp,
            self._is_windows,
        )
        self.client_layer: ClientLayerRunner = ClientLayerRunner(
            self.client_config,
            self.direct_runner,
            self._is_windows,
            self.revert_tracker.add_revert_script,
        )
        self.target_layer: TargetLayerRunner = TargetLayerRunner(
            self.target_config,
            self.revert_tracker,
            self.direct_runner,
            is_ip_address,
            self._has_admin_credentials,
            self._execute_ps_command_with_creds,
        )
        self._elevation_service = ShellElevationService()
        self.localhost_preparer = LocalhostPreparer(
            self._is_windows,
            self.direct_runner.layer1_direct_attempts,
            self._get_timestamp,
            self.repository,
            lambda: self.revert_tracker.scripts,
        )
        self.revert_service = RevertService(
            self.credential_handler,
            self.client_config,
            self._is_windows,
            self._execute_ps_command_with_creds,
        )
        self.flow = ConnectionFlow(
            self.repository,
            self.credential_handler,
            self.client_config,
            self.target_config,
            self.direct_runner,
            self.client_layer,
            self.target_layer,
            self.revert_tracker,
            self.localhost_preparer,
            self._elevation_service,
            self._get_timestamp,
            self._is_windows,
        )

    def connect_to_server(
        self, server_name: str, credentials: Dict[str, Any], allow_config: bool = True
    ) -> PSRemotingResult:
        """Delegate to the connection flow orchestrator."""
        return self.flow.connect_to_server(server_name, credentials, allow_config)

    def revert_server(
        self, server_name: str, credentials: Dict[str, Any], dry_run: bool = False
    ) -> PSRemotingResult:
        """Delegate revert to the revert service."""
        return self.revert_service.revert_server(server_name, credentials, dry_run)

    def test_connection(self, server_name: str, credentials: Dict[str, Any]) -> bool:
        """Quick test if connection is possible without making config changes."""
        result = self.connect_to_server(server_name, credentials, allow_config=False)
        return result.is_success()

    def _execute_ps_command_with_creds(
        self, script: str, bundle: CredentialBundle
    ) -> subprocess.CompletedProcess:
        """Execute PowerShell command with credentials."""
        ps_cred = self.credential_handler.create_pscredential(bundle)
        if ps_cred:
            script = script.replace("(Get-Credential)", f"({ps_cred})")

        return subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
        )

    @staticmethod
    def _has_admin_credentials(bundle: CredentialBundle) -> bool:
        """Simple admin heuristic: credentials are present."""
        if bundle.windows_explicit:
            username = bundle.windows_explicit.get("username")
            password = bundle.windows_explicit.get("password")
            return bool(username and password)
        return False

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime  # pylint: disable=import-outside-toplevel

        return datetime.now().isoformat()
