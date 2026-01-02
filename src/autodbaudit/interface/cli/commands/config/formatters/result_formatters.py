"""
Result formatters for config commands.

Provides formatting and display logic for command results.
"""


class ValidationResultFormatter:
    """
    Formatter for configuration validation results.
    """

    def display_validation_results(self, errors: list[str], strict: bool) -> None:
        """
        Display validation results to the user.

        Args:
            errors: List of validation error messages
            strict: Whether strict validation was performed
        """
        if not errors:
            mode = "strict " if strict else ""
            print(f"[green]✅ All {mode}configuration validation checks passed![/green]")
            return

        print(f"[red]❌ Configuration validation failed with {len(errors)} error(s):[/red]")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")

        if strict:
            print("\n[yellow]💡 Strict validation mode was enabled[/yellow]")


class ConfigSummaryFormatter:
    """
    Formatter for configuration summary results.
    """

    def display_config_summary(self, summary_data: dict, detailed: bool) -> None:
        """
        Display configuration summary to the user.

        Args:
            summary_data: Dictionary containing summary information
            detailed: Whether to show detailed information
        """
        print("[blue]📊 Configuration Summary[/blue]")
        print("=" * 50)

        # Display basic config info
        if "config_files" in summary_data:
            print("\n[bold]Configuration Files:[/bold]")
            for file_info in summary_data["config_files"]:
                status = "[green]✓[/green]" if file_info["loaded"] else "[red]✗[/red]"
                print(f"  {status} {file_info['name']}: {file_info['path']}")

        if "targets" in summary_data:
            print(f"\n[bold]SQL Targets ({len(summary_data['targets'])}):[/bold]")
            for target in summary_data["targets"][:5] if not detailed else summary_data["targets"]:
                print(f"  • {target['name']} ({target['server']})")
            if len(summary_data["targets"]) > 5 and not detailed:
                print(f"  ... and {len(summary_data['targets']) - 5} more")

        if detailed and "credentials" in summary_data:
            print("\n[bold]Credentials Status:[/bold]")
            for cred in summary_data["credentials"]:
                status = "[green]✓[/green]" if cred["valid"] else "[red]✗[/red]"
                print(f"  {status} {cred['type']}: {cred['file']}")

        print("\n[yellow]💡 Use --detailed for more information[/yellow]")
