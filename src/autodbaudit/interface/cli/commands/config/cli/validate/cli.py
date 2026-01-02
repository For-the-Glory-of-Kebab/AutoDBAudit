"""
Validate Command Function - Configuration Validation

Handles configuration validation command.
"""

import logging
from typing import Optional

import typer

from autodbaudit.application.container import Container
from ...services.config_validate_command import ConfigValidateCommand

logger = logging.getLogger(__name__)


def config_validate(
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Perform strict validation with additional checks."
    )
):
    """
    Validate all configuration files with comprehensive checks.

    This command serves as the single source of truth for configuration validation,
    ensuring all config files are consistent, valid, and properly structured.

    Performs checks on:
    - Audit configuration integrity
    - SQL targets schema validation
    - Credentials encryption and accessibility
    - Cross-references between configurations
    """
    container = Container()
    command = ConfigValidateCommand(container)

    try:
        command.execute(strict=strict)
    except Exception as e:
        logger.error("Config validation failed: %s", e)
        print(f"[red]❌ Error:[/red] {e}")
        raise typer.Exit(1)
