"""
State Tracker micro-component.
Tracks remediation execution state and metadata snapshots.
Ultra-granular component (<50 lines) following Railway patterns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime

from autodbaudit.infrastructure.remediation.results import Result, Success, Failure

if TYPE_CHECKING:
    from sqlite3 import Connection

@dataclass(frozen=True)
class RemediationRunContext:
    """Context for creating a remediation run."""
    audit_run_id: int
    aggressiveness_level: int
    target_server: str
    target_instance: str

@dataclass(frozen=True)
class RemediationItemContext:
    """Context for recording a remediation item."""
    run_id: int
    finding_type: str
    entity_name: str
    script_executed: str
    execution_result: str
    rollback_script: str | None = None

@dataclass(frozen=True)
class StateTracker:
    """
    Tracks remediation execution state and creates metadata snapshots.
    Railway-oriented: returns Success with tracking result or Failure.
    """

    def create_remediation_run(
        self,
        db_connection: Connection,
        context: RemediationRunContext
    ) -> Result[int, str]:
        """
        Create a new remediation run record.
        Returns Success with run ID or Failure with error.
        """
        try:
            cursor = db_connection.cursor()
            cursor.execute(
                """
                INSERT INTO remediation_runs (
                    audit_run_id, aggressiveness_level, target_server,
                    target_instance, started_at, status
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    context.audit_run_id, context.aggressiveness_level,
                    context.target_server, context.target_instance,
                    datetime.now(), 'running'
                )
            )
            run_id = cursor.lastrowid
            if run_id is None:
                return Failure("Failed to get remediation run ID")
            db_connection.commit()
            return Success(run_id)
        except Exception as e:
            return Failure(f"Failed to create remediation run: {str(e)}")

    def record_remediation_item(
        self,
        db_connection: Connection,
        context: RemediationItemContext
    ) -> Result[bool, str]:
        """
        Record individual remediation item execution.
        Returns Success or Failure.
        """
        try:
            db_connection.execute(
                """
                INSERT INTO remediation_items (
                    remediation_run_id, finding_type, entity_name,
                    script_executed, execution_result, rollback_script,
                    executed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    context.run_id, context.finding_type, context.entity_name,
                    context.script_executed, context.execution_result,
                    context.rollback_script, datetime.now()
                )
            )
            db_connection.commit()
            return Success(True)
        except Exception as e:
            return Failure(f"Failed to record remediation item: {str(e)}")

    def update_run_status(
        self,
        db_connection: Connection,
        run_id: int,
        status: str,
        error_message: str | None = None
    ) -> Result[bool, str]:
        """
        Update remediation run status.
        Returns Success or Failure.
        """
        try:
            db_connection.execute(
                """
                UPDATE remediation_runs
                SET status = ?, completed_at = ?, error_message = ?
                WHERE id = ?
                """,
                (status, datetime.now(), error_message, run_id)
            )
            db_connection.commit()
            return Success(True)
        except Exception as e:
            return Failure(f"Failed to update run status: {str(e)}")
