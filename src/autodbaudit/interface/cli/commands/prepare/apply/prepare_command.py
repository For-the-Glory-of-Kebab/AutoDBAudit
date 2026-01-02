"""
Prepare command - Ultra-granular prepare command implementation.

This module provides the main prepare command that orchestrates all
ultra-granular components for target preparation.
"""

import logging
from typing import List, Optional

from autodbaudit.application.container import Container
from autodbaudit.domain.config.audit_settings import AuditSettings
from autodbaudit.interface.cli.services.localhost_revert_service import LocalhostRevertService
from autodbaudit.interface.cli.utils.shell_elevation import ShellElevationService
from autodbaudit.interface.cli.utils.powershell_generator import PowerShellScriptGenerator
from autodbaudit.interface.cli.formatters.result_formatters import PrepareResultFormatter, CacheStatisticsFormatter
from .target_resolver import TargetResolver
from .parallel_processor import ParallelProcessor
from .fallback_script_generator import FallbackScriptGenerator

logger = logging.getLogger(__name__)


class PrepareCommand:  # pylint: disable=too-many-instance-attributes
    """
    Ultra-granular prepare command implementation.

    Handles target preparation with dynamic timeouts, parallel processing,
    and fallback script generation.
    """

    def __init__(
        self,
        container: Container,
        audit_settings: Optional[AuditSettings] = None
    ):
        """
        Initialize the prepare command.

        Args:
            container: Application dependency container
            audit_settings: Dynamic audit settings for timeouts
        """
        self.container = container
        self.audit_settings = audit_settings or AuditSettings()

        # Ultra-granular service dependencies
        self.shell_elevation = ShellElevationService()
        self.script_generator = PowerShellScriptGenerator()
        self.result_formatter = PrepareResultFormatter()
        self.cache_formatter = CacheStatisticsFormatter()

        # Ultra-granular logic components
        self.target_resolver = TargetResolver(container)
        self.parallel_processor = ParallelProcessor(container, self.audit_settings)
        self.fallback_generator = FallbackScriptGenerator(self.script_generator)
        self.revert_service = LocalhostRevertService()

    def execute(  # pylint: disable=too-many-positional-arguments,too-many-arguments
        self,
        target_names: Optional[List[str]] = None,
        verbose: bool = False,
        force_refresh: bool = False,
        show_cache_stats: bool = False,
        require_elevation: bool = False,
        generate_fallback_scripts: bool = True,
        revert_localhost: bool = False
    ) -> None:
        """
        Execute the prepare command.

        Args:
            target_names: Specific targets to prepare
            verbose: Enable verbose output
            force_refresh: Force cache refresh
            show_cache_stats: Show cache statistics
            require_elevation: Require elevated shell
            generate_fallback_scripts: Generate PowerShell scripts on failure
            revert_localhost: Revert localhost to secure state
        """
        # Handle revert operation
        if revert_localhost:
            self.revert_service.revert_unsafe_configurations()
            return

        # Check elevation if required
        if require_elevation or self.audit_settings.require_elevated_shell:
            if not self.shell_elevation.require_elevation("SQL Server target preparation"):
                return

        # Clear cache if requested
        if force_refresh:
            self.container.prepare_service.clear_cache()
            print("[yellow]🧹 Connection cache cleared.[/yellow]")

        # Get targets to prepare
        targets = self.target_resolver.resolve_targets(target_names)
        if not targets:
            print("[yellow]⚠️  No enabled targets found in configuration.[/yellow]")
            return

        print(f"[blue]🔍 Preparing {len(targets)} target(s) with ultra-granular services...[/blue]")

        # Prepare targets with dynamic settings
        self._configure_dynamic_timeouts()

        if self.audit_settings.enable_parallel_processing:
            results = self.parallel_processor.process_targets_parallel(targets)
        else:
            results = self.container.prepare_service.prepare_targets(targets)

        # Display results
        self.result_formatter.display_results_table(
            results, verbose=verbose, show_cache_stats=show_cache_stats
        )

        # Generate fallback scripts for failed targets if enabled
        if generate_fallback_scripts and self.audit_settings.enable_fallback_scripts:
            self.fallback_generator.generate_for_failures(results)

        # Show cache statistics if requested
        if show_cache_stats or verbose:
            cache_stats = self.container.prepare_service.get_cache_stats()
            self.cache_formatter.display_cache_stats(cache_stats)

    def _configure_dynamic_timeouts(self) -> None:
        """Configure dynamic timeouts in the prepare service."""
        # Update timeouts in the prepare service components
        # This would require extending the prepare service to accept timeout settings
        logger.debug("Configured dynamic timeouts: %s", self.audit_settings.timeouts)
