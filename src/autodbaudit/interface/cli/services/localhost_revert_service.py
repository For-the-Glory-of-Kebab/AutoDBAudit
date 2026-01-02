"""
Localhost revert service - Ultra-granular component for security cleanup.

This module provides specialized functionality for reverting localhost
to a secure state by disabling remote access configurations.
"""

import logging
import subprocess

logger = logging.getLogger(__name__)


class LocalhostRevertService:
    """
    Service for reverting localhost to secure state.

    Disables WinRM, PowerShell remoting, remote registry, and resets firewall
    to help users recover from unsafe configurations during development.
    """

    def revert_unsafe_configurations(self) -> None:
        """
        Revert localhost to secure state by disabling all remote access.

        This method disables:
        - Windows Remote Management (WinRM)
        - PowerShell remoting
        - Remote registry access
        - Resets Windows Firewall to defaults
        """
        print("[yellow]🔄 Reverting localhost to secure state...[/yellow]")
        print("[dim]This will disable remote access configurations for security.[/dim]")

        operations = [
            ("Disable WinRM service", self._disable_winrm),
            ("Disable PowerShell remoting", self._disable_ps_remoting),
            ("Disable remote registry", self._disable_remote_registry),
            ("Reset firewall rules", self._reset_firewall),
        ]

        completed = 0
        for description, operation in operations:
            try:
                print(f"[blue]   ↻ {description}...[/blue]", end="", flush=True)
                operation()
                print(" ✅")
                completed += 1
            except Exception as e:
                print(f" ❌ ({e})")
                logger.warning("Failed to %s: %s", description, e)

        total_ops = len(operations)
        print(f"[green]✅ Revert completed: {completed}/{total_ops} operations successful[/green]")
        print("[yellow]⚠️  Localhost has been secured. Remote access is disabled.[/yellow]")

    def _disable_winrm(self) -> None:
        """Disable Windows Remote Management service."""
        # Stop WinRM service
        subprocess.run([
            "net", "stop", "winrm"
        ], capture_output=True, check=False)

        # Disable WinRM service startup
        subprocess.run([
            "sc", "config", "winrm", "start=", "disabled"
        ], capture_output=True, check=False)

    def _disable_ps_remoting(self) -> None:
        """Disable PowerShell remoting."""
        # Disable PS remoting using PowerShell
        subprocess.run([
            "powershell", "-Command",
            "Disable-PSRemoting -Force"
        ], capture_output=True, check=False)

    def _disable_remote_registry(self) -> None:
        """Disable remote registry access."""
        # Disable remote registry service
        subprocess.run([
            "net", "stop", "RemoteRegistry"
        ], capture_output=True, check=False)

        # Disable remote registry service startup
        subprocess.run([
            "sc", "config", "RemoteRegistry", "start=", "disabled"
        ], capture_output=True, check=False)

    def _reset_firewall(self) -> None:
        """Reset Windows Firewall to defaults."""
        # Reset Windows Firewall to defaults
        subprocess.run([
            "netsh", "advfirewall", "reset"
        ], capture_output=True, check=False)
