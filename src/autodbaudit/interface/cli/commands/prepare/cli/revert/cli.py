"""
Revert Command Function - Revert Audit Preparation

Handles reverting audit preparation changes on targets.
"""

import typer
from typing import List, Optional

from autodbaudit.interface.cli.commands.prepare.services.revert_service import RevertService


def revert_targets(
    targets: Optional[List[str]] = typer.Option(
        None,
        "--targets",
        "-t",
        help="Target servers to revert. If not specified, uses all enabled targets from sql_targets.json"
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
        help="Timeout in seconds for each target revert"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be reverted without executing"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force revert without confirmation"
    )
):
    """
    Revert PS remoting changes on specified targets.

    This command removes PS remoting configuration and restores
    systems to their pre-preparation state.

    If no targets are specified, processes ALL enabled targets from sql_targets.json.
    Multiple SQL instances on the same server are consolidated into one revert operation.
    """
    if not force and not dry_run:
        target_count = "all enabled" if targets is None else str(len(targets))
        confirm = typer.confirm(f"Revert PS remoting setup on {target_count} servers?")
        if not confirm:
            typer.echo("Cancelled")
            return

    service = RevertService()

    result = service.revert_targets(
        targets=targets,
        config_file=config_file,
        credentials_file=credentials_file,
        parallel=parallel,
        timeout=timeout,
        dry_run=dry_run
    )

    typer.echo(result)
