"""
Hotfix planning module.

Determines which SQL Server instances need updates and creates
a deployment plan based on the hotfix mapping configuration.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autodbaudit.hotfix.models import HotfixMapping, HotfixTarget, HotfixStep

logger = logging.getLogger(__name__)


class HotfixPlanner:
    """
    Plans hotfix deployments by comparing current versions to mapping config.
    
    Workflow:
    1. Load hotfix mapping from config/hotfix_mapping.json
    2. Query current build versions from audit data or direct connection
    3. Compare each instance against mapping to determine needed updates
    4. Generate HotfixTarget and HotfixStep records for execution
    
    Usage:
        planner = HotfixPlanner(mapping_file="config/hotfix_mapping.json")
        
        # Create plan for all servers needing updates
        plan = planner.create_plan(servers=["PROD-SQL1", "PROD-SQL2"])
        
        # Review plan before execution
        for target in plan:
            print(f"{target.server}: {target.pre_build} -> {target.post_build}")
    """
    
    def __init__(
        self,
        mapping_file: str | Path = "config/hotfix_mapping.json",
        hotfixes_dir: str | Path = "hotfixes"
    ):
        """
        Initialize hotfix planner.
        
        Args:
            mapping_file: Path to hotfix mapping configuration
            hotfixes_dir: Directory containing hotfix installer files
        """
        self.mapping_file = Path(mapping_file)
        self.hotfixes_dir = Path(hotfixes_dir)
        self._mappings: list[HotfixMapping] = []
        logger.info("HotfixPlanner initialized with mapping: %s", self.mapping_file)
    
    def load_mappings(self) -> list[HotfixMapping]:
        """
        Load hotfix mappings from configuration file.
        
        Returns:
            List of HotfixMapping objects
            
        Raises:
            FileNotFoundError: If mapping file doesn't exist
            ValueError: If mapping file is invalid
        """
        # TODO: Implement - parse config/hotfix_mapping.json
        raise NotImplementedError("load_mappings not yet implemented")
    
    def get_mapping_for_version(
        self,
        version_family: str,
        current_build: str
    ) -> HotfixMapping | None:
        """
        Find applicable mapping for a version.
        
        Args:
            version_family: SQL Server version (e.g., "2019", "2022")
            current_build: Current build string (e.g., "15.0.4298.1")
            
        Returns:
            HotfixMapping if update needed, None if up-to-date
        """
        # TODO: Implement
        raise NotImplementedError("get_mapping_for_version not yet implemented")
    
    def create_plan(
        self,
        servers: list[str] | None = None,
        include_up_to_date: bool = False
    ) -> list[HotfixTarget]:
        """
        Create deployment plan for specified or all servers.
        
        Args:
            servers: List of server names (None = all active servers)
            include_up_to_date: Include servers already at target version
            
        Returns:
            List of HotfixTarget records with associated HotfixSteps
        """
        # TODO: Implement
        raise NotImplementedError("create_plan not yet implemented")
    
    def validate_plan(self, targets: list[HotfixTarget]) -> list[str]:
        """
        Validate a deployment plan before execution.
        
        Checks:
        - All installer files exist
        - No unsupported versions
        - Required permissions available
        
        Args:
            targets: List of HotfixTarget to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        # TODO: Implement
        raise NotImplementedError("validate_plan not yet implemented")
