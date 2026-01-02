"""
Prepare command function - Ultra-granular CLI command entry point.

This module provides the Typer command function that serves as the
entry point for the prepare command.
"""

import logging
from typing import List, Optional

import typer

from autodbaudit.application.container import Container
from autodbaudit.domain.config.audit_settings import AuditSettings, AuditTimeouts
from .prepare_command import PrepareCommand

logger = logging.getLogger(__name__)


def prepare_command(  # pylint: disable=too-many-positional-arguments,too-many-arguments
    target_names: Optional[List[str]] = typer.Argument(
        None,
        help="Specific target names to prepare. If not provided, prepares all enabled targets."
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose output with detailed logs and cache statistics."
    ),
    force_refresh: bool = typer.Option(
        False,
        "--force-refresh",
        help="Force refresh of cached connection information."
    ),
    show_cache_stats: bool = typer.Option(
        False,
        "--cache-stats",
        help="Display cache statistics after preparation."
    ),
    require_elevation: bool = typer.Option(
        False,
        "--require-elevation",
        help="Require elevated shell privileges for preparation."
    ),
    revert_localhost: bool = typer.Option(
        False,
        "--revert-localhost",
        help="Revert localhost to secure state by disabling all remote access configurations."
    ),
    powershell_timeout: int = typer.Option(
        30,
        "--powershell-timeout",
        help="Timeout in seconds for PowerShell remoting commands.",
        min=5,
        max=300
    ),
    tsql_timeout: int = typer.Option(
        60,
        "--tsql-timeout",
        help="Timeout in seconds for T-SQL queries.",
        min=10,
        max=600
    ),
    parallel: bool = typer.Option(
        True,
        "--parallel/--sequential",
        help="Enable parallel processing of targets."
    ),
    max_parallel: int = typer.Option(
        5,
        "--max-parallel",
        help="Maximum number of targets to process in parallel.",
        min=1,
        max=20
    )
):
    """
    Prepare SQL Server targets for auditing using ultra-granular services.

    This command orchestrates OS detection, connection testing, method selection,
    and caching to ensure optimal preparation for all configured targets.

    The prepare service is the single source of truth for target preparation
    across the entire application.
    """
    # Create dynamic audit settings
    audit_settings = AuditSettings(
        timeouts=AuditTimeouts(
            powershell_command_timeout=powershell_timeout,
            tsql_query_timeout=tsql_timeout
        ),
        enable_parallel_processing=parallel,
        max_parallel_targets=max_parallel,
        require_elevated_shell=require_elevation
    )

    container = Container()
    command = PrepareCommand(container, audit_settings)

    try:
        command.execute(
            target_names=target_names,
            verbose=verbose,
            force_refresh=force_refresh,
            show_cache_stats=show_cache_stats,
            require_elevation=require_elevation,
            revert_localhost=revert_localhost
        )
    except Exception as e:
        logger.error("Prepare command failed: %s", e)
        print(f"[red]❌ Error:[/red] {e}")
        raise typer.Exit(1)
