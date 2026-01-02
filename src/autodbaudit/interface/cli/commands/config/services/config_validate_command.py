"""
Config validate command - Ultra-granular config validation logic.

This module provides specialized functionality for validating
all configuration files with comprehensive checks.
"""

import logging
from typing import List

import typer

from autodbaudit.application.container import Container
from ..formatters.result_formatters import ValidationResultFormatter

logger = logging.getLogger(__name__)


class ConfigValidateCommand:
    """
    Ultra-granular config validation command.

    Handles comprehensive configuration validation with strict mode.
    """

    def __init__(self, container: Container):
        """
        Initialize the config validate command.

        Args:
            container: Application dependency container
        """
        self.container = container
        self.formatter = ValidationResultFormatter()

    def execute(self, strict: bool = False) -> None:
        """
        Execute config validation.

        Args:
            strict: Enable strict validation mode
        """
        print("[blue]🔍 Validating configuration files...[/blue]")

        errors = self.container.config_manager.validate_all_configs()

        if strict:
            # Additional strict validation checks
            strict_errors = self._perform_strict_validation()
            errors.extend(strict_errors)

        self.formatter.display_validation_results(errors, strict)

        if errors:
            raise typer.Exit(1)

    def _perform_strict_validation(self) -> List[str]:
        """
        Perform additional strict validation checks.

        Returns:
            List of validation errors
        """
        errors = []

        try:
            # Check if prepare service can be initialized
            prepare_service = self.container.prepare_service
            if not prepare_service:
                errors.append("Prepare service cannot be initialized")

            # Check if all ultra-granular components are available
            if not self.container.os_detector:
                errors.append("OS detection service not available")
            if not self.container.connection_tester:
                errors.append("Connection testing service not available")
            if not self.container.method_selector:
                errors.append("Method selector service not available")
            if not self.container.cache_manager:
                errors.append("Cache manager not available")

            # Check target configurations
            targets = self.container.config_manager.get_all_targets()
            for target in targets:
                if not target.name or not target.server:
                    errors.append(f"Target '{target.name}' has incomplete configuration")

        except Exception as e:
            errors.append(f"Strict validation failed: {e}")

        return errors
