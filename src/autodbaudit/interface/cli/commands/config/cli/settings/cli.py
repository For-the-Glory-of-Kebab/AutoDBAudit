"""
Settings Command Function - Audit Settings Management

Handles audit settings management command.
"""

import logging
from typing import Optional

import typer

from autodbaudit.application.container import Container
from autodbaudit.interface.cli.commands.config.services.audit_settings_command import AuditSettingsCommand, SettingsUpdate

logger = logging.getLogger(__name__)


def audit_settings(  # pylint: disable=too-many-positional-arguments,too-many-arguments
    show_current: bool = typer.Option(
        True,
        "--show/--no-show",
        help="Display current audit settings."
    ),
    powershell_timeout: Optional[int] = typer.Option(
        None,
        "--powershell-timeout",
        help="Set timeout in seconds for PowerShell remoting commands.",
        min=5,
        max=300
    ),
    tsql_timeout: Optional[int] = typer.Option(
        None,
        "--tsql-timeout",
        help="Set timeout in seconds for T-SQL queries.",
        min=10,
        max=600
    ),
    enable_parallel: Optional[bool] = typer.Option(
        None,
        "--enable-parallel/--disable-parallel",
        help="Enable or disable parallel processing of targets."
    ),
    max_parallel: int = typer.Option(
        None,
        "--max-parallel",
        help="Set maximum number of targets to process in parallel.",
        min=1,
        max=20
    ),
    require_elevation: Optional[bool] = typer.Option(
        None,
        "--require-elevation/--no-elevation",
        help="Require elevated shell privileges for operations."
    )
):
    """
    Manage dynamic audit settings for timeouts and performance tuning.

    This command allows you to view and modify audit settings that control
    timeouts and performance parameters across the entire application.

    Settings include:
    - PowerShell command timeouts
    - T-SQL query timeouts
    - Parallel processing configuration
    - Shell elevation requirements
    """
    container = Container()
    command = AuditSettingsCommand(container)

    updates = SettingsUpdate(
        powershell_timeout=powershell_timeout,
        tsql_timeout=tsql_timeout,
        enable_parallel=enable_parallel,
        max_parallel=max_parallel,
        require_elevation=require_elevation
    )

    try:
        command.execute(show_current=show_current, updates=updates)
    except Exception as e:
        logger.error("Audit settings command failed: %s", e)
        print(f"[red]❌ Error:[/red] {e}")
        raise typer.Exit(1)
