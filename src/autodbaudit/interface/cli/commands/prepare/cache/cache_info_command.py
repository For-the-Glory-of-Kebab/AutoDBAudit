"""
Cache Info Command - Ultra-granular cache information display.

This module provides the cache info command for displaying cache statistics.
"""

import logging

import typer

from autodbaudit.application.container import Container
from autodbaudit.interface.cli.formatters.result_formatters import CacheStatisticsFormatter

logger = logging.getLogger(__name__)


class CacheInfoCommand:
    """
    Ultra-granular cache information command.

    Displays current cache statistics and health.
    """

    def __init__(self, container: Container):
        """
        Initialize the cache info command.

        Args:
            container: Application dependency container
        """
        self.container = container
        self.formatter = CacheStatisticsFormatter()

    def execute(self) -> None:
        """Execute cache information display."""
        cache_stats = self.container.prepare_service.get_cache_stats()
        self.formatter.display_cache_stats(cache_stats)


def cache_info_command():
    """
    Display cache statistics and health information.

    Shows the current state of all caches used by the ultra-granular prepare services.
    """
    container = Container()
    command = CacheInfoCommand(container)

    try:
        command.execute()
    except Exception as e:
        logger.error("Cache info command failed: %s", e)
        print(f"[red]❌ Error:[/red] {e}")
        raise typer.Exit(1)
