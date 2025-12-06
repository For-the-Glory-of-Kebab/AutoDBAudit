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

__all__ = [
    # Enums
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
]
