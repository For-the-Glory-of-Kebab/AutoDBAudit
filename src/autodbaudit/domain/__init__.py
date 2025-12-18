"""
Domain layer package.

Contains pure data models with no I/O dependencies.
Models can be serialized to/from SQLite via the infrastructure layer.
"""

from autodbaudit.domain.models import (
    # Enums
    AuditStatus,
    RequirementStatus,
    Severity,
    ActionType,
    # Core Models (Phase 1)
    AuditRun,
    Server,
    Instance,
    # Future Models (Phase 2+)
    Requirement,
    RequirementResult,
    Action,
)

# Sync Engine Types (Phase 2+)
from autodbaudit.domain.change_types import (
    FindingStatus,
    ChangeType,
    RiskLevel,
    ActionStatus,
    EntityType,
    MutationType,
    TransitionResult,
    DetectedChange,
    ExceptionInfo,
    SyncStats,
)

from autodbaudit.domain.state_machine import (
    classify_finding_transition,
    classify_exception_change,
    resolve_concurrent_changes,
    is_exception_eligible,
    should_clear_exception_status,
    count_active_issues,
    count_documented_exceptions,
    count_compliant,
)

__all__ = [
    # Original Enums
    "AuditStatus",
    "RequirementStatus",
    "Severity",
    "ActionType",
    # Core Models
    "AuditRun",
    "Server",
    "Instance",
    # Future Models
    "Requirement",
    "RequirementResult",
    "Action",
    # Sync Engine Types
    "FindingStatus",
    "ChangeType",
    "RiskLevel",
    "ActionStatus",
    "EntityType",
    "MutationType",
    "TransitionResult",
    "DetectedChange",
    "ExceptionInfo",
    "SyncStats",
    # State Machine Functions
    "classify_finding_transition",
    "classify_exception_change",
    "resolve_concurrent_changes",
    "is_exception_eligible",
    "should_clear_exception_status",
    "count_active_issues",
    "count_documented_exceptions",
    "count_compliant",
]
