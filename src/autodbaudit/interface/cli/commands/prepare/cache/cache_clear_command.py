"""
Cache Clear Command - Ultra-granular cache clearing functionality.

This module provides the cache clear command for clearing all caches.
"""

import logging

import typer

from ......application.container import Container

logger = logging.getLogger(__name__)


class CacheClearCommand:
    """
    Ultra-granular cache clearing command.

    Clears all caches in the prepare service.
    """

    def __init__(self, container: Container):
        """
        Initialize the cache clear command.

        Args:
            container: Application dependency container
        """
        self.container = container

    def execute(self) -> None:
        """Execute cache clearing."""
        self.container.prepare_service.clear_cache()
        print("[green]✅ All caches cleared successfully![/green]")


def cache_clear_command():
    """
    Clear all caches in the prepare service.

    This command clears connection caches, OS detection caches, and test result caches.
    """
    container = Container()
    command = CacheClearCommand(container)

    try:
        command.execute()
    except Exception as e:
        logger.error("Cache clear command failed: %s", e)
        print(f"[red]❌ Error:[/red] {e}")
        raise typer.Exit(1)
