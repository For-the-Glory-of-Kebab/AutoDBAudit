"""
Attempt logging helpers for PS remoting.
"""

import json
from datetime import datetime, timezone
from typing import List, Optional

from ..models import ConnectionAttempt
from .base import RepositoryBase


class AttemptsMixin(RepositoryBase):
    """Logging operations for attempts."""

    def log_connection_attempt(self, attempt: ConnectionAttempt) -> int:
        """Log a single connection attempt."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            config_changes_json = (
                json.dumps(attempt.config_changes) if attempt.config_changes else None
            )
            rollback_actions_json = (
                json.dumps(attempt.rollback_actions) if attempt.rollback_actions else None
            )
            now = datetime.now(timezone.utc).isoformat()

            cursor.execute(
                """
                INSERT INTO psremoting_attempts
                (profile_id, server_name, attempt_timestamp, layer, connection_method,
                 protocol, port, credential_type, auth_method, success, error_message,
                 duration_ms, config_changes, rollback_actions, manual_script_path,
                 created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt.profile_id,
                    attempt.server_name,
                    attempt.attempt_timestamp or now,
                    attempt.layer or "",
                    self._cm_value(attempt.connection_method) or "",
                    attempt.protocol,
                    attempt.port,
                    attempt.credential_type,
                    attempt.auth_method,
                    1 if attempt.success else 0,
                    attempt.error_message,
                    attempt.duration_ms,
                    config_changes_json,
                    rollback_actions_json,
                    attempt.manual_script_path,
                    attempt.created_at or now,
                ),
            )

            attempt_id = cursor.lastrowid
            conn.commit()
            return int(attempt_id or 0)

    def log_attempts(
        self, attempts: List[ConnectionAttempt], profile_id: Optional[int] = None
    ) -> None:
        """Log multiple attempts, applying profile_id if provided."""
        for attempt in attempts:
            if profile_id and not attempt.profile_id:
                attempt.profile_id = profile_id
            self.log_connection_attempt(attempt)

    def get_recent_attempts(self, limit: int = 50) -> List[ConnectionAttempt]:
        """Retrieve the most recent connection attempts."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT profile_id, server_name, attempt_timestamp, layer, connection_method,
                       protocol, port, credential_type, auth_method, success, error_message,
                       duration_ms, config_changes, rollback_actions, manual_script_path,
                       created_at
                FROM psremoting_attempts
                ORDER BY attempt_timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()

            attempts_list: List[ConnectionAttempt] = []
            for row in rows:
                attempts_list.append(
                    ConnectionAttempt(
                        profile_id=row["profile_id"],
                        server_name=row["server_name"],
                        attempt_timestamp=row["attempt_timestamp"],
                        layer=row["layer"],
                        connection_method=row["connection_method"],
                        protocol=row["protocol"],
                        port=row["port"],
                        credential_type=row["credential_type"],
                        auth_method=row["auth_method"],
                        success=bool(row["success"]),
                        error_message=row["error_message"],
                        duration_ms=row["duration_ms"],
                        config_changes=json.loads(row["config_changes"])
                        if row["config_changes"]
                        else None,
                        rollback_actions=json.loads(row["rollback_actions"])
                        if row["rollback_actions"]
                        else None,
                        manual_script_path=row["manual_script_path"],
                        created_at=row["created_at"],
                    )
                )
            return attempts_list
