"""
Summary Command Function - Configuration Summary

Handles configuration summary command.
"""

import logging
from typing import Optional

import typer

from autodbaudit.application.container import Container
from ...services.config_summary_command import ConfigSummaryCommand

logger = logging.getLogger(__name__)


def config_summary(
    detailed: bool = typer.Option(
        False,
        "--detailed",
        help="Show detailed configuration information."
    )
):
    """
    Display comprehensive configuration summary.

    This command provides the single source of truth for configuration state,
    showing loaded configs, available targets, credential status, and system health.
    """
    container = Container()
    command = ConfigSummaryCommand(container)

    try:
        command.execute(detailed=detailed)
    except Exception as e:
        logger.error("Config summary failed: %s", e)
        print(f"[red]❌ Error:[/red] {e}")
        raise typer.Exit(1)
