"""
Prepare Command CLI - Ultra-modular Command Wiring

This module wires together all prepare-related commands in a clean,
decoupled architecture. Each subcommand lives in its own namespace.
"""

import typer
from typing import List, Optional

from .apply.cli import apply_targets
from .revert.cli import revert_targets
from .status.cli import show_status
from .cache.cli import cache_app

# Create prepare app
prepare_app = typer.Typer(
    name="prepare",
    help="🎯 Prepare audit targets and manage connection cache",
    rich_markup_mode="rich",
    no_args_is_help=True
)

# Add direct commands
prepare_app.command("apply")(apply_targets)
prepare_app.command("revert")(revert_targets)
prepare_app.command("status")(show_status)

# Add sub-app for cache (which has subcommands)
prepare_app.add_typer(cache_app, name="cache")
