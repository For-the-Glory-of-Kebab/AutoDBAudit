"""
Client-side WinRM configuration helpers.
"""

import logging
import socket
import subprocess
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class ClientConfigurator:
    """Apply client-side WinRM settings and TrustedHosts changes."""

    def detect_client_ip(self) -> str:
        """
        Determine a suitable local IP without external connectivity.

        Uses hostname resolution fallback; returns 127.0.0.1 if unavailable.
        """
        try:
            hostname = socket.gethostname()
            ip_addr = socket.gethostbyname(hostname)
            return ip_addr
        except Exception:
            return "127.0.0.1"

    def add_to_trusted_hosts(self, server: str) -> Tuple[bool, Optional[str]]:
        """
        Add server to WinRM TrustedHosts and return a revert script restoring the prior list.

        Returns:
            (success, revert_script or None)
        """
        previous = self._read_value("WSMan:\\localhost\\Client\\TrustedHosts")
        command = (
            "Set-Item WSMan:\\localhost\\Client\\TrustedHosts "
            f"-Value '{server}' -Concatenate -Force"
        )
        success = self._run_command(command)
        revert_script = self._build_trustedhosts_revert(previous) if success else None
        return success, revert_script

    def configure_winrm_client(self) -> Tuple[bool, list[str]]:
        """
        Apply client WinRM settings and return revert scripts.

        Returns:
            (all_success, revert_scripts)
        """
        revert_scripts: list[str] = []
        prev_allow_unencrypted = self._read_value("WSMan:\\localhost\\Client\\AllowUnencrypted")
        prev_trusted = self._read_value("WSMan:\\localhost\\Client\\TrustedHosts")

        commands = [
            (
                "Set-Item -Path WSMan:\\localhost\\Client\\AllowUnencrypted "
                "-Value true -Force"
            ),
            (
                "Set-Item -Path WSMan:\\localhost\\Client\\TrustedHosts "
                "-Value * -Concatenate -Force"
            ),
        ]
        results = [self._run_command(cmd) for cmd in commands]

        if prev_allow_unencrypted is not None:
            revert_scripts.append(
                "Set-Item -Path WSMan:\\localhost\\Client\\AllowUnencrypted "
                f"-Value {prev_allow_unencrypted} -Force"
            )
        if prev_trusted is not None:
            revert_scripts.append(self._build_trustedhosts_revert(prev_trusted))

        return all(results), revert_scripts

    def cleanup_trustedhosts(self, server_name: str) -> str:
        """Build a PowerShell snippet to remove a server from TrustedHosts."""
        cleanup_parts = [
            "(Get-Item WSMan:\\localhost\\Client\\TrustedHosts).Value",
            "$hosts = ($current -split ',') | Where-Object { $_ -and $_ -ne '%s' }" % server_name,
            "Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value ($hosts -join ',') -Force",
        ]
        return "$current = " + "; ".join(cleanup_parts)

    def _read_value(self, path: str) -> Optional[str]:
        """Read a WSMan client value, returning None on error."""
        try:
            result = subprocess.run(
                ["powershell", "-Command", f"(Get-Item {path}).Value"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode != 0:
                return None
            return result.stdout.strip()
        except subprocess.SubprocessError:
            return None

    @staticmethod
    def _build_trustedhosts_revert(previous: Optional[str]) -> str:
        """Create a revert script to restore TrustedHosts."""
        value = previous if previous is not None else ""
        escaped = value.replace("'", "''")
        return (
            f"$prev = '{escaped}'; "
            "Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value $prev -Force"
        )

    def _run_command(self, command: str) -> bool:
        try:
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )
            return result.returncode == 0
        except subprocess.SubprocessError as exc:
            logger.debug("WinRM client configuration failed: %s", exc)
            return False
