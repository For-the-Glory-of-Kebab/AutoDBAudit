"""
CLI Orchestrator - Main Entry Point

Ultra-modular CLI architecture with decoupled command wiring.
Each command lives in its own namespace with full functionality.
"""

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from autodbaudit.application.container import Container

# Import command modules
from autodbaudit.interface.cli.commands.prepare.cli import prepare_app
from autodbaudit.interface.cli.commands.config.cli import config_app
# from .commands.audit.cli import audit_app
# from .commands.report.cli import report_app

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create console for rich output
console = Console()

# Create main app
app = typer.Typer(
    name="autodbaudit",
    help="🔒 SQL Server Security Audit Tool - Ultra-modular Architecture",
    add_completion=False,
    rich_markup_mode="rich",
    invoke_without_command=True,
    no_args_is_help=True
)

# Add -h as synonym for --help
@app.callback()
def add_help_synonym(help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit.", is_eager=True)):
    if help:
        typer.echo(typer.get_command(app).get_help(typer.Context(typer.get_command(app))))
        raise typer.Exit()

# Add sub-apps to main app
app.add_typer(prepare_app, name="prepare")
app.add_typer(config_app, name="config")
# app.add_typer(audit_app, name="audit")
# app.add_typer(report_app, name="report")


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """
    🔒 AutoDBAudit - Ultra-modular SQL Server Security Audit Tool

    🚀 **Enterprise-grade Security Auditing with Railway-oriented Architecture**

    ✨ **Key Features:**
    - 🔍 **Ultra-granular Components**: Single-responsibility micro-modules (<50 lines each)
    - ⚡ **Dynamic Configuration**: Runtime-adjustable timeouts and audit settings
    - 🔄 **Parallel Processing**: Concurrent target validation and execution
    - 🧠 **DB-backed State**: Persistent audit state without TTL limitations
    - 🔧 **Hybrid Execution**: T-SQL + PowerShell remoting with fallback chains
    - 🛡️ **Elevation Awareness**: Automatic privilege detection and guidance
    - 🔐 **Secure Credentials**: Encrypted storage with SQL/OS credential separation

    📁 **Configuration Hierarchy:**
    1. Config file settings (primary)
    2. CLI overrides (secondary)
    3. Reasonable defaults (fallback)

    🏗️ **Clean Architecture:**
    - **Domain**: Pure business logic with Pydantic models
    - **Application**: Use cases and service orchestration
    - **Infrastructure**: External dependencies and persistence
    - **Interface**: Modular CLI with decoupled command wiring

    🎯 **Available Commands:**
    - `autodbaudit prepare` - Target preparation and cache management
    - `autodbaudit config` - Configuration validation and settings
    - `autodbaudit audit` - Security scanning and remediation
    - `autodbaudit report` - Comprehensive reporting and export

    🔧 **Quick Start:**
    1. Configure targets: `autodbaudit config validate`
    2. Prepare environment: `autodbaudit prepare apply`
    3. Run security audit: `autodbaudit audit run`
    4. Generate reports: `autodbaudit report generate`
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


if __name__ == "__main__":
    try:
        app()
    except SystemExit as e:
        # Typer uses SystemExit for various exit codes
        # If it's because of missing required arguments, show help
        import sys
        if len(sys.argv) > 1 and e.code == 1:
            # Try to show help for the current command
            try:
                app([*sys.argv[1:], "--help"])
            except:
                pass
        raise
