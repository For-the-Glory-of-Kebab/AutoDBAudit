"""
Railway-oriented result types for remediation operations.
Following Railway programming patterns with Success/Failure variants.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar, Optional
from dataclasses import dataclass
from datetime import datetime

T = TypeVar('T')
E = TypeVar('E')

@dataclass(frozen=True)
class Success(Generic[T]):
    """Successful remediation operation result."""
    value: T
    metadata: dict[str, Any] | None = None
    execution_time_ms: int | None = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now())

@dataclass(frozen=True)
class Failure(Generic[E]):
    """Failed remediation operation result."""
    error: E
    context: dict[str, Any] | None = None
    recoverable: bool = False
    retry_count: int = 0
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now())

# Type alias for Railway Result
Result = Success[T] | Failure[E]

# Specific result types for remediation operations
@dataclass(frozen=True)
class ScriptExecutionSuccess:
    """Result of successful script execution."""
    target_server: str
    target_instance: str
    script_type: str  # 'tsql' | 'powershell'
    affected_rows: int | None = None
    execution_output: str | None = None
    rollback_script: str | None = None

@dataclass(frozen=True)
class ScriptExecutionFailure:
    """Result of failed script execution."""
    target_server: str
    target_instance: str
    script_type: str
    error_message: str
    error_code: str | None = None
    partial_success: bool = False
    recoverable_actions: list[str] | None = None

@dataclass(frozen=True)
class ConnectionFailure:
    """Result of connection establishment failure."""
    target_server: str
    target_instance: str
    connection_type: str  # 'odbc' | 'psremote'
    attempted_methods: list[str]
    last_error: str
    can_retry: bool = True

@dataclass(frozen=True)
class ValidationFailure:
    """Result of validation failure."""
    target_server: str
    target_instance: str
    validation_type: str  # 'pre_execution' | 'post_execution'
    issues: list[str]
    can_continue: bool = False

@dataclass(frozen=True)
class ExceptionFiltered:
    """Result of exception filtering."""
    target_server: str
    target_instance: str
    filtered_findings: list[str]
    total_findings: int
    reason: str = "exceptionalized"

# Type aliases for common remediation results
ScriptResult = Result[ScriptExecutionSuccess, ScriptExecutionFailure]
ConnectionResult = Result[bool, ConnectionFailure]
ValidationResult = Result[bool, ValidationFailure]
FilterResult = Result[list[dict], ExceptionFiltered]
