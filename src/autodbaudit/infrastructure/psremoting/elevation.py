"""
Shell Elevation Detection and User Guidance

Detects whether the current shell has administrative privileges
and provides user guidance for elevation when needed.
"""

import ctypes
import sys
import platform

from .models import ElevationStatus


class ShellElevationService:
    """
    Service for detecting shell elevation status and guiding users.

    This service checks if the current process has administrative privileges
    and provides appropriate guidance when elevation is required for operations.
    """

    def __init__(self):
        self._is_windows = platform.system() == "Windows"

    def check_elevation(self) -> ElevationStatus:
        """
        Check current elevation status.

        Returns:
            ElevationStatus: Current elevation state and requirements
        """
        if not self._is_windows:
            # On non-Windows, assume elevated (simplified for now)
            return ElevationStatus(
                is_elevated=True,
                elevation_required=False,
                can_elevate=True
            )

        is_elevated = self._is_admin_windows()
        return ElevationStatus(
            is_elevated=is_elevated,
            elevation_required=False,  # Will be set by calling code
            can_elevate=True,
            elevation_method="UAC" if self._supports_uac() else "runas"
        )

    def require_elevation(self, operation: str) -> ElevationStatus:
        """
        Check if elevation is required for an operation.

        Args:
            operation: Description of the operation requiring elevation

        Returns:
            ElevationStatus: Elevation requirements for the operation
        """
        current_status = self.check_elevation()

        if current_status.is_elevated:
            return current_status

        # Mark elevation as required
        return ElevationStatus(
            is_elevated=False,
            elevation_required=True,
            can_elevate=current_status.can_elevate,
            elevation_method=current_status.elevation_method
        )

    def guide_user_elevation(self, operation: str) -> str:
        """
        Provide user guidance for elevation.

        Args:
            operation: Description of operation requiring elevation

        Returns:
            str: User-friendly guidance message
        """
        status = self.require_elevation(operation)

        if status.is_elevated:
            return f"✓ Administrative privileges confirmed for: {operation}"

        if not status.can_elevate:
            return f"✗ Elevation not possible on this system. {operation} may fail."

        method = status.elevation_method or "administrator"
        return "\n".join([
            f"⚠️  Administrative privileges required for: {operation}",
            "",
            f"To proceed, restart this application as {method}:",
            "",
            "Option 1 - Windows Terminal/Command Prompt:",
            "  Right-click the terminal icon → Run as administrator",
            "",
            "Option 2 - PowerShell:",
            "  Start-Process powershell -Verb RunAs",
            "",
            "Option 3 - Explorer:",
            f"  Right-click {sys.executable} → Run as administrator",
            "",
            "After elevation, re-run the prepare command."
        ])

    def _is_admin_windows(self) -> bool:
        """
        Check if current process has administrative privileges on Windows.

        Returns:
            bool: True if running as administrator
        """
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            # Fallback: check if we can access admin-only resources
            try:
                # Try to open an admin-only registry key
                import winreg
                winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\Microsoft\Windows\CurrentVersion",
                             0, winreg.KEY_READ)
                return True
            except Exception:
                return False

    def _supports_uac(self) -> bool:
        """
        Check if system supports UAC (Vista and later).

        Returns:
            bool: True if UAC is supported
        """
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                               r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System")
            value, _ = winreg.QueryValueEx(key, "EnableLUA")
            winreg.CloseKey(key)
            return value == 1
        except Exception:
            # Assume UAC support on modern Windows
            return True
