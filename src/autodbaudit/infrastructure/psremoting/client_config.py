"""
Client-side WinRM configuration helpers.
"""

import logging
import socket
import subprocess

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

    def add_to_trusted_hosts(self, server: str) -> bool:
        """Add server to WinRM TrustedHosts."""
        command = (
            "Set-Item WSMan:\\localhost\\Client\\TrustedHosts "
            f"-Value '{server}' -Concatenate -Force"
        )
        return self._run_command(command)

    def configure_winrm_client(self) -> None:
        """Apply client WinRM settings."""
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
        for command in commands:
            self._run_command(command)

    def cleanup_trustedhosts(self, server_name: str) -> str:
        """Build a PowerShell snippet to remove a server from TrustedHosts."""
        cleanup_parts = [
            "(Get-Item WSMan:\\localhost\\Client\\TrustedHosts).Value",
            "$hosts = ($current -split ',') | Where-Object { $_ -and $_ -ne '%s' }" % server_name,
            "Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value ($hosts -join ',') -Force",
        ]
        return "$current = " + "; ".join(cleanup_parts)

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
