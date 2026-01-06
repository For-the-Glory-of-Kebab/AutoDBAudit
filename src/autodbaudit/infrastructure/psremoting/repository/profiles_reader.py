"""
Profile read operations for PS remoting.
"""

import json
from typing import Optional, List

from ..models import ConnectionProfile, ConnectionMethod
from .base import RepositoryBase


class ProfilesReader(RepositoryBase):
    """Read-only profile queries."""

    def get_connection_profile(self, server_name: str) -> Optional[ConnectionProfile]:
        """Fetch a connection profile by server name."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, server_name, connection_method, protocol, port, credential_type,
                       auth_method, successful, last_successful_attempt, last_attempt,
                       attempt_count, sql_targets, baseline_state, current_state,
                       created_at, updated_at
                FROM psremoting_profiles
                WHERE server_name = ?
                """,
                (server_name,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            sql_targets = json.loads(row["sql_targets"]) if row["sql_targets"] else []
            baseline = json.loads(row["baseline_state"]) if row["baseline_state"] else None
            current = json.loads(row["current_state"]) if row["current_state"] else None

            return ConnectionProfile(
                id=row["id"],
                server_name=row["server_name"],
                connection_method=ConnectionMethod(row["connection_method"]),
                auth_method=row["auth_method"],
                protocol=row["protocol"],
                port=row["port"],
                credential_type=row["credential_type"],
                successful=bool(row["successful"]),
                last_successful_attempt=row["last_successful_attempt"],
                last_attempt=row["last_attempt"],
                attempt_count=row["attempt_count"],
                sql_targets=sql_targets or [],
                baseline_state=baseline,
                current_state=current,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def get_successful_servers(self) -> List[str]:
        """Return server names with successful profiles."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT server_name FROM psremoting_profiles WHERE successful = 1")
            rows = cursor.fetchall()
            return [row["server_name"] for row in rows]

    def get_all_profiles(self) -> List[ConnectionProfile]:
        """Return all connection profiles."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, server_name, connection_method, protocol, port, credential_type,
                       auth_method, successful, last_successful_attempt, last_attempt,
                       attempt_count, sql_targets, baseline_state, current_state,
                       created_at, updated_at
                FROM psremoting_profiles
                ORDER BY server_name
                """
            )
            rows = cursor.fetchall()

            profiles: List[ConnectionProfile] = []
            for row in rows:
                sql_targets = json.loads(row["sql_targets"]) if row["sql_targets"] else []
                baseline = json.loads(row["baseline_state"]) if row["baseline_state"] else None
                current = json.loads(row["current_state"]) if row["current_state"] else None
                profiles.append(
                    ConnectionProfile(
                        id=row["id"],
                        server_name=row["server_name"],
                        connection_method=ConnectionMethod(row["connection_method"]),
                        auth_method=row["auth_method"],
                        protocol=row["protocol"],
                        port=row["port"],
                        credential_type=row["credential_type"],
                        successful=bool(row["successful"]),
                        last_successful_attempt=row["last_successful_attempt"],
                        last_attempt=row["last_attempt"],
                        attempt_count=row["attempt_count"],
                        sql_targets=sql_targets or [],
                        baseline_state=baseline,
                        current_state=current,
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )
            return profiles
