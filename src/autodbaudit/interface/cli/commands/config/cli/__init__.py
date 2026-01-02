"""
Config Command CLI - Ultra-modular Configuration Management

Wires together all configuration-related commands in a clean,
decoupled architecture. Each subcommand lives in its own namespace.
"""

import typer

from .validate.cli import config_validate
from .summary.cli import config_summary
from .settings.cli import audit_settings

# Create config app
config_app = typer.Typer(
    name="config",
    help="⚙️ Configuration validation and management",
    rich_markup_mode="rich",
    no_args_is_help=True
)

# Add sub-commands
config_app.command("validate")(config_validate)
config_app.command("summary")(config_summary)
config_app.command("settings")(audit_settings)
