"""
Cache Subcommand CLI - Manage Connection Cache

Handles caching of connection information and credentials.
"""

import typer

from autodbaudit.interface.cli.commands.prepare.services.cache_service import CacheService

app = typer.Typer(
    name="cache",
    help="💾 Manage connection cache for audit targets",
    rich_markup_mode="rich",
    no_args_is_help=True
)

cache_app = app

@app.command("clear")
def clear_cache(
    targets: list[str] = typer.Option(
        None,
        "--targets",
        help="Specific targets to clear from cache"
    ),
    all_targets: bool = typer.Option(
        False,
        "--all",
        help="Clear all cached targets"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force clear without confirmation"
    )
):
    """
    Clear cached connection information.

    Removes cached credentials and connection details for targets.
    Use --all to clear everything or specify specific targets.
    """
    if not all_targets and not targets:
        typer.echo("❌ Must specify --all or --targets")
        raise typer.Exit(1)

    service = CacheService()

    if all_targets:
        if not force:
            confirm = typer.confirm("Clear all cached targets?")
            if not confirm:
                typer.echo("Cancelled")
                return

        result = service.clear_all_cache()
    else:
        result = service.clear_cache(targets)

    typer.echo(result)

@app.command("list")
def list_cache(
    format: str = typer.Option(
        "table",
        "--format",
        help="Output format: table, json, csv"
    )
):
    """
    List cached connection information.

    Shows all currently cached targets and their connection status.
    """
    service = CacheService()

    cache_data = service.list_cache()

    if format == "json":
        import json
        typer.echo(json.dumps(cache_data, indent=2))
    elif format == "csv":
        import csv
        import sys
        if cache_data:
            writer = csv.DictWriter(sys.stdout, fieldnames=cache_data[0].keys())
            writer.writeheader()
            writer.writerows(cache_data)
    else:  # table
        from rich.table import Table
        from rich.console import Console

        table = Table(title="Connection Cache")
        if cache_data:
            table.add_column("Target", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Last Used", style="yellow")
            table.add_column("Method", style="blue")
            table.add_column("Auth", style="magenta")
            table.add_column("Attempts", style="red")
            table.add_column("SQL Targets", style="white")

            for item in cache_data:
                if item.get("status") == "stats":
                    # Special handling for stats row
                    table.add_row(
                        item.get("target", ""),
                        "Stats",
                        f"Hits: {item.get('cache_hits', 0)}",
                        f"Misses: {item.get('cache_misses', 0)}",
                        f"Entries: {item.get('total_entries', 0)}",
                        "",
                        ""
                    )
                else:
                    sql_targets = item.get("sql_targets", [])
                    targets_str = ", ".join(sql_targets) if sql_targets else "None"
                    table.add_row(
                        item.get("target", ""),
                        item.get("status", ""),
                        item.get("last_used", ""),
                        item.get("connection_method", ""),
                        item.get("auth_method", ""),
                        str(item.get("attempts", 0)),
                        targets_str
                    )

        console = Console()
        console.print(table)
