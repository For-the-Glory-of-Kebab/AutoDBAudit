"""
Handles revert flows and script construction for PS remoting changes.
"""
# pylint: disable=line-too-long

from typing import Dict, Any
import subprocess
import time

from ..models import PSRemotingResult
from ..credentials import CredentialHandler
from ..config.client_config import ClientConfigurator


class RevertService:
    """Build and execute revert scripts for PS remoting changes."""

    def __init__(
        self,
        credential_handler: CredentialHandler,
        client_config: ClientConfigurator,
        is_windows: bool,
        exec_with_creds,
    ):
        self.credential_handler = credential_handler
        self.client_config = client_config
        self._is_windows = is_windows
        self._exec_with_creds = exec_with_creds

    def revert_server(
        self,
        server_name: str,
        credentials: Dict[str, Any],
        dry_run: bool = False,
    ) -> PSRemotingResult:
        """Revert PS remoting changes on a target server."""
        start_time = time.time()
        if not self._is_windows:
            return PSRemotingResult(
                success=False,
                session=None,
                error_message="Revert supported on Windows clients only",
                attempts_made=[],
                duration_ms=int((time.time() - start_time) * 1000),
                troubleshooting_report=None,
                manual_setup_scripts=None,
                revert_scripts=[],
            )

        bundle = self.credential_handler.prepare_credentials(credentials)
        revert_script = self._build_revert_script(server_name)
        client_cleanup = self.client_config.cleanup_trustedhosts(server_name)
        scripts = [revert_script, client_cleanup]

        if dry_run:
            return PSRemotingResult(
                success=True,
                session=None,
                error_message=None,
                attempts_made=[],
                duration_ms=int((time.time() - start_time) * 1000),
                troubleshooting_report=None,
                manual_setup_scripts=None,
                revert_scripts=scripts,
            )

        try:
            result = self._exec_with_creds(revert_script, bundle)
            client_result = subprocess.run(
                ["powershell", "-Command", client_cleanup],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )

            success = result.returncode == 0 and client_result.returncode == 0
            error = None
            if not success:
                error = "\n".join([result.stderr or "", client_result.stderr or ""]).strip()

            return PSRemotingResult(
                success=success,
                session=None,
                error_message=error if not success else None,
                attempts_made=[],
                duration_ms=int((time.time() - start_time) * 1000),
                troubleshooting_report=None,
                manual_setup_scripts=None,
                revert_scripts=scripts,
            )
        except Exception as exc:  # pylint: disable=broad-except
            return PSRemotingResult(
                success=False,
                session=None,
                error_message=str(exc),
                attempts_made=[],
                duration_ms=int((time.time() - start_time) * 1000),
                troubleshooting_report=None,
                manual_setup_scripts=None,
                revert_scripts=scripts,
            )

    @staticmethod
    def _build_revert_script(server_name: str) -> str:
        """PowerShell script to revert target-side changes."""
        return f"""
        Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{
            Write-Host "Reverting WinRM configuration on {server_name}"

            # Stop and disable WinRM service
            Stop-Service -Name WinRM -ErrorAction SilentlyContinue
            Set-Service -Name WinRM -StartupType Manual -ErrorAction SilentlyContinue

            # Remove WinRM firewall rules
            Get-NetFirewallRule -Name "WINRM-HTTP-In-TCP" -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
            Get-NetFirewallRule -Name "WINRM-HTTPS-In-TCP" -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue

            # Remove registry overrides if present
            Remove-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" -Name "LocalAccountTokenFilterPolicy" -ErrorAction SilentlyContinue
            Remove-ItemProperty -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa" -Name "DisableLoopbackCheck" -ErrorAction SilentlyContinue

            Write-Host "Revert complete on {server_name}"
        }}
        """
