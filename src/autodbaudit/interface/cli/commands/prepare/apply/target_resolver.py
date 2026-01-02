"""
Target resolver - Ultra-granular target resolution logic.

This module provides specialized functionality for resolving target names
to target objects from configuration.
"""

import logging
from typing import List, Optional

from autodbaudit.application.container import Container

logger = logging.getLogger(__name__)


class TargetResolver:
    """Ultra-granular target resolution logic."""

    def __init__(self, container: Container):
        self.container = container

    def resolve_targets(self, target_names: Optional[List[str]]) -> List:
        """Resolve target names to target objects."""
        if target_names:
            return self._resolve_specific_targets(target_names)
        return self.container.config_manager.get_enabled_targets()

    def _resolve_specific_targets(self, target_names: List[str]) -> List:
        """Resolve specific target names."""
        targets = []
        for name in target_names:
            target = self.container.config_manager.get_connection_info_for_target(name)
            if target:
                targets.append(target)
            else:
                print(f"[red]❌ Error:[/red] Target '{name}' not found in configuration.")
                return []
        return targets
