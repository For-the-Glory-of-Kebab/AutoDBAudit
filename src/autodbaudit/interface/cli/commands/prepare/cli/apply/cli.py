"""
Apply Command Function - Prepare and Apply Audit Targets

Handles the application of audit preparation to targets.
"""

import typer
from typing import List, Optional

from autodbaudit.interface.cli.commands.prepare.services.apply_service import ApplyService


def apply_targets(
    targets: Optional[List[str]] = typer.Option(
        None,
        "--targets",
        "-t",
        help="Target servers to prepare. If not specified, uses all enabled targets from sql_targets.json"
    ),
    config_file: str = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to audit configuration file"
    ),
    credentials_file: str = typer.Option(
        None,
        "--credentials",
        help="Path to credentials file"
    ),
    parallel: bool = typer.Option(
        True,
        "--parallel/--sequential",
        help="Process targets in parallel"
    ),
    timeout: int = typer.Option(
        300,
        "--timeout",
        help="Timeout in seconds for each target preparation"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be done without executing"
    )
):
    """
    Apply PS remoting setup to specified targets.

    This command prepares servers for PS remoting by:
    - Establishing PowerShell remoting connections
    - Configuring WinRM services and firewall rules
    - Setting up authentication and credentials
    - Generating manual override scripts for failures

    If no targets are specified, processes ALL enabled targets from sql_targets.json.
    Multiple SQL instances on the same server are consolidated into one PS remoting operation.
    """
    service = ApplyService()

    result = service.apply_targets(
        targets=targets,
        config_file=config_file,
        credentials_file=credentials_file,
        parallel=parallel,
        timeout=timeout,
        dry_run=dry_run
    )

    typer.echo(result)
