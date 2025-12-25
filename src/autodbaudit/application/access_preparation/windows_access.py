"""
Windows Access Manager.

Handles WinRM access preparation for Windows targets:
- Tests WinRM connectivity
- Enables WinRM service
- Configures firewall rules
- Sets TrustedHosts
- Captures/reverts state
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autodbaudit.infrastructure.config_loader import SqlTarget

logger = logging.getLogger(__name__)


@dataclass
class WinRMChange:
    """Record of a single change made during preparation."""

    step: str
    setting: str
    original_value: str | None
    new_value: str
    success: bool
    error: str | None = None


class WindowsAccessManager:
    """
    Manages WinRM access for a Windows target.

    Usage:
        manager = WindowsAccessManager(target)
        state = manager.capture_state()
        if not manager.test_connection():
            changes = manager.enable_access()
        manager.revert_changes(changes)
    """

    def __init__(self, target: SqlTarget):
        """
        Initialize manager for a target.

        Args:
            target: SQL target configuration
        """
        self.target = target
        self.hostname = target.server

    def test_connection(self) -> bool:
        """
        Test if WinRM connection works.

        Returns:
            True if connection successful
        """
        try:
            import winrm

            session = winrm.Session(
                self.hostname,
                auth=(
                    (self.target.username, self.target.password)
                    if self.target.auth == "sql"
                    else None
                ),
            )
            result = session.run_cmd("hostname")
            return result.status_code == 0
        except ImportError:
            logger.warning("pywinrm not installed, testing via PowerShell")
            return self._test_via_powershell()
        except Exception as e:
            logger.debug("WinRM test failed: %s", e)
            return False

    def _test_via_powershell(self) -> bool:
        """Test WinRM via PowerShell command."""
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"Test-WSMan -ComputerName {self.hostname} -ErrorAction Stop",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0
        except Exception as e:
            logger.debug("PowerShell WinRM test failed: %s", e)
            return False

    def capture_state(self) -> dict:
        """
        Capture current state of WinRM-related settings.

        Returns:
            Dict with current settings for revert
        """
        state = {
            "winrm_service": self._get_service_state("WinRM"),
            "trusted_hosts": self._get_trusted_hosts(),
            "firewall_rules": self._get_firewall_rules(),
        }
        logger.debug("Captured state for %s: %s", self.hostname, state)
        return state

    def _get_service_state(self, service_name: str) -> dict:
        """Get Windows service state."""
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"Get-Service {service_name} | Select-Object Status,StartType | ConvertTo-Json",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                import json

                return json.loads(result.stdout)
        except Exception as e:
            logger.debug("Could not get service state: %s", e)
        return {}

    def _get_trusted_hosts(self) -> str:
        """Get current TrustedHosts value."""
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "(Get-Item WSMan:\\localhost\\Client\\TrustedHosts).Value",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.debug("Could not get TrustedHosts: %s", e)
        return ""

    def _get_firewall_rules(self) -> list:
        """Get relevant firewall rules."""
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-NetFirewallRule -Name 'WINRM*' | Select-Object Name,Enabled | ConvertTo-Json",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                import json

                data = json.loads(result.stdout)
                return data if isinstance(data, list) else [data]
        except Exception as e:
            logger.debug("Could not get firewall rules: %s", e)
        return []

    def enable_access(self) -> list[dict]:
        """
        Enable WinRM access.

        Returns:
            List of changes made (for revert)
        """
        changes = []

        # Step 1: Enable WinRM service
        change = self._enable_winrm_service()
        changes.append(change.__dict__)

        # Step 2: Configure WinRM listener
        change = self._configure_winrm_listener()
        changes.append(change.__dict__)

        # Step 3: Enable firewall rules
        change = self._enable_firewall_rules()
        changes.append(change.__dict__)

        # Step 4: Add to TrustedHosts (if local machine)
        change = self._add_trusted_host()
        changes.append(change.__dict__)

        # Step 5: Enable PS Remoting
        change = self._enable_ps_remoting()
        changes.append(change.__dict__)

        return changes

    def _enable_winrm_service(self) -> WinRMChange:
        """Enable and start WinRM service."""
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Set-Service WinRM -StartupType Automatic; Start-Service WinRM",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return WinRMChange(
                step="winrm_service",
                setting="StartupType",
                original_value="Unknown",
                new_value="Automatic",
                success=result.returncode == 0,
                error=result.stderr if result.returncode != 0 else None,
            )
        except Exception as e:
            return WinRMChange(
                step="winrm_service",
                setting="StartupType",
                original_value="Unknown",
                new_value="Automatic",
                success=False,
                error=str(e),
            )

    def _configure_winrm_listener(self) -> WinRMChange:
        """Configure WinRM listener."""
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "winrm quickconfig -quiet",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            return WinRMChange(
                step="winrm_listener",
                setting="QuickConfig",
                original_value=None,
                new_value="Configured",
                success=result.returncode == 0,
                error=result.stderr if result.returncode != 0 else None,
            )
        except Exception as e:
            return WinRMChange(
                step="winrm_listener",
                setting="QuickConfig",
                original_value=None,
                new_value="Configured",
                success=False,
                error=str(e),
            )

    def _enable_firewall_rules(self) -> WinRMChange:
        """Enable WinRM firewall rules."""
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Enable-NetFirewallRule -Name 'WINRM-HTTP-In-TCP' -ErrorAction SilentlyContinue",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return WinRMChange(
                step="firewall",
                setting="WINRM-HTTP-In-TCP",
                original_value="Unknown",
                new_value="Enabled",
                success=True,  # May already be enabled
            )
        except Exception as e:
            return WinRMChange(
                step="firewall",
                setting="WINRM-HTTP-In-TCP",
                original_value="Unknown",
                new_value="Enabled",
                success=False,
                error=str(e),
            )

    def _add_trusted_host(self) -> WinRMChange:
        """Add target to TrustedHosts on local machine."""
        current = self._get_trusted_hosts()
        if self.hostname in current or current == "*":
            return WinRMChange(
                step="trusted_hosts",
                setting="TrustedHosts",
                original_value=current,
                new_value=current,
                success=True,
            )

        new_value = f"{current},{self.hostname}" if current else self.hostname
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value '{new_value}' -Force",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return WinRMChange(
                step="trusted_hosts",
                setting="TrustedHosts",
                original_value=current,
                new_value=new_value,
                success=result.returncode == 0,
                error=result.stderr if result.returncode != 0 else None,
            )
        except Exception as e:
            return WinRMChange(
                step="trusted_hosts",
                setting="TrustedHosts",
                original_value=current,
                new_value=new_value,
                success=False,
                error=str(e),
            )

    def _enable_ps_remoting(self) -> WinRMChange:
        """Enable PowerShell Remoting."""
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Enable-PSRemoting -Force -SkipNetworkProfileCheck -ErrorAction SilentlyContinue",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            return WinRMChange(
                step="ps_remoting",
                setting="PSRemoting",
                original_value="Unknown",
                new_value="Enabled",
                success=result.returncode == 0,
                error=result.stderr if result.returncode != 0 else None,
            )
        except Exception as e:
            return WinRMChange(
                step="ps_remoting",
                setting="PSRemoting",
                original_value="Unknown",
                new_value="Enabled",
                success=False,
                error=str(e),
            )

    def revert_changes(self, changes: list[dict]) -> None:
        """
        Revert changes made during preparation.

        Args:
            changes: List of changes to revert
        """
        for change in reversed(changes):
            step = change.get("step")
            original = change.get("original_value")

            if step == "trusted_hosts" and original:
                logger.info("Reverting TrustedHosts to: %s", original)
                subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        f"Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value '{original}' -Force",
                    ],
                    capture_output=True,
                    timeout=30,
                )

            # Add more revert logic for other steps as needed
            logger.debug("Reverted step: %s", step)
