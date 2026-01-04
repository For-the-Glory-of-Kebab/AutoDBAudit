"""
Layer 2 client-side configuration runner for PS remoting.
"""

import logging
import subprocess
from typing import List, Callable

from ..models import ConnectionAttempt, PSRemotingResult
from .direct_runner import DirectAttemptRunner
from ..config.client_config import ClientConfigurator
from ..config.gpo_enforcer import apply_winrm_policy, build_revert_script

logger = logging.getLogger(__name__)


class ClientLayerRunner:
    """Handles client TrustedHosts and WinRM client tweaks before retrying direct attempts."""

    def __init__(
        self,
        client_config: ClientConfigurator,
        direct_runner: DirectAttemptRunner,
        is_windows: bool,
        record_revert: Callable[[str], None],
    ):
        self.client_config = client_config
        self.direct_runner = direct_runner
        self._is_windows = is_windows
        self._record_revert = record_revert

    def run(
        self,
        server_name: str,
        bundle,
        attempts: List[ConnectionAttempt],
        profile_id: int,
    ) -> PSRemotingResult:
        """Apply client configuration then retry direct connections."""
        if not self._is_windows:
            return PSRemotingResult(
                success=False,
                session=None,
                error_message="Layer 2: Client config only supported on Windows",
                attempts_made=attempts,
                duration_ms=0,
                troubleshooting_report=None,
                manual_setup_scripts=None,
                revert_scripts=None,
            )

        # Add to TrustedHosts, then retry direct attempts
        trusted_success, trusted_revert = self.client_config.add_to_trusted_hosts(server_name)
        if trusted_revert:
            self._record_revert(trusted_revert)
        if trusted_success:
            result = self.direct_runner.layer1_direct_attempts(
                server_name, bundle, attempts, profile_id
            )
            if result.is_success():
                return result

        # Configure WinRM client settings and policy, then retry direct attempts
        client_success, client_reverts = self.client_config.configure_winrm_client()
        for revert_script in client_reverts:
            self._record_revert(revert_script)
        policy_success, previous = apply_winrm_policy("localhost", self._run_local_ps)
        if policy_success:
            self._record_revert(build_revert_script("localhost", previous))

        if client_success:
            return self.direct_runner.layer1_direct_attempts(
                server_name, bundle, attempts, profile_id
            )
        return PSRemotingResult(
            success=False,
            session=None,
            error_message="Layer 2: Client configuration failed",
            attempts_made=attempts,
            duration_ms=0,
            troubleshooting_report=None,
            manual_setup_scripts=None,
            revert_scripts=None,
        )

    @staticmethod
    def _run_local_ps(script: str):
        """Run a PowerShell snippet locally and return CompletedProcess."""
        return subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
