"""
Change Types and Enums for the Sync Engine.

This module defines the core enums and dataclasses used throughout
the sync/diff/action system. It is the single source of truth for
all change-related type definitions.

Architecture Note:
    This is a pure domain module with NO external dependencies.
    It should only contain enums, dataclasses, and type definitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class FindingStatus(str, Enum):
    """
    Status of a compliance finding.

    Discrepant statuses (FAIL, WARN) require action or exception.
    """

    PASS = "PASS"  # Compliant - no action needed
    FAIL = "FAIL"  # Non-compliant - security issue
    WARN = "WARN"  # Needs attention but not critical

    def is_discrepant(self) -> bool:
        """Check if this status indicates a discrepancy."""
        return self in (FindingStatus.FAIL, FindingStatus.WARN)

    @classmethod
    def from_string(cls, value: str | None) -> FindingStatus | None:
        """Parse status from string, handling various formats."""
        if value is None:
            return None
        upper = str(value).upper().strip()
        if upper in ("PASS", "✓", "OK", "COMPLIANT"):
            return cls.PASS
        if upper in ("FAIL", "❌", "FAILED", "NON-COMPLIANT"):
            return cls.FAIL
        if upper in ("WARN", "⚠", "WARNING", "ATTENTION"):
            return cls.WARN
        return None


class ChangeType(str, Enum):
    """
    Type of change detected during sync.

    Ordered by priority (first item = highest priority).
    When multiple changes happen in one sync, higher priority wins.
    """

    # Priority 1 - Compliance changes (most important)
    FIXED = "Fixed"  # FAIL/WARN → PASS
    REGRESSION = "Regression"  # PASS → FAIL/WARN
    NEW_ISSUE = "New"  # (none) → FAIL/WARN

    # Priority 2 - Exception changes
    EXCEPTION_ADDED = "Exception Documented"
    EXCEPTION_REMOVED = "Exception Removed"
    EXCEPTION_UPDATED = "Exception Updated"

    # Priority 3 - Entity mutations
    ENTITY_ADDED = "Added"
    ENTITY_REMOVED = "Removed"
    ENTITY_MODIFIED = "Modified"
    ENTITY_ENABLED = "Enabled"
    ENTITY_DISABLED = "Disabled"

    # Priority 4 - Informational
    SYSTEM_INFO = "System Information"

    # No change / unclassified
    STILL_FAILING = "Still Failing"
    NO_CHANGE = "No Change"
    UNKNOWN = "Unknown"

    @property
    def priority(self) -> int:
        """Get priority for conflict resolution. Lower = higher priority."""
        priorities = {
            self.FIXED: 1,
            self.REGRESSION: 2,
            self.NEW_ISSUE: 3,
            self.EXCEPTION_ADDED: 4,
            self.EXCEPTION_REMOVED: 5,
            self.EXCEPTION_UPDATED: 6,
            self.ENTITY_ADDED: 10,
            self.ENTITY_REMOVED: 11,
            self.ENTITY_MODIFIED: 12,
            self.ENTITY_ENABLED: 13,
            self.ENTITY_DISABLED: 14,
            self.SYSTEM_INFO: 20,
            self.STILL_FAILING: 100,
            self.NO_CHANGE: 101,
            self.UNKNOWN: 999,
        }
        return priorities.get(self, 999)

    @property
    def should_log(self) -> bool:
        """Check if this change type should be logged to action_log."""
        no_log_types = {self.STILL_FAILING, self.NO_CHANGE, self.UNKNOWN}
        return self not in no_log_types

    @property
    def is_closing(self) -> bool:
        """Check if this change type closes/resolves an issue."""
        return self in (self.FIXED, self.EXCEPTION_ADDED)


class RiskLevel(str, Enum):
    """Risk level for findings and changes."""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFO = "Info"

    @property
    def is_actionable(self) -> bool:
        """Check if this risk level requires action."""
        return self in (self.CRITICAL, self.HIGH, self.MEDIUM)


class ActionStatus(str, Enum):
    """Status of an action log entry."""

    OPEN = "open"  # Issue still active
    CLOSED = "closed"  # Issue resolved (fixed)
    EXCEPTION = "exception"  # Documented exception
    PENDING = "pending"  # Needs attention
    REGRESSION = "regression"  # Previously fixed, now failing again


class EntityType(str, Enum):
    """Types of entities tracked by the audit system."""

    SA_ACCOUNT = "SA Account"
    LOGIN = "Login"
    SERVER_ROLE = "Server Role"
    CONFIGURATION = "Configuration"
    SERVICE = "Service"
    DATABASE = "Database"
    DATABASE_USER = "Database User"
    DATABASE_ROLE = "Database Role"
    ORPHANED_USER = "Orphaned User"
    LINKED_SERVER = "Linked Server"
    TRIGGER = "Trigger"
    BACKUP = "Backup"
    PROTOCOL = "Protocol"
    ENCRYPTION = "Encryption"
    AUDIT_SETTING = "Audit Setting"
    INSTANCE = "Instance"


class MutationType(str, Enum):
    """Types of mutations that can occur to entities."""

    ADDED = "Added"
    REMOVED = "Removed"
    RENAMED = "Renamed"
    ENABLED = "Enabled"
    DISABLED = "Disabled"
    MODIFIED = "Modified"
    COMPLIANT = "Became Compliant"
    NON_COMPLIANT = "Became Non-Compliant"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass(frozen=True)
class TransitionResult:
    """
    Result of classifying a state transition.

    Attributes:
        change_type: The type of change detected
        should_log: Whether to create an action log entry
        action_status: Status for the action log entry
        risk_level: Risk level of the change
        description: Human-readable description
    """

    change_type: ChangeType
    should_log: bool
    action_status: ActionStatus = ActionStatus.OPEN
    risk_level: RiskLevel = RiskLevel.MEDIUM
    description: str = ""


@dataclass
class DetectedChange:
    # pylint: disable=too-many-instance-attributes
    """
    A detected change ready for logging.

    Attributes:
        entity_type: Type of entity (Login, Config, etc.)
        entity_key: Unique key for the entity
        change_type: Type of change detected
        description: Human-readable description
        risk_level: Risk level of the change
        old_value: Previous value (if applicable)
        new_value: Current value (if applicable)
        server: Server name
        instance: Instance name
        detected_at: When the change was detected
    """

    entity_type: EntityType
    entity_key: str
    change_type: ChangeType
    description: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    old_value: str | None = None
    new_value: str | None = None
    server: str = ""
    instance: str = ""
    detected_at: datetime = field(default_factory=datetime.now)

    @property
    def should_log(self) -> bool:
        """Check if this change should be logged."""
        return self.change_type.should_log

    @property
    def action_status(self) -> ActionStatus:
        """Derive action status from change type."""
        if self.change_type == ChangeType.FIXED:
            return ActionStatus.CLOSED
        if self.change_type in (
            ChangeType.EXCEPTION_ADDED,
            ChangeType.EXCEPTION_UPDATED,
        ):
            return ActionStatus.EXCEPTION
        if self.change_type == ChangeType.REGRESSION:
            return ActionStatus.REGRESSION
        return ActionStatus.OPEN


@dataclass
class ExceptionInfo:
    """
    Information about an exception (documented risk acceptance).

    Attributes:
        entity_key: Unique key for the entity
        has_justification: Whether there's a justification note
        review_status: Value of the Review Status dropdown
        justification_text: The actual justification text
        last_reviewed: When the exception was last reviewed
    """

    entity_key: str
    has_justification: bool = False
    review_status: str | None = None
    justification_text: str | None = None
    last_reviewed: datetime | None = None

    @property
    def is_valid(self) -> bool:
        """
        Check if this is a valid exception.

        An exception is valid if it has justification OR
        the review status is set to "Exception".
        """
        return (
            self.has_justification
            or (
                self.review_status is not None
                and "Exception" in str(self.review_status)
            )
        )


@dataclass
class SyncStats:
    # pylint: disable=too-many-instance-attributes
    """
    Statistics from a sync operation.

    This is THE data structure all consumers (CLI, Excel, --finalize) use.
    """

    # Current state counts
    total_findings: int = 0
    active_issues: int = 0  # FAIL/WARN without exception
    documented_exceptions: int = 0  # FAIL/WARN with exception
    compliant_items: int = 0  # PASS

    # Changes from baseline (initial audit)
    fixed_since_baseline: int = 0
    regressions_since_baseline: int = 0
    new_issues_since_baseline: int = 0
    exceptions_added_since_baseline: int = 0

    # Changes from last sync
    fixed_since_last: int = 0
    regressions_since_last: int = 0
    new_issues_since_last: int = 0
    exceptions_added_since_last: int = 0
    exceptions_removed_since_last: int = 0
    exceptions_updated_since_last: int = 0

    # Documentation changes (even on compliant items)
    docs_added_since_last: int = 0
    docs_updated_since_last: int = 0
    docs_removed_since_last: int = 0

    # Entity changes (informational)
    entity_changes_count: int = 0

    # Per-sheet breakdowns (sheet_name -> {stat_name -> count})
    sheet_stats: dict[str, dict[str, int]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_findings": self.total_findings,
            "active_issues": self.active_issues,
            "documented_exceptions": self.documented_exceptions,
            "compliant_items": self.compliant_items,
            "baseline": {
                "fixed": self.fixed_since_baseline,
                "regressions": self.regressions_since_baseline,
                "new_issues": self.new_issues_since_baseline,
                "exceptions_added": self.exceptions_added_since_baseline,
            },
            "recent": {
                "fixed": self.fixed_since_last,
                "regressions": self.regressions_since_last,
                "new_issues": self.new_issues_since_last,
                "exceptions_added": self.exceptions_added_since_last,
            },
            "entity_changes": self.entity_changes_count,
        }
