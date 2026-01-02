"""
Ultra-granular CLI orchestrator - main entry point.

This module orchestrates all CLI commands using dependency injection
and clean architecture principles. Ultra-granular separation enforced.
"""

import logging
from pathlib import Path

import typer
from rich.console import Console

from autodbaudit.application.container import Container
from .cli.commands.prepare.apply import prepare_command  # pylint: disable=no-name-in-module
from .cli.commands.prepare.cache.cache_info_command import cache_info_command  # pylint: disable=no-name-in-module
from .cli.commands.prepare.cache.cache_clear_command import cache_clear_command  # pylint: disable=no-name-in-module
from .cli.commands.prepare.revert.revert_command import revert_command  # pylint: disable=no-name-in-module
from .cli.commands.config import config_validate_command, config_summary_command, audit_settings_command  # pylint: disable=no-name-in-module
from .cli.commands.audit.findings.findings_list_command import findings_list_command  # pylint: disable=no-name-in-module
from .cli.commands.audit.sync.sync_command import sync_command  # pylint: disable=no-name-in-module
from .cli.commands.audit.remediation.remediation_execute_command import remediation_execute_command  # pylint: disable=no-name-in-module
from .cli.commands.report.report_generate_command import report_generate_command  # pylint: disable=no-name-in-module

# Set up logging with modern patterns
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create console for rich output
console = Console()

# Create Typer app with enhanced configuration
app = typer.Typer(
    name="autodbaudit",
    help="🔒 SQL Server Security Audit Tool - Ultra-granular Architecture",
    add_completion=False,
    rich_markup_mode="rich",
    invoke_without_command=True
)

# Create sub-apps for categorical commands
prepare_app = typer.Typer(
    name="prepare",
    help="🎯 Prepare audit targets and manage connection cache",
    rich_markup_mode="rich"
)

config_app = typer.Typer(
    name="config",
    help="⚙️  Configuration management and validation",
    rich_markup_mode="rich"
)

audit_app = typer.Typer(
    name="audit",
    help="🔍 Audit execution, findings, and remediation",
    rich_markup_mode="rich"
)

report_app = typer.Typer(
    name="report",
    help="📊 Report generation and export",
    rich_markup_mode="rich"
)

# Create sub-sub-apps for audit categories
findings_app = typer.Typer(
    name="findings",
    help="📋 Manage and display audit findings",
    rich_markup_mode="rich"
)

sync_app = typer.Typer(
    name="sync",
    help="🔄 Synchronize audit data",
    rich_markup_mode="rich"
)

remediation_app = typer.Typer(
    name="remediation",
    help="🔧 Execute remediation actions",
    rich_markup_mode="rich"
)

# Add sub-apps to main app
app.add_typer(prepare_app, name="prepare")
app.add_typer(config_app, name="config")
app.add_typer(audit_app, name="audit")
app.add_typer(report_app, name="report")

# Add sub-sub-apps to audit app
audit_app.add_typer(findings_app, name="findings")
audit_app.add_typer(sync_app, name="sync")
audit_app.add_typer(remediation_app, name="remediation")


def get_container() -> Container:
    """Get the dependency injection container with ultra-granular components."""
    config_dir = Path.cwd() / "config"
    return Container(config_dir)


def revert_command():
    """
    Revert localhost to secure state by disabling remote access configurations.

    This command disables WinRM, PowerShell remoting, remote registry, and resets
    firewall rules to secure the local machine against remote access vulnerabilities.
    """
    revert_service = LocalhostRevertService()
    revert_service.revert_unsafe_configurations()


# Register commands to sub-apps
prepare_app.command(
    name="apply",
    help="🔍 Prepare and validate SQL Server audit targets with connection testing"
)(prepare_command)

prepare_app.command(
    name="revert",
    help="🔄 Revert localhost to secure state by disabling remote access configurations"
)(revert_command)

prepare_app.command(
    name="cache-info",
    help="📊 Display current connection cache information and statistics"
)(cache_info_command)

prepare_app.command(
    name="cache-clear",
    help="🧹 Clear all cached connection data and reset cache state"
)(cache_clear_command)

config_app.command(
    name="validate",
    help="✅ Validate configuration files and credentials"
)(config_validate_command)

config_app.command(
    name="summary",
    help="📋 Display comprehensive configuration summary"
)(config_summary_command)

config_app.command(
    name="settings",
    help="🔧 Show current audit settings and timeout configurations"
)(audit_settings_command)

findings_app.command(
    name="list",
    help="📋 List audit findings with filtering options"
)(findings_list_command)

sync_app.command(
    name="run",
    help="🔄 Synchronize audit data between storage locations"
)(sync_command)

remediation_app.command(
    name="execute",
    help="🔧 Execute remediation actions for audit findings"
)(remediation_execute_command)

report_app.command(
    name="generate",
    help="📊 Generate comprehensive audit reports"
)(report_generate_command)


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """
    🔒 AutoDBAudit - Ultra-granular SQL Server Security Audit Tool

    🚀 **Comprehensive Security Auditing for SQL Server Environments**

    This tool provides enterprise-grade security auditing capabilities using modern Python patterns,
    clean architecture principles, and ultra-granular component separation.

    ✨ **Key Features:**
    - 🔍 **Ultra-granular Architecture**: Single-responsibility micro-components (<50 lines each)
    - ⚡ **Dynamic Configuration**: Runtime-adjustable timeouts and audit settings
    - 🔄 **Parallel Processing**: Concurrent target validation and connection testing
    - 🧠 **Intelligent Caching**: TTL-based performance optimization with DB persistence
    - 🔧 **Fallback Scripts**: Automatic PowerShell script generation for manual execution
    - 🛡️ **Elevated Privileges**: Automatic shell elevation detection and handling
    - 🔐 **Secure Credentials**: Encrypted storage with separate SQL/OS credential management

    📁 **Configuration Hierarchy:**
    1. Config file settings (primary)
    2. CLI overrides (secondary)
    3. Reasonable defaults (fallback)

    🏗️ **Architecture:**
    - **Domain Layer**: Pure business logic with Pydantic models
    - **Application Layer**: Use cases and service orchestration
    - **Infrastructure Layer**: External dependencies and persistence
    - **Interface Layer**: CLI, formatters, and user interaction

    � **Commands:**
    - `autodbaudit prepare apply` - Prepare audit targets
    - `autodbaudit prepare cache-info` - View cache statistics  
    - `autodbaudit prepare cache-clear` - Clear all caches
    - `autodbaudit prepare revert` - Secure localhost
    - `autodbaudit config validate` - Validate configuration
    - `autodbaudit config summary` - Show config summary
    - `autodbaudit config settings` - Show audit settings
    - `autodbaudit audit findings list` - List audit findings
    - `autodbaudit audit sync run` - Sync audit data
    - `autodbaudit audit remediation execute` - Execute remediation
    - `autodbaudit report generate` - Generate reports

    🔧 **Quick Start:**
    1. Configure your targets: `autodbaudit config validate`
    2. Prepare audit targets: `autodbaudit prepare apply`
    3. Check cache status: `autodbaudit prepare cache-info`
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


if __name__ == "__main__":
    app()
