"""
Revert Command - Ultra-granular localhost security revert functionality.

This module provides the revert command for securing localhost.
"""

import logging

import typer

from autodbaudit.interface.cli.services.localhost_revert_service import LocalhostRevertService

logger = logging.getLogger(__name__)


class RevertCommand:
    """
    Ultra-granular revert command for localhost security.

    Reverts localhost to secure state by disabling remote access configurations.
    """

    def __init__(self):
        """Initialize the revert command."""
        self.revert_service = LocalhostRevertService()

    def execute(self) -> None:
        """Execute localhost security revert."""
        self.revert_service.revert_unsafe_configurations()


def revert_command():
    """
    Revert localhost to secure state by disabling remote access configurations.

    This command disables WinRM, PowerShell remoting, remote registry, and resets
    firewall rules to secure the local machine against remote access vulnerabilities.
    """
    command = RevertCommand()

    try:
        command.execute()
    except Exception as e:
        logger.error("Revert command failed: %s", e)
        print(f"[red]❌ Error:[/red] {e}")
        raise typer.Exit(1)
