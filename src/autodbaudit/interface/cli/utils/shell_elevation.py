"""
Shell elevation utilities for detecting and requesting elevated privileges.

This module provides ultra-granular utilities for shell elevation detection
and user interaction for privilege escalation.
"""

import logging
import os
import sys

import typer
from rich.console import Console
from rich.panel import Panel

# Windows-specific imports (optional)
try:
    import ctypes
    import win32con
    from win32com.shell.shell import ShellExecuteEx
    WINDOWS_ELEVATION_AVAILABLE = True
except ImportError:
    WINDOWS_ELEVATION_AVAILABLE = False

logger = logging.getLogger(__name__)
console = Console()


class ShellElevationService:
    """
    Service for detecting and managing shell elevation status.

    Provides methods to check current privilege level and request elevation.
    """

    def is_elevated(self) -> bool:
        """
        Check if the current process is running with elevated privileges.

        Returns:
            True if running as administrator/root, False otherwise
        """
        try:
            if sys.platform == "win32":
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            # Unix-like systems
            return os.geteuid() == 0
        except AttributeError:
            # os.geteuid() not available on some platforms (like Windows)
            logger.warning("Could not determine elevation status: geteuid not available")
            return False
        except Exception as e:
            logger.warning("Could not determine elevation status: %s", e)
            return False

    def require_elevation(self, operation: str) -> bool:
        """
        Check if elevation is required for an operation and prompt user if needed.

        Args:
            operation: Description of the operation requiring elevation

        Returns:
            True if elevation is available or user agrees to elevate, False otherwise
        """
        if self.is_elevated():
            logger.debug("Already running with elevated privileges")
            return True

        console.print(Panel.fit(
            f"[yellow]⚠️  Operation requires elevated privileges:[/yellow]\n"
            f"[red]{operation}[/red]\n\n"
            f"Current shell is not elevated. Some operations may fail.",
            title="🔐 Elevation Required",
            border_style="yellow"
        ))

        if typer.confirm("Would you like to restart with elevated privileges?", default=False):
            self._request_elevation()
            return False  # Will restart the process

        console.print("[yellow]Continuing without elevation - some operations may fail[/yellow]")
        return False

    def _request_elevation(self) -> None:
        """
        Request elevation by restarting the process with elevated privileges.

        This method will exit the current process and start a new elevated one.
        """
        if sys.platform == "win32":
            self._elevate_windows()
        else:
            self._elevate_unix()

    def _elevate_windows(self) -> None:
        """Request elevation on Windows systems."""
        if not WINDOWS_ELEVATION_AVAILABLE:
            console.print("[red]❌ Elevation not supported - pywin32 not available[/red]")
            return

        try:
            # Request elevation
            quoted_args = [f'"{arg}"' for arg in sys.argv[1:]]
            params = " ".join(quoted_args)
            result = ShellExecuteEx(
                lpVerb="runas",
                lpFile=sys.executable,
                lpParameters=params,
                nShow=win32con.SW_SHOWNORMAL
            )

            if result:
                msg = ("[green]✅ Elevation requested - "
                       "restarting with administrator privileges[/green]")
                console.print(msg)
                sys.exit(0)
            else:
                console.print("[red]❌ Elevation request failed[/red]")

        except Exception as e:
            logger.error("Elevation request failed: %s", e)
            console.print("[red]❌ Elevation request failed[/red]")

    def _elevate_unix(self) -> None:
        """Request elevation on Unix-like systems."""
        try:
            # Use sudo to restart with elevated privileges
            cmd = ["sudo"] + sys.argv
            console.print("[green]✅ Requesting elevation with sudo...[/green]")

            # Replace current process
            os.execvp("sudo", cmd)

        except Exception as e:
            logger.error("Sudo elevation failed: %s", e)
            console.print("[red]❌ Elevation request failed[/red]")
