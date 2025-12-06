"""
Hotfix module package.

Contains components for SQL Server hotfix orchestration:
- Planner: Determines which servers need updates
- Executor: Runs installers on remote servers
- Service: High-level orchestration API
- Models: Data structures for hotfix tracking
"""

from autodbaudit.hotfix.models import (
    # Enums
    HotfixRunStatus,
    HotfixTargetStatus,
    HotfixStepStatus,
    # Models
    HotfixRun,
    HotfixTarget,
    HotfixStep,
    HotfixMapping,
    HotfixFile,
)
from autodbaudit.hotfix.planner import HotfixPlanner
from autodbaudit.hotfix.executor import HotfixExecutor
from autodbaudit.hotfix.service import HotfixService

__all__ = [
    # Enums
    "HotfixRunStatus",
    "HotfixTargetStatus",
    "HotfixStepStatus",
    # Models
    "HotfixRun",
    "HotfixTarget",
    "HotfixStep",
    "HotfixMapping",
    "HotfixFile",
    # Services
    "HotfixPlanner",
    "HotfixExecutor",
    "HotfixService",
]
