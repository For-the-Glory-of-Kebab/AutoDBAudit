"""
PS Remoting Persistence Layer

Database schema and repository for storing connection profiles
and attempt logs for PowerShell remoting.
"""

import sqlite3
import json
from datetime import datetime, timezone
from typing import List, Optional
from contextlib import contextmanager

from .models import ConnectionProfile, ConnectionAttempt, ServerState, ConnectionMethod


class PSRemotingRepository:
    """
    Repository for PS remoting connection data.

    Handles persistence of successful connection profiles and
    logging of all connection attempts for learning and reuse.
    """

    def __init__(self, db_path: str = "audit_history.db"):
        self.db_path = db_path
        self._ensure_tables()

    @contextmanager
    def _get_connection(self):
        """Get database connection with proper cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()

    def _ensure_tables(self):
        """Ensure PS remoting tables exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # PS Remoting Connection Profiles
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS psremoting_profiles (
                    id INTEGER PRIMARY KEY,
                    server_name TEXT NOT NULL,
                    connection_method TEXT NOT NULL,
                    auth_method TEXT,
                    successful INTEGER NOT NULL DEFAULT 0,
                    last_successful_attempt TEXT,
                    last_attempt TEXT,
                    attempt_count INTEGER DEFAULT 0,
                    sql_targets TEXT,
                    baseline_state TEXT,
                    current_state TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(server_name)
                )
            """)

            # PS Remoting Connection Attempts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS psremoting_attempts (
                    id INTEGER PRIMARY KEY,
                    profile_id INTEGER NOT NULL REFERENCES psremoting_profiles(id) ON DELETE CASCADE,
                    attempt_timestamp TEXT NOT NULL,
                    layer TEXT NOT NULL,
                    connection_method TEXT NOT NULL,
                    auth_method TEXT,
                    success INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT,
                    duration_ms INTEGER,
                    config_changes TEXT,
                    rollback_actions TEXT,
                    manual_script_path TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # PS Remoting Server State
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS psremoting_server_state (
                    id INTEGER PRIMARY KEY,
                    profile_id INTEGER NOT NULL REFERENCES psremoting_profiles(id) ON DELETE CASCADE,
                    state_type TEXT NOT NULL,
                    collected_at TEXT NOT NULL,
                    winrm_service_status TEXT,
                    winrm_service_startup TEXT,
                    winrm_service_account TEXT,
                    winrm_firewall_enabled INTEGER,
                    winrm_firewall_ports TEXT,
                    trusted_hosts TEXT,
                    network_category TEXT,
                    local_account_token_filter INTEGER,
                    allow_unencrypted INTEGER,
                    auth_basic INTEGER,
                    auth_kerberos INTEGER,
                    auth_negotiate INTEGER,
                    auth_certificate INTEGER,
                    auth_credssp INTEGER,
                    auth_digest INTEGER,
                    execution_policy TEXT,
                    enable_lua INTEGER,
                    remote_management_enabled INTEGER,
                    full_state_json TEXT,
                    UNIQUE(profile_id, state_type)
                )
            """)

            # Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_psremoting_profiles_server ON psremoting_profiles(server_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_psremoting_profiles_success ON psremoting_profiles(successful, last_successful_attempt)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_psremoting_attempts_profile ON psremoting_attempts(profile_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_psremoting_attempts_timestamp ON psremoting_attempts(attempt_timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_psremoting_attempts_layer ON psremoting_attempts(layer, success)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_psremoting_server_state_profile ON psremoting_server_state(profile_id, state_type)")

            conn.commit()

    def save_connection_profile(self, profile: ConnectionProfile) -> int:
        """
        Save or update a connection profile.

        Args:
            profile: Connection profile to save

        Returns:
            Profile ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Convert complex fields to JSON
            sql_targets_json = json.dumps(profile.sql_targets) if profile.sql_targets else None
            baseline_state_json = json.dumps(profile.baseline_state) if profile.baseline_state else None
            current_state_json = json.dumps(profile.current_state) if profile.current_state else None

            cursor.execute("""
                INSERT OR REPLACE INTO psremoting_profiles
                (server_name, connection_method, auth_method, successful,
                 last_successful_attempt, last_attempt, attempt_count,
                 sql_targets, baseline_state, current_state, created_at,
                 updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.server_name,
                profile.connection_method.value,
                profile.auth_method,
                1 if profile.successful else 0,
                profile.last_successful_attempt,
                profile.last_attempt,
                profile.attempt_count,
                sql_targets_json,
                baseline_state_json,
                current_state_json,
                profile.created_at,
                profile.updated_at
            ))

            profile_id = cursor.lastrowid
            conn.commit()
            return profile_id

    def get_connection_profile(
        self,
        server_name: str
    ) -> Optional[ConnectionProfile]:
        """
        Retrieve stored connection profile for a server.

        Args:
            server_name: Server to get profile for

        Returns:
            ConnectionProfile if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, server_name, connection_method, auth_method, successful,
                       last_successful_attempt, last_attempt, attempt_count,
                       sql_targets, baseline_state, current_state, created_at,
                       updated_at
                FROM psremoting_profiles
                WHERE server_name = ?
            """, (server_name,))

            row = cursor.fetchone()
            if not row:
                return None

            # Parse JSON fields
            sql_targets = json.loads(row['sql_targets']) if row['sql_targets'] else []
            baseline_state = json.loads(row['baseline_state']) if row['baseline_state'] else None
            current_state = json.loads(row['current_state']) if row['current_state'] else None

            return ConnectionProfile(
                server_name=row['server_name'],
                connection_method=ConnectionMethod(row['connection_method']),
                auth_method=row['auth_method'],
                successful=bool(row['successful']),
                last_successful_attempt=row['last_successful_attempt'],
                last_attempt=row['last_attempt'],
                attempt_count=row['attempt_count'],
                sql_targets=sql_targets,
                baseline_state=baseline_state,
                current_state=current_state,
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )

    def update_connection_profile_success(
        self,
        server_name: str,
        auth_method: str,
        connection_method: ConnectionMethod
    ) -> None:
        """
        Update profile after successful connection.

        Args:
            server_name: Server that connected successfully
            auth_method: Authentication method that worked
            connection_method: Connection method that worked
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE psremoting_profiles
                SET auth_method = ?, connection_method = ?, successful = 1,
                    last_successful_attempt = ?, last_attempt = ?,
                    attempt_count = attempt_count + 1, updated_at = ?
                WHERE server_name = ?
            """, (auth_method, connection_method.value, now, now, now, server_name))
            conn.commit()

    def increment_attempt_count(self, server_name: str) -> None:
        """
        Increment attempt count for a server.

        Args:
            server_name: Server to update
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE psremoting_profiles
                SET attempt_count = attempt_count + 1, last_attempt = ?, updated_at = ?
                WHERE server_name = ?
            """, (now, now, server_name))
            conn.commit()

    def log_connection_attempt(self, attempt: ConnectionAttempt) -> int:
        """
        Log a connection attempt for analysis.

        Args:
            attempt: Attempt details to log

        Returns:
            Attempt ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Convert complex fields to JSON
            config_changes_json = json.dumps(attempt.config_changes) if attempt.config_changes else None
            rollback_actions_json = json.dumps(attempt.rollback_actions) if attempt.rollback_actions else None

            cursor.execute("""
                INSERT INTO psremoting_attempts
                (profile_id, attempt_timestamp, layer, connection_method,
                 auth_method, success, error_message, duration_ms,
                 config_changes, rollback_actions, manual_script_path,
                 created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                attempt.profile_id,
                attempt.attempt_timestamp,
                attempt.layer,
                attempt.connection_method.value,
                attempt.auth_method,
                1 if attempt.success else 0,
                attempt.error_message,
                attempt.duration_ms,
                config_changes_json,
                rollback_actions_json,
                attempt.manual_script_path,
                attempt.created_at
            ))

            attempt_id = cursor.lastrowid
            conn.commit()
            return attempt_id

    def get_recent_attempts(
        self,
        server_name: str,
        limit: int = 10
    ) -> List[ConnectionAttempt]:
        """
        Get recent connection attempts for a server.

        Args:
            server_name: Server to get attempts for
            limit: Maximum number of attempts to return

        Returns:
            List of recent connection attempts
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.id, a.profile_id, a.attempt_timestamp, a.layer,
                       a.connection_method, a.auth_method, a.success,
                       a.error_message, a.duration_ms, a.config_changes,
                       a.rollback_actions, a.manual_script_path, a.created_at
                FROM psremoting_attempts a
                JOIN psremoting_profiles p ON a.profile_id = p.id
                WHERE p.server_name = ?
                ORDER BY a.attempt_timestamp DESC
                LIMIT ?
            """, (server_name, limit))

            attempts = []
            for row in cursor.fetchall():
                # Parse JSON fields
                config_changes = json.loads(row['config_changes']) if row['config_changes'] else None
                rollback_actions = json.loads(row['rollback_actions']) if row['rollback_actions'] else None

                attempts.append(ConnectionAttempt(
                    profile_id=row['profile_id'],
                    attempt_timestamp=row['attempt_timestamp'],
                    layer=row['layer'],
                    connection_method=ConnectionMethod(row['connection_method']),
                    auth_method=row['auth_method'],
                    success=bool(row['success']),
                    error_message=row['error_message'],
                    duration_ms=row['duration_ms'],
                    config_changes=config_changes,
                    rollback_actions=rollback_actions,
                    manual_script_path=row['manual_script_path'],
                    created_at=row['created_at']
                ))

            return attempts

    def get_successful_servers(self) -> List[str]:
        """
        Get list of servers with successful connection profiles.

        Returns:
            List of server names with stored profiles
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT server_name FROM psremoting_profiles
                WHERE successful = 1
                ORDER BY last_successful_attempt DESC
            """)

            return [row['server_name'] for row in cursor.fetchall()]

    def get_all_profiles(self) -> List[ConnectionProfile]:
        """
        Get all connection profiles.

        Returns:
            List of all connection profiles
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, server_name, connection_method, auth_method, successful,
                       last_successful_attempt, last_attempt, attempt_count,
                       sql_targets, baseline_state, current_state, created_at,
                       updated_at
                FROM psremoting_profiles
                ORDER BY server_name
            """)

            profiles = []
            for row in cursor.fetchall():
                # Parse JSON fields
                sql_targets = json.loads(row['sql_targets']) if row['sql_targets'] else []
                baseline_state = json.loads(row['baseline_state']) if row['baseline_state'] else None
                current_state = json.loads(row['current_state']) if row['current_state'] else None

                profiles.append(ConnectionProfile(
                    server_name=row['server_name'],
                    connection_method=ConnectionMethod(row['connection_method']),
                    auth_method=row['auth_method'],
                    successful=bool(row['successful']),
                    last_successful_attempt=row['last_successful_attempt'],
                    last_attempt=row['last_attempt'],
                    attempt_count=row['attempt_count'],
                    sql_targets=sql_targets,
                    baseline_state=baseline_state,
                    current_state=current_state,
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                ))

            return profiles

    def save_server_state(self, state: ServerState) -> int:
        """
        Save server state snapshot.

        Args:
            state: Server state to save

        Returns:
            State record ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Convert complex fields to JSON
            firewall_ports_json = json.dumps(state.winrm_firewall_ports) if state.winrm_firewall_ports else None
            full_state_json = json.dumps(state.full_state_json) if state.full_state_json else None

            cursor.execute("""
                INSERT OR REPLACE INTO psremoting_server_state
                (profile_id, state_type, collected_at, winrm_service_status,
                 winrm_service_startup, winrm_service_account,
                 winrm_firewall_enabled, winrm_firewall_ports, trusted_hosts,
                 network_category, local_account_token_filter,
                 allow_unencrypted, auth_basic, auth_kerberos, auth_negotiate,
                 auth_certificate, auth_credssp, auth_digest, execution_policy,
                 enable_lua, remote_management_enabled, full_state_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?)
            """, (
                state.profile_id,
                state.state_type,
                state.collected_at,
                state.winrm_service_status,
                state.winrm_service_startup,
                state.winrm_service_account,
                state.winrm_firewall_enabled,
                firewall_ports_json,
                state.trusted_hosts,
                state.network_category,
                state.local_account_token_filter,
                state.allow_unencrypted,
                state.auth_basic,
                state.auth_kerberos,
                state.auth_negotiate,
                state.auth_certificate,
                state.auth_credssp,
                state.auth_digest,
                state.execution_policy,
                state.enable_lua,
                state.remote_management_enabled,
                full_state_json
            ))

            state_id = cursor.lastrowid
            conn.commit()
            return state_id

    def get_server_state(self, profile_id: int, state_type: str) -> Optional[ServerState]:
        """
        Get server state snapshot.

        Args:
            profile_id: Profile ID
            state_type: Type of state ('baseline' or 'current')

        Returns:
            ServerState if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT profile_id, state_type, collected_at, winrm_service_status,
                       winrm_service_startup, winrm_service_account,
                       winrm_firewall_enabled, winrm_firewall_ports,
                       trusted_hosts, network_category,
                       local_account_token_filter, allow_unencrypted, auth_basic,
                       auth_kerberos, auth_negotiate, auth_certificate,
                       auth_credssp, auth_digest, execution_policy, enable_lua,
                       remote_management_enabled, full_state_json
                FROM psremoting_server_state
                WHERE profile_id = ? AND state_type = ?
                ORDER BY collected_at DESC
                LIMIT 1
            """, (profile_id, state_type))

            row = cursor.fetchone()
            if not row:
                return None

            # Parse JSON fields
            firewall_ports = json.loads(row['winrm_firewall_ports']) if row['winrm_firewall_ports'] else None
            full_state_json = json.loads(row['full_state_json']) if row['full_state_json'] else None

            return ServerState(
                profile_id=row['profile_id'],
                state_type=row['state_type'],
                collected_at=row['collected_at'],
                winrm_service_status=row['winrm_service_status'],
                winrm_service_startup=row['winrm_service_startup'],
                winrm_service_account=row['winrm_service_account'],
                winrm_firewall_enabled=row['winrm_firewall_enabled'],
                winrm_firewall_ports=firewall_ports,
                trusted_hosts=row['trusted_hosts'],
                network_category=row['network_category'],
                local_account_token_filter=row['local_account_token_filter'],
                allow_unencrypted=row['allow_unencrypted'],
                auth_basic=row['auth_basic'],
                auth_kerberos=row['auth_kerberos'],
                auth_negotiate=row['auth_negotiate'],
                auth_certificate=row['auth_certificate'],
                auth_credssp=row['auth_credssp'],
                auth_digest=row['auth_digest'],
                execution_policy=row['execution_policy'],
                enable_lua=row['enable_lua'],
                remote_management_enabled=row['remote_management_enabled'],
                full_state_json=full_state_json
            )
