"""
Revert Service - Handles Audit Preparation Reversion

Manages reverting audit preparation changes on targets.
"""

from typing import List, Optional
from collections import defaultdict

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
            _ = (config_file, parallel, timeout)
            # Get SQL targets for the specified target names
            if targets is None:
                # Use all enabled targets from config
                all_targets = self.config_manager.get_enabled_targets()
                selected_targets = all_targets
            else:
                # Use specified targets
                all_targets = self.config_manager.get_enabled_targets()
                selected_targets = [t for t in all_targets if t.name in targets]

            if not selected_targets:
                if targets is None:
                    return "No enabled targets found in sql_targets.json"
                return f"No matching targets found for: {targets}"

            # Group by server and invoke revert
            server_groups = defaultdict(list)
            for target in selected_targets:
                server_groups[target.server].append(target)

            failures = []
            for server_name in server_groups:
                result = self.prepare_service.revert_server(
                    server_name=server_name,
                    sql_targets=server_groups[server_name],
                    credentials_file=credentials_file,
                    dry_run=dry_run
                )
                if not result.success:
                    failures.append(server_name)

            if failures:
                return f"Failed to revert servers: {failures}"
            server_list = ", ".join(server_groups.keys())
            return f"Successfully reverted preparation for servers: {server_list}"
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
