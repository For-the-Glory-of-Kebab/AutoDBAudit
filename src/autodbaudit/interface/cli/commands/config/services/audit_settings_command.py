"""
Audit settings command - Ultra-granular audit settings management logic.

This module provides specialized functionality for managing
dynamic audit settings and timeouts.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from autodbaudit.application.container import Container
from autodbaudit.domain.config.audit_settings import AuditSettings

logger = logging.getLogger(__name__)


@dataclass
class SettingsUpdate:
    """Settings update parameters."""
    powershell_timeout: Optional[int] = None
    tsql_timeout: Optional[int] = None
    enable_parallel: Optional[bool] = None
    max_parallel: Optional[int] = None
    require_elevation: Optional[bool] = None


class AuditSettingsCommand:
    """
    Ultra-granular audit settings management command.

    Handles display and modification of dynamic audit settings.
    """

    def __init__(self, container: Container):
        """
        Initialize the audit settings command.

        Args:
            container: Application dependency container
        """
        self.container = container

    def execute(
        self,
        show_current: bool = True,
        updates: Optional[SettingsUpdate] = None
    ) -> None:
        """
        Execute audit settings management.

        Args:
            show_current: Display current settings
            updates: Settings updates to apply
        """
        current_settings = self.container.audit_settings

        if show_current:
            self._display_current_settings(current_settings)

        # Update settings if provided
        updated = False
        if updates:
            if updates.powershell_timeout is not None:
                current_settings.timeouts.powershell_command_timeout = updates.powershell_timeout
                updated = True
            if updates.tsql_timeout is not None:
                current_settings.timeouts.tsql_query_timeout = updates.tsql_timeout
                updated = True
            if updates.enable_parallel is not None:
                current_settings.enable_parallel_processing = updates.enable_parallel
                updated = True
            if updates.max_parallel is not None:
                current_settings.max_parallel_targets = updates.max_parallel
                updated = True
            if updates.require_elevation is not None:
                current_settings.require_elevated_shell = updates.require_elevation
                updated = True

        if updated:
            print("[green]✅ Audit settings updated successfully[/green]")
            if show_current:
                self._display_current_settings(current_settings)
        elif not show_current:
            print("[yellow]⚠️  No settings were modified[/yellow]")

    def _display_current_settings(self, settings: AuditSettings) -> None:
        """Display current audit settings."""
        print("[blue]🔧 Current Audit Settings:[/blue]")
        print(f"  PowerShell Timeout: {settings.timeouts.powershell_command_timeout}s")
        print(f"  T-SQL Timeout: {settings.timeouts.tsql_query_timeout}s")
        print(f"  Connection Test Timeout: {settings.timeouts.connection_test_timeout}s")
        print(f"  OS Detection Timeout: {settings.timeouts.os_detection_timeout}s")
        parallel_status = "Enabled" if settings.enable_parallel_processing else "Disabled"
        print(f"  Parallel Processing: {parallel_status}")
        print(f"  Max Parallel Targets: {settings.max_parallel_targets}")
        print(f"  Require Elevated Shell: {'Yes' if settings.require_elevated_shell else 'No'}")
        enable_fallback = "Yes" if settings.enable_fallback_scripts else "No"
        print(f"  Enable Fallback Scripts: {enable_fallback}")
