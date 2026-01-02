"""
CLI result formatters for displaying prepare results and statistics.

This module provides ultra-granular formatters for CLI output,
separating display logic from command logic.
"""

import logging
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from autodbaudit.domain.config import PrepareResult

logger = logging.getLogger(__name__)
console = Console()


class PrepareResultFormatter:
    """
    Formatter for displaying prepare results in various formats.

    Provides clean separation between data processing and display logic.
    """

    def display_results_table(
        self,
        results: List[PrepareResult],
        verbose: bool = False,
        show_cache_stats: bool = False
    ) -> None:
        """
        Display prepare results in a formatted table.

        Args:
            results: List of prepare results
            verbose: Whether to show detailed logs
            show_cache_stats: Whether to show cache statistics
        """
        table = Table(title="🔍 Prepare Results - Ultra-granular Services")
        table.add_column("Target", style="cyan", no_wrap=True)
        table.add_column("Server", style="blue", no_wrap=True)
        table.add_column("Status", style="green")
        table.add_column("OS Type", style="yellow")
        table.add_column("Connection Method", style="magenta")
        table.add_column("Available", style="green")

        successful = 0
        for result in results:
            if result.success:
                successful += 1
                status = "[green]✅ Success[/green]"
                os_type = result.connection_info.os_type.value if result.connection_info else "Unknown"
                method = result.connection_info.preferred_method.value if result.connection_info and result.connection_info.preferred_method else "None"
                available = "[green]✅ Yes[/green]" if result.connection_info and result.connection_info.is_available else "[red]❌ No[/red]"
            else:
                status = "[red]❌ Failed[/red]"
                os_type = "N/A"
                method = "N/A"
                available = "[red]❌ No[/red]"

            table.add_row(
                result.target.name,
                result.target.server,
                status,
                os_type,
                method,
                available
            )

        console.print(table)
        console.print(f"\n[blue]📊 Summary: {successful}/{len(results)} targets prepared successfully[/blue]")

        if verbose:
            self._display_detailed_logs(results)

        if show_cache_stats:
            # Cache stats would be passed separately
            pass

    def _display_detailed_logs(self, results: List[PrepareResult]) -> None:
        """Display detailed logs for each result."""
        console.print("\n[blue]📝 Detailed Logs:[/blue]")
        for result in results:
            console.print(f"\n[yellow]🎯 Target: {result.target.name}[/yellow]")
            for log in result.logs:
                console.print(f"  {log}")
            if result.error_message:
                console.print(f"  [red]❌ Error: {result.error_message}[/red]")


class CacheStatisticsFormatter:
    """
    Formatter for displaying cache statistics and health information.

    Provides comprehensive cache status display.
    """

    def display_cache_stats(self, stats: dict) -> None:
        """
        Display comprehensive cache statistics.

        Args:
            stats: Dictionary containing cache statistics
        """
        cache_panel = Panel.fit(
            f"[bold]Connection Cache:[/bold]\n"
            f"  Hits: {stats.get('connection_cache', {}).get('hits', 0)}\n"
            f"  Misses: {stats.get('connection_cache', {}).get('misses', 0)}\n"
            f"  Puts: {stats.get('connection_cache', {}).get('puts', 0)}\n"
            f"  Deletes: {stats.get('connection_cache', {}).get('deletes', 0)}\n"
            f"  Hit Rate: {stats.get('connection_cache', {}).get('hit_rate', 0):.1%}\n\n"
            f"[bold]OS Detection Cache:[/bold] {stats.get('os_detection_cache_size', 0)} entries\n"
            f"[bold]Connection Test Cache:[/bold] {stats.get('connection_test_cache_size', 0)} entries",
            title="📈 Cache Statistics",
            border_style="cyan"
        )
        console.print(cache_panel)


class ConfigSummaryFormatter:
    """
    Formatter for displaying configuration summaries.

    Provides clean display of configuration state.
    """

    def display_config_summary(self, summary: dict) -> None:
        """
        Display configuration summary in formatted panels.

        Args:
            summary: Configuration summary dictionary
        """
        # Main configuration panel
        config_panel = Panel.fit(
            f"[bold blue]Configuration Directory:[/bold blue] {summary.get('config_directory', 'Unknown')}\n"
            f"[bold blue]Audit Config:[/bold blue] {'✅ Loaded' if summary.get('audit_config_loaded') else '❌ Not loaded'}\n"
            f"[bold blue]SQL Targets:[/bold blue] {'✅ Loaded' if summary.get('sql_targets_loaded') else '❌ Not loaded'}\n"
            f"[bold blue]Cached Credentials:[/bold blue] {summary.get('cached_credentials', 0)}",
            title="📋 Configuration Summary",
            border_style="blue"
        )
        console.print(config_panel)

        # Detailed information
        if summary.get('organization'):
            org_panel = Panel.fit(
                f"[bold]Organization:[/bold] {summary['organization']}\n"
                f"[bold]Audit Year:[/bold] {summary['audit_year']}",
                title="🏢 Organization Details",
                border_style="green"
            )
            console.print(org_panel)

        if summary.get('total_targets', 0) > 0:
            targets_panel = Panel.fit(
                f"[bold]Total Targets:[/bold] {summary['total_targets']}\n"
                f"[bold]Enabled Targets:[/bold] {summary['enabled_targets']}\n"
                f"[bold]Disabled Targets:[/bold] {summary['total_targets'] - summary['enabled_targets']}",
                title="🎯 Target Statistics",
                border_style="yellow"
            )
            console.print(targets_panel)


class ValidationResultFormatter:
    """
    Formatter for displaying validation results and errors.

    Provides clear error reporting and success confirmation.
    """

    def display_validation_results(self, errors: List[str], strict_mode: bool = False) -> None:
        """
        Display validation results with appropriate formatting.

        Args:
            errors: List of validation errors
            strict_mode: Whether strict validation was performed
        """
        if not errors:
            mode_text = " (Strict Mode)" if strict_mode else ""
            console.print(f"[green]✅ All configuration files are valid{mode_text}![/green]")
            console.print("[green]🎉 Configuration is ready for prepare operations![/green]")
        else:
            console.print("[red]❌ Configuration validation failed:[/red]")
            for error in errors:
                console.print(f"  • {error}")
            console.print(f"\n[yellow]💡 Fix the above errors and run validation again[/yellow]")
