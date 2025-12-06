"""
Hotfix domain models.

Contains data structures for tracking hotfix deployments across SQL Server instances.
These models are used by the hotfix planner, executor, and service modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


# ============================================================================
# Enumerations
# ============================================================================

class HotfixRunStatus(Enum):
    """Status of an overall hotfix deployment run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"  # Some targets succeeded, some failed
    FAILED = "failed"
    CANCELLED = "cancelled"


class HotfixTargetStatus(Enum):
    """Status of hotfix deployment to a single server."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    PARTIAL = "partial"  # Some steps succeeded, some failed
    FAILED = "failed"
    SKIPPED = "skipped"


class HotfixStepStatus(Enum):
    """Status of a single installer execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# ============================================================================
# Hotfix Models
# ============================================================================

@dataclass
class HotfixRun:
    """
    Represents a hotfix deployment session across multiple servers.
    
    Attributes:
        id: Unique identifier
        started_at: Timestamp when deployment started
        completed_at: Timestamp when deployment completed
        status: Overall status of the run
        initiated_by: Username who started the deployment
        notes: Optional notes or comments
    """
    id: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: HotfixRunStatus = HotfixRunStatus.PENDING
    initiated_by: str | None = None
    notes: str | None = None


@dataclass
class HotfixTarget:
    """
    Represents a server being patched in a hotfix run.
    
    Attributes:
        id: Unique identifier
        hotfix_run_id: Foreign key to HotfixRun
        server_id: Foreign key to Server
        pre_build: SQL Server build version before patching
        post_build: SQL Server build version after patching
        status: Current status of this target
        requires_restart: Whether server needs restart
        error_message: Error details if failed
    """
    id: int | None = None
    hotfix_run_id: int | None = None
    server_id: int | None = None
    pre_build: str | None = None
    post_build: str | None = None
    status: HotfixTargetStatus = HotfixTargetStatus.PENDING
    requires_restart: bool = False
    error_message: str | None = None


@dataclass
class HotfixStep:
    """
    Represents a single installer execution on a target server.
    
    Attributes:
        id: Unique identifier
        hotfix_target_id: Foreign key to HotfixTarget
        step_order: Sequence number (1, 2, 3...)
        installer_file: Filename of the installer
        description: Human-readable description (e.g., "CU22 for SQL Server 2019")
        status: Current status of this step
        started_at: Timestamp when step started
        completed_at: Timestamp when step completed
        exit_code: Installer exit code
        output: Stdout/stderr output (may be truncated)
    """
    id: int | None = None
    hotfix_target_id: int | None = None
    step_order: int = 1
    installer_file: str = ""
    description: str = ""
    status: HotfixStepStatus = HotfixStepStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    exit_code: int | None = None
    output: str | None = None


# ============================================================================
# Configuration Models
# ============================================================================

@dataclass
class HotfixMapping:
    """
    Mapping from SQL Server version to required hotfix files.
    
    Loaded from config/hotfix_mapping.json.
    
    Attributes:
        version_family: SQL Server version (e.g., "2019", "2022")
        edition_filter: Optional edition filter (e.g., "Standard")
        min_build: Minimum build that needs this update
        target_build: Expected build after applying update
        description: Human-readable description
        files: List of installer files in order
        requires_restart: Whether update requires restart
        notes: Additional notes for operators
    """
    version_family: str
    min_build: str
    target_build: str
    description: str = ""
    edition_filter: str | None = None
    files: list[HotfixFile] = field(default_factory=list)
    requires_restart: bool = True
    notes: str | None = None


@dataclass
class HotfixFile:
    """
    Configuration for a single hotfix installer file.
    
    Attributes:
        filename: Name of the installer file
        path: Relative or UNC path to the file
        order: Execution order (1, 2, 3...)
        required: If True, failure stops further steps
        parameters: CLI arguments for silent install
    """
    filename: str
    path: str = ""
    order: int = 1
    required: bool = True
    parameters: str = "/quiet /IAcceptSQLServerLicenseTerms /Action=Patch /AllInstances"
