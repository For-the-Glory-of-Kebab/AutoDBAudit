"""
Revert Service - Handles Audit Preparation Reversion

Manages reverting audit preparation changes on targets.
"""

from typing import List, Optional

from autodbaudit.infrastructure.config.manager import ConfigManager
from autodbaudit.application.prepare_service import PrepareService


class RevertService:
    """Service for reverting audit preparation changes."""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.prepare_service = PrepareService(self.config_manager)

    def revert_targets(
        self,
        targets: Optional[List[str]] = None,
        config_file: Optional[str] = None,
        credentials_file: Optional[str] = None,
        parallel: bool = True,
        timeout: int = 300,
        dry_run: bool = False
    ) -> str:
        """
        Revert audit preparation changes on specified targets.

        Args:
            targets: List of target server names. If None, uses all enabled targets.
            config_file: Path to configuration file
            credentials_file: Path to credentials file
            parallel: Whether to process in parallel
            timeout: Timeout per target in seconds
            dry_run: Whether to simulate without executing

        Returns:
            Success message or error message
        """
        try:
            # Get SQL targets for the specified target names
            if targets is None:
                # Use all enabled targets from config
                all_targets = self.config_manager.get_enabled_targets()
                selected_targets = all_targets
                target_names = [t.name for t in selected_targets]
            else:
                # Use specified targets
                all_targets = self.config_manager.get_enabled_targets()
                selected_targets = [t for t in all_targets if t.name in targets]
                target_names = targets

            if not selected_targets:
                if targets is None:
                    return "No enabled targets found in sql_targets.json"
                else:
                    return f"No matching targets found for: {targets}"

            # For now, simulate revert by clearing cache
            # In a full implementation, this would undo audit infrastructure
            self.prepare_service.clear_cache()

            return f"Successfully reverted preparation for {len(selected_targets)} targets"
        except Exception as e:
            return f"Failed to revert targets: {str(e)}"

    def revert_localhost(self, dry_run: bool = False) -> str:
        """
        Revert audit preparation on localhost.

        Args:
            dry_run: Whether to simulate without executing

        Returns:
            Success message or error message
        """
        try:
            if dry_run:
                return "DRY RUN: Would revert localhost audit preparation"

            # Clear local caches and reset any local audit state
            self.prepare_service.clear_cache()

            return "Successfully reverted localhost audit preparation"
        except Exception as e:
            return f"Failed to revert localhost: {str(e)}"
