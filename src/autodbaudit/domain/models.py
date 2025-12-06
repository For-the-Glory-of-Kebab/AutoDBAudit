"""
Domain models for AutoDBAudit.

This module contains the core business entities that represent:
- Audit runs and their results
- Requirements and compliance status
- Actions taken and exceptions documented
- Server and instance information

These models are pure data structures with no I/O dependencies.
They can be serialized to/from SQLite via the infrastructure layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


# ============================================================================
# Enumerations
# ============================================================================

class AuditStatus(Enum):
    """Status of an audit run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RequirementStatus(Enum):
    """Status of a requirement check result."""
    PASS = "pass"
    FAIL = "fail"
    EXCEPTION = "exception"
    NOT_APPLICABLE = "not_applicable"
    PENDING = "pending"


class Severity(Enum):
    """Severity level for requirements and findings."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class ActionType(Enum):
    """Type of remediation action."""
    APPLIED = "applied"
    SKIPPED = "skipped"
    FAILED = "failed"


# ============================================================================
# Core Domain Models
# ============================================================================

@dataclass
class AuditRun:
    """
    Represents a single audit execution.
    
    Attributes:
        id: Unique identifier (auto-generated)
        organization: Name of the organization being audited
        audit_date: Date of the audit (ISO format: YYYY-MM-DD)
        started_at: Timestamp when audit started
        completed_at: Timestamp when audit completed (None if in progress)
        status: Current status of the audit run
        config_hash: SHA256 hash of config used (for reproducibility)
        notes: Optional notes or comments
    """
    id: int | None = None
    organization: str = ""
    audit_date: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: AuditStatus = AuditStatus.PENDING
    config_hash: str | None = None
    notes: str | None = None


@dataclass
class Server:
    """
    Represents a SQL Server host machine.
    
    Attributes:
        id: Unique identifier
        hostname: Server hostname or IP address
        first_seen_audit_id: Audit run when this server was first discovered
        last_seen_audit_id: Most recent audit run that included this server
        is_active: Whether the server is currently active (not decommissioned)
    """
    id: int | None = None
    hostname: str = ""
    first_seen_audit_id: int | None = None
    last_seen_audit_id: int | None = None
    is_active: bool = True


@dataclass
class Instance:
    """
    Represents a SQL Server instance on a server.
    
    Attributes:
        id: Unique identifier
        server_id: Foreign key to Server
        instance_name: Instance name (empty string for default instance)
        sql_version: Full version string (e.g., "15.0.4298.1")
        sql_edition: Edition name (e.g., "Standard", "Enterprise")
        sql_version_major: Major version number (10=2008, 15=2019, 16=2022)
    """
    id: int | None = None
    server_id: int | None = None
    instance_name: str = ""
    sql_version: str | None = None
    sql_edition: str | None = None
    sql_version_major: int | None = None
    first_seen_audit_id: int | None = None
    last_seen_audit_id: int | None = None


@dataclass
class Requirement:
    """
    Represents a security/compliance requirement from db-requirements.md.
    
    Attributes:
        id: Requirement number (e.g., 4, 10, 15)
        code: Short code identifier (e.g., "Req04", "Req10")
        title: Brief title of the requirement
        description: Full description of what is checked
        severity: Severity level if requirement fails
        category: Category grouping (e.g., "Authentication", "Features")
    """
    id: int
    code: str
    title: str
    description: str = ""
    severity: Severity = Severity.WARNING
    category: str | None = None


@dataclass
class RequirementResult:
    """
    Result of checking a requirement against a specific instance.
    
    Attributes:
        id: Unique identifier
        audit_run_id: Foreign key to AuditRun
        instance_id: Foreign key to Instance
        requirement_id: Foreign key to Requirement
        status: Result status (pass/fail/exception/not_applicable)
        finding: Human-readable description of what was found
        evidence: Raw data/query output (JSON string)
        checked_at: Timestamp when the check was performed
    """
    id: int | None = None
    audit_run_id: int | None = None
    instance_id: int | None = None
    requirement_id: int | None = None
    status: RequirementStatus = RequirementStatus.PENDING
    finding: str | None = None
    evidence: str | None = None
    checked_at: datetime | None = None


@dataclass
class Action:
    """
    Represents a remediation action taken.
    
    Attributes:
        id: Unique identifier
        audit_run_id: Foreign key to AuditRun
        instance_id: Foreign key to Instance
        requirement_id: Foreign key to Requirement
        script_file: Path to the remediation script
        action_type: Type of action (applied/skipped/failed)
        executed_at: Timestamp when action was executed
        result_message: Output or error message
        executed_by: Username who performed the action
    """
    id: int | None = None
    audit_run_id: int | None = None
    instance_id: int | None = None
    requirement_id: int | None = None
    script_file: str | None = None
    action_type: ActionType = ActionType.SKIPPED
    executed_at: datetime | None = None
    result_message: str | None = None
    executed_by: str | None = None


@dataclass
class Exception_:
    """
    Represents a documented exception (intentional non-fix).
    
    Note: Named Exception_ to avoid collision with built-in Exception.
    
    Attributes:
        id: Unique identifier
        audit_run_id: Foreign key to AuditRun
        instance_id: Foreign key to Instance
        requirement_id: Foreign key to Requirement
        reason: Justification for the exception
        approved_by: Who approved the exception
        approved_at: Timestamp of approval
        expires_at: Optional expiry date for the exception
    """
    id: int | None = None
    audit_run_id: int | None = None
    instance_id: int | None = None
    requirement_id: int | None = None
    reason: str = ""
    approved_by: str | None = None
    approved_at: datetime | None = None
    expires_at: datetime | None = None


# ============================================================================
# Convenience type aliases
# ============================================================================

# For SQLite row data before conversion to model
RawRow = dict[str, Any]
