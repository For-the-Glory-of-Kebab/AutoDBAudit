"""
Hotfix orchestration service.

High-level service that coordinates the hotfix workflow:
planning, execution, logging, and resume/retry operations.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from autodbaudit.hotfix.planner import HotfixPlanner
from autodbaudit.hotfix.executor import HotfixExecutor
from autodbaudit.hotfix.models import HotfixRun, HotfixRunStatus

if TYPE_CHECKING:
    from autodbaudit.hotfix.models import HotfixTarget
    from autodbaudit.application.history_service import HistoryService

logger = logging.getLogger(__name__)


class HotfixService:
    """
    High-level hotfix orchestration service.
    
    Coordinates the complete hotfix workflow:
    1. Load configuration and create deployment plan
    2. Validate plan (check files exist, permissions, etc.)
    3. Execute deployments with concurrency control
    4. Log all operations to SQLite history
    5. Support resume after interruption
    6. Support retry of failed targets
    
    Usage:
        service = HotfixService(history_service)
        
        # Plan and review
        plan = service.create_plan()
        service.print_plan(plan)
        
        # Execute with progress updates
        def on_progress(msg):
            print(msg)
        
        results = service.deploy(plan, progress_callback=on_progress)
        
        # Resume after cancellation
        service.resume()
        
        # Retry failed only
        service.retry_failed()
    """
    
    def __init__(
        self,
        history_service: HistoryService | None = None,
        mapping_file: str | Path = "config/hotfix_mapping.json",
        hotfixes_dir: str | Path = "hotfixes",
        max_concurrent: int = 3,
    ):
        """
        Initialize hotfix service.
        
        Args:
            history_service: Service for persisting deployment history
            mapping_file: Path to hotfix mapping configuration
            hotfixes_dir: Directory containing installer files
            max_concurrent: Maximum parallel server deployments
        """
        self.history_service = history_service
        self.planner = HotfixPlanner(mapping_file, hotfixes_dir)
        self.executor = HotfixExecutor(max_concurrent=max_concurrent)
        self._current_run: HotfixRun | None = None
        logger.info("HotfixService initialized")
    
    def create_plan(
        self,
        servers: list[str] | None = None
    ) -> list[HotfixTarget]:
        """
        Create deployment plan for specified or all servers.
        
        Args:
            servers: List of server names (None = all active servers)
            
        Returns:
            List of HotfixTarget with planned steps
        """
        return self.planner.create_plan(servers)
    
    def validate(self, targets: list[HotfixTarget]) -> bool:
        """
        Validate deployment plan.
        
        Args:
            targets: Planned targets to validate
            
        Returns:
            True if plan is valid
            
        Raises:
            ValueError: If plan has validation errors
        """
        errors = self.planner.validate_plan(targets)
        if errors:
            for error in errors:
                logger.error("Validation error: %s", error)
            raise ValueError(f"Plan validation failed with {len(errors)} errors")
        return True
    
    def deploy(
        self,
        targets: list[HotfixTarget],
        dry_run: bool = False,
        progress_callback: Callable[[str], None] | None = None
    ) -> HotfixRun:
        """
        Execute hotfix deployment.
        
        Args:
            targets: Planned targets to deploy
            dry_run: If True, log actions without executing
            progress_callback: Optional callback for real-time progress
            
        Returns:
            HotfixRun record with final status
        """
        # TODO: Implement deployment orchestration
        raise NotImplementedError("deploy not yet implemented")
    
    def resume(self) -> HotfixRun | None:
        """
        Resume last interrupted deployment.
        
        Loads state from history and continues from last completed target.
        
        Returns:
            HotfixRun if resumed, None if no interrupted run found
        """
        # TODO: Implement
        raise NotImplementedError("resume not yet implemented")
    
    def retry_failed(self) -> HotfixRun | None:
        """
        Retry only failed targets from last run.
        
        Returns:
            HotfixRun if retried, None if no failed targets found
        """
        # TODO: Implement
        raise NotImplementedError("retry_failed not yet implemented")
    
    def get_deployment_status(self, run_id: int | None = None) -> dict:
        """
        Get status summary of a deployment run.
        
        Args:
            run_id: Specific run ID, or None for latest
            
        Returns:
            Dictionary with status summary
        """
        # TODO: Implement
        raise NotImplementedError("get_deployment_status not yet implemented")
