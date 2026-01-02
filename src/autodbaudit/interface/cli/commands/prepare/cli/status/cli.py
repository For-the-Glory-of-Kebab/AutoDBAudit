"""
Status Command Function - Show PS Remoting Connection Status

Displays recorded connection status and availability for all servers.
"""

import typer
from typing import Optional

from autodbaudit.interface.cli.commands.prepare.services.status_service import StatusService


def show_status(
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json, csv"
    ),
    filter: str = typer.Option(
        "all",
        "--filter",
        help="Filter results: all, successful, failed, manual"
    )
):
    """
    Show recorded PS remoting connection status for all servers.

    Displays connection methods, authentication types, timestamps,
    and associated SQL targets for each server that has been prepared.
    """
    service = StatusService()

    result = service.show_status(
        format=format,
        filter=filter
    )

    typer.echo(result)
