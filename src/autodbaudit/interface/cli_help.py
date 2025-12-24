"""
Rich-formatted CLI help display.

Provides colorful, dynamic help output for the AutoDBAudit CLI.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()


def print_main_help() -> None:
    """Print the main CLI help with rich formatting."""
    # Header banner
    banner = Text()
    banner.append(
        "╔═══════════════════════════════════════════════════════════════╗\n",
        style="bold cyan",
    )
    banner.append("║  ", style="bold cyan")
    banner.append("🛡️  AutoDBAudit", style="bold white")
    banner.append(" - SQL Server Security Audit Tool    ", style="bold cyan")
    banner.append("║\n", style="bold cyan")
    banner.append(
        "╚═══════════════════════════════════════════════════════════════╝",
        style="bold cyan",
    )
    console.print(banner)
    console.print()

    # Usage
    console.print("[bold yellow]USAGE:[/bold yellow]")
    console.print(
        "  python main.py [bright_cyan]<command>[/bright_cyan] [dim][options][/dim]\n"
    )

    # Commands table
    commands = Table(
        show_header=True,
        header_style="bold magenta",
        box=box.SIMPLE,
        padding=(0, 2),
    )
    commands.add_column("Command", style="bright_cyan", width=12)
    commands.add_column("Description", style="white")
    commands.add_column("Key Options", style="dim")

    commands.add_row(
        "audit", "Run security audit collection", "--new, --id, --list, --targets"
    )
    commands.add_row("sync", "Re-scan & merge changes", "--audit-id, --targets")
    commands.add_row(
        "remediate", "Generate fix scripts", "--generate, --aggressiveness"
    )
    commands.add_row(
        "finalize", "Lock audit as baseline", "--audit-id, --force, --status"
    )
    commands.add_row("definalize", "Revert finalized audit", "--audit-id")
    commands.add_row(
        "util", "Utilities & diagnostics", "--check-drivers, --validate-config"
    )

    console.print(
        Panel(
            commands, title="[bold green]📋 COMMANDS[/bold green]", border_style="green"
        )
    )

    # Quick examples
    console.print("\n[bold yellow]QUICK START:[/bold yellow]")
    examples = [
        ("Start new audit:", 'python main.py audit --new --name "Q4 2024 Audit"'),
        ("List audits:", "python main.py audit --list"),
        ("Sync progress:", "python main.py sync --audit-id 1"),
        ("Generate scripts:", "python main.py remediate --generate --audit-id 1"),
    ]
    for label, cmd in examples:
        console.print(f"  [dim]{label}[/dim]")
        console.print(f"    [bright_green]{cmd}[/bright_green]")

    console.print(
        "\n[dim]Use[/dim] [bright_cyan]python main.py <command> --help[/bright_cyan] [dim]for command-specific options.[/dim]\n"
    )


def print_audit_help() -> None:
    """Print help for the audit command."""
    console.print("\n[bold cyan]🔍 AUDIT COMMAND[/bold cyan]")
    console.print(
        "[dim]Collect security configuration from SQL Server instances.[/dim]\n"
    )

    table = Table(show_header=True, header_style="bold", box=box.ROUNDED)
    table.add_column("Option", style="bright_cyan", width=20)
    table.add_column("Description", style="white")
    table.add_column("Default", style="dim", width=15)

    table.add_row("--new", "Start a fresh audit", "-")
    table.add_row("--name <name>", "Name for the new audit", "Auto-generated")
    table.add_row("--id <ID>", "Resume an existing audit", "-")
    table.add_row("--list", "Show all audits", "-")
    table.add_row("--targets <file>", "Target config file", "sql_targets.json")
    table.add_row("--organization <name>", "Organization name", "-")

    console.print(table)

    console.print("\n[bold yellow]EXAMPLES:[/bold yellow]")
    console.print(
        '  [green]python main.py audit --new --name "Monthly Security Audit"[/green]'
    )
    console.print(
        "  [green]python main.py audit --id 3[/green]  [dim]# Resume audit #3[/dim]"
    )
    console.print()


def print_sync_help() -> None:
    """Print help for the sync command."""
    console.print("\n[bold cyan]🔄 SYNC COMMAND[/bold cyan]")
    console.print(
        "[dim]Re-scan servers and merge changes with existing annotations.[/dim]\n"
    )

    table = Table(show_header=True, header_style="bold", box=box.ROUNDED)
    table.add_column("Option", style="bright_cyan", width=20)
    table.add_column("Description", style="white")
    table.add_column("Default", style="dim", width=15)

    table.add_row("--audit-id <ID>", "Audit to sync", "Latest audit")
    table.add_row("--targets <file>", "Target config file", "sql_targets.json")

    console.print(table)

    console.print("\n[bold yellow]WORKFLOW:[/bold yellow]")
    console.print("  [dim]1.[/dim] Edit Excel → Add notes, exceptions, justifications")
    console.print(
        "  [dim]2.[/dim] Run sync → [green]python main.py sync --audit-id 1[/green]"
    )
    console.print("  [dim]3.[/dim] Review → Regressions ↩, Fixed ✓, New Issues tracked")
    console.print()


def print_remediate_help() -> None:
    """Print help for the remediate command."""
    console.print("\n[bold cyan]🔧 REMEDIATE COMMAND[/bold cyan]")
    console.print("[dim]Generate T-SQL remediation scripts based on findings.[/dim]\n")

    table = Table(show_header=True, header_style="bold", box=box.ROUNDED)
    table.add_column("Option", style="bright_cyan", width=25)
    table.add_column("Description", style="white")

    table.add_row("--generate", "Generate script files")
    table.add_row("--audit-id <ID>", "Target audit")
    table.add_row("--aggressiveness <1-3>", "Fix intensity level")
    table.add_row("--scripts <folder>", "Custom scripts folder")
    table.add_row("--dry-run", "Simulate execution")

    console.print(table)

    console.print("\n[bold yellow]AGGRESSIVENESS LEVELS:[/bold yellow]")
    levels = Table(show_header=False, box=box.SIMPLE)
    levels.add_column("Level", style="bold", width=10)
    levels.add_column("Description", style="white")
    levels.add_row(
        "[green]1 (Safe)[/green]", "Conservative - all changes commented out"
    )
    levels.add_row("[yellow]2 (Standard)[/yellow]", "Recommended actions uncommented")
    levels.add_row("[red]3 (Nuclear)[/red]", "Aggressive - DROP instead of DISABLE")
    console.print(levels)
    console.print()


def print_finalize_help() -> None:
    """Print help for the finalize command."""
    console.print("\n[bold cyan]🔒 FINALIZE COMMAND[/bold cyan]")
    console.print("[dim]Lock an audit as the baseline for future comparisons.[/dim]\n")

    table = Table(show_header=True, header_style="bold", box=box.ROUNDED)
    table.add_column("Option", style="bright_cyan", width=20)
    table.add_column("Description", style="white")

    table.add_row("--audit-id <ID>", "Audit to finalize")
    table.add_row("--status", "Check readiness only")
    table.add_row("--force", "Bypass safety checks")
    table.add_row("--apply-exceptions", "Import Excel exceptions first")
    table.add_row("--excel <file>", "Excel file path")

    console.print(table)

    console.print("\n[bold yellow]NOTES:[/bold yellow]")
    console.print(
        "  [dim]•[/dim] Finalization is [bold]irreversible[/bold] (use [bright_cyan]definalize[/bright_cyan] to revert)"
    )
    console.print("  [dim]•[/dim] All unresolved issues will be marked as baseline")
    console.print()


def print_util_help() -> None:
    """Print help for the util command."""
    console.print("\n[bold cyan]🛠️  UTIL COMMAND[/bold cyan]")
    console.print("[dim]Diagnostic and configuration utilities.[/dim]\n")

    table = Table(show_header=True, header_style="bold", box=box.ROUNDED)
    table.add_column("Option", style="bright_cyan", width=20)
    table.add_column("Description", style="white")

    table.add_row("--check-drivers", "Verify ODBC drivers")
    table.add_row("--validate-config", "Validate config files")
    table.add_row("--setup-credentials", "Setup encrypted credentials")

    console.print(table)
    console.print()


def show_version() -> None:
    """Display version information."""
    console.print("\n[bold cyan]AutoDBAudit[/bold cyan] [dim]v1.0.0[/dim]")
    console.print("[dim]SQL Server Security Audit & Remediation Tool[/dim]")
    console.print("[dim]https://github.com/your-org/autodbaudit[/dim]\n")
