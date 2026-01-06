"""
Profile write/update operations for PS remoting.
"""

import json
from datetime import datetime, timezone
from ..models import ConnectionProfile, ConnectionMethod
from .base import RepositoryBase
from .profiles_reader import ProfilesReader


class ProfilesWriter(RepositoryBase):
    """Create/update profile records."""

    def save_connection_profile(self, profile: ConnectionProfile) -> int:
        """Save or update a connection profile."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            sql_targets_json = json.dumps(profile.sql_targets) if profile.sql_targets else None
            baseline_json = json.dumps(profile.baseline_state) if profile.baseline_state else None
            current_json = json.dumps(profile.current_state) if profile.current_state else None

            cursor.execute(
                """
                INSERT INTO psremoting_profiles
                (server_name, connection_method, protocol, port, credential_type,
                 auth_method, successful, last_successful_attempt, last_attempt,
                 attempt_count, sql_targets, baseline_state, current_state,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(server_name) DO UPDATE SET
                    connection_method = excluded.connection_method,
                    protocol = excluded.protocol,
                    port = excluded.port,
                    credential_type = excluded.credential_type,
                    auth_method = excluded.auth_method,
                    successful = excluded.successful,
                    last_successful_attempt = excluded.last_successful_attempt,
                    last_attempt = excluded.last_attempt,
                    attempt_count = excluded.attempt_count,
                    sql_targets = excluded.sql_targets,
                    baseline_state = excluded.baseline_state,
                    current_state = excluded.current_state,
                    updated_at = excluded.updated_at
                """,
                (
                    profile.server_name,
                    self._cm_value(profile.connection_method),
                    profile.protocol,
                    profile.port,
                    profile.credential_type,
                    profile.auth_method,
                    1 if profile.successful else 0,
                    profile.last_successful_attempt,
                    profile.last_attempt,
                    profile.attempt_count,
                    sql_targets_json,
                    baseline_json,
                    current_json,
                    profile.created_at,
                    profile.updated_at,
                ),
            )
            profile_id = cursor.lastrowid
            conn.commit()
            return int(profile_id or 0)

    def ensure_profile(self, server_name: str) -> int:
        """Ensure a profile record exists for the server."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO psremoting_profiles
                (server_name, connection_method, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (server_name, ConnectionMethod.POWERSHELL_REMOTING.value, now, now),
            )
            conn.commit()

        reader = ProfilesReader(self.db_path)  # type: ignore[arg-type]
        profile = reader.get_connection_profile(server_name)
        return int(profile.id) if profile and profile.id else 0

    def update_connection_profile_success(self, server_name: str, connection_method: str) -> None:
        """Mark profile as successful."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE psremoting_profiles
                SET successful = 1,
                    last_successful_attempt = ?,
                    updated_at = ?,
                    connection_method = ?
                WHERE server_name = ?
                """,
                (now, now, connection_method, server_name),
            )
            conn.commit()

    def increment_attempt_count(self, server_name: str) -> None:
        """Increment attempt count and update last_attempt timestamp."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE psremoting_profiles
                SET attempt_count = attempt_count + 1, last_attempt = ?, updated_at = ?
                WHERE server_name = ?
                """,
                (now, now, server_name),
            )
            conn.commit()

    def update_profile_after_attempt(
        self, profile_id: int, success: bool, attempt_time: str
    ) -> None:
        """Update profile attempt stats after an attempt."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE psremoting_profiles
                SET attempt_count = attempt_count + 1,
                    last_attempt = ?,
                    last_successful_attempt = CASE WHEN ? THEN ? ELSE last_successful_attempt END,
                    successful = CASE WHEN ? THEN 1 ELSE successful END,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    attempt_time,
                    1 if success else 0,
                    attempt_time,
                    1 if success else 0,
                    attempt_time,
                    profile_id,
                ),
            )
            conn.commit()
