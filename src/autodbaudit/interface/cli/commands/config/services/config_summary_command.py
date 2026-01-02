"""
Config summary command - Ultra-granular config summary logic.

This module provides specialized functionality for displaying
comprehensive configuration state information.
"""

import logging

from autodbaudit.application.container import Container
from ..formatters.result_formatters import ConfigSummaryFormatter

logger = logging.getLogger(__name__)


class ConfigSummaryCommand:
    """
    Ultra-granular config summary command.

    Displays comprehensive configuration state information.
    """

    def __init__(self, container: Container):
        """
        Initialize the config summary command.

        Args:
            container: Application dependency container
        """
        self.container = container
        self.formatter = ConfigSummaryFormatter()

    def execute(self, detailed: bool = False) -> None:
        """
        Execute config summary display.

        Args:
            detailed: Show detailed target information
        """
        summary = self.container.config_manager.get_config_summary()
        self.formatter.display_config_summary(summary, detailed)

        # Show detailed target information if requested
        if detailed and summary.get('total_targets', 0) > 0:
            self._display_detailed_targets()

    def _display_detailed_targets(self) -> None:
        """Display detailed information about all targets."""
        targets = self.container.config_manager.get_all_targets()

        if not targets:
            return

        # Use a simple table display for targets
        print(f"\n[yellow]🎯 Detailed Target Information ({len(targets)} targets):[/yellow]")
        for target in targets:
            enabled = "[green]✅ Yes[/green]" if target.enabled else "[red]❌ No[/red]"
            print(f"  {target.name}: {target.server}:{target.port} - {enabled}")
