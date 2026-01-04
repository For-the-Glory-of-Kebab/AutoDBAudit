# pylint: disable=line-too-long,too-many-arguments,too-many-positional-arguments
"""
PS Remoting Persistence Layer

Database schema and repository for storing connection profiles
and attempt logs for PowerShell remoting.
"""

import sqlite3
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional
from contextlib import contextmanager

from .models import ConnectionProfile, ConnectionAttempt, ServerState, ConnectionMethod

logger = logging.getLogger(__name__)

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
                    protocol TEXT,
                    port INTEGER,
                    credential_type TEXT,
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
                    server_name TEXT,
                    attempt_timestamp TEXT NOT NULL,
                    layer TEXT NOT NULL,
                    connection_method TEXT NOT NULL,
                    protocol TEXT,
                    port INTEGER,
                    credential_type TEXT,
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

            self._ensure_columns(cursor)
            conn.commit()

    def _ensure_columns(self, cursor: sqlite3.Cursor) -> None:
        """
        Add newly introduced columns to existing tables to avoid runtime KeyErrors.
        """
        cursor.execute("PRAGMA table_info(psremoting_profiles)")
        profile_cols = {row["name"] for row in cursor.fetchall()}
        if "protocol" not in profile_cols:
            cursor.execute("ALTER TABLE psremoting_profiles ADD COLUMN protocol TEXT")
        if "port" not in profile_cols:
            cursor.execute("ALTER TABLE psremoting_profiles ADD COLUMN port INTEGER")
        if "credential_type" not in profile_cols:
            cursor.execute("ALTER TABLE psremoting_profiles ADD COLUMN credential_type TEXT")

        cursor.execute("PRAGMA table_info(psremoting_attempts)")
        attempt_cols = {row["name"] for row in cursor.fetchall()}
        if "server_name" not in attempt_cols:
            cursor.execute("ALTER TABLE psremoting_attempts ADD COLUMN server_name TEXT")
        if "protocol" not in attempt_cols:
            cursor.execute("ALTER TABLE psremoting_attempts ADD COLUMN protocol TEXT")
        if "port" not in attempt_cols:
            cursor.execute("ALTER TABLE psremoting_attempts ADD COLUMN port INTEGER")
        if "credential_type" not in attempt_cols:
            cursor.execute("ALTER TABLE psremoting_attempts ADD COLUMN credential_type TEXT")

    @staticmethod
    def _cm_value(method: Optional[ConnectionMethod]) -> Optional[str]:
        """Normalize connection_method to string."""
        if method is None:
            return None
        return method.value if hasattr(method, "value") else str(method)

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
                (server_name, connection_method, protocol, port, credential_type,
                 auth_method, successful, last_successful_attempt, last_attempt,
                 attempt_count, sql_targets, baseline_state, current_state,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
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
                baseline_state_json,
                current_state_json,
                profile.created_at,
                profile.updated_at
            ))

            profile_id = cursor.lastrowid
            conn.commit()
            return int(profile_id or 0)
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
                SELECT id, server_name, connection_method, protocol, port,
                       credential_type, auth_method, successful,
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
                id=row['id'],
                server_name=row['server_name'],
                connection_method=ConnectionMethod(row['connection_method']) if row['connection_method'] else ConnectionMethod.POWERSHELL_REMOTING,
                protocol=row['protocol'],
                port=row['port'],
                credential_type=row['credential_type'],
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

    def ensure_profile(self, server_name: str) -> int:
        """Ensure a profile row exists for a server and return its id."""
        existing = self.get_connection_profile(server_name)
        if existing and existing.id:
            return existing.id

        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute("""
                INSERT OR IGNORE INTO psremoting_profiles
                (server_name, connection_method, protocol, port, credential_type,
                 auth_method, successful, last_successful_attempt, last_attempt,
                 attempt_count, sql_targets, baseline_state, current_state,
                 created_at, updated_at)
                VALUES (?, ?, NULL, NULL, NULL, ?, 0, NULL, NULL, 0, NULL, NULL, NULL, ?, ?)
            """, (server_name, ConnectionMethod.POWERSHELL_REMOTING.value, None, now, now))
            conn.commit()

            cursor.execute(
                "SELECT id FROM psremoting_profiles WHERE server_name = ?",
                (server_name,)
            )
            row = cursor.fetchone()
            return int(row['id']) if row and row['id'] is not None else 0

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
            now = datetime.now(timezone.utc).isoformat()

            cursor.execute("""
                INSERT INTO psremoting_attempts
                (profile_id, server_name, attempt_timestamp, layer, connection_method,
                 protocol, port, credential_type, auth_method, success, error_message,
                 duration_ms, config_changes, rollback_actions, manual_script_path,
                 created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
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
                attempt.created_at or now
            ))

            attempt_id = cursor.lastrowid
            conn.commit()
            return int(attempt_id or 0)

    def update_profile_after_attempt(
        self,
        server_name: str,
        success: bool,
        auth_method: Optional[str] = None,
        connection_method: Optional[ConnectionMethod] = None,
        last_attempt: Optional[str] = None
    ) -> None:
        """Update profile metadata after an attempt."""
        now = last_attempt or datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE psremoting_profiles
                SET attempt_count = attempt_count + 1,
                    last_attempt = ?,
                    updated_at = ?,
                    successful = CASE WHEN ? THEN 1 ELSE successful END,
                    last_successful_attempt = CASE WHEN ? THEN ? ELSE last_successful_attempt END,
                    auth_method = CASE WHEN ? THEN ? ELSE auth_method END,
                    connection_method = CASE WHEN ? THEN ? ELSE connection_method END
                WHERE server_name = ?
                """,
                (
                    now,
                    now,
                    1 if success else 0,
                    1 if success else 0,
                    now,
                    1 if auth_method else 0,
                    auth_method,
                    1 if connection_method else 0,
                    self._cm_value(connection_method),
                    server_name,
                ),
            )
            conn.commit()

    def log_attempts(self, attempts: List[ConnectionAttempt], profile_id: Optional[int] = None) -> None:
        """Persist a batch of attempts when a profile id is available."""
        if profile_id is None:
            return
        for attempt in attempts:
            attempt.profile_id = profile_id
            try:
                self.log_connection_attempt(attempt)
                self.update_profile_after_attempt(
                    server_name=attempt.server_name or "",
                    success=attempt.success,
                    auth_method=attempt.auth_method,
                    connection_method=attempt.connection_method,
                    last_attempt=attempt.attempt_timestamp or attempt.created_at,
                )
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Failed to log attempt for %s: %s", attempt.server_name, exc)

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
                       a.connection_method, a.protocol, a.port, a.credential_type,
                       a.server_name,
                       a.auth_method, a.success,
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
                    server_name=row['server_name'],
                    protocol=row['protocol'],
                    port=row['port'],
                    credential_type=row['credential_type'],
                    attempt_timestamp=row['attempt_timestamp'],
                    attempted_at=row['attempt_timestamp'],
                    layer=row['layer'],
                    connection_method=ConnectionMethod(row['connection_method']) if row['connection_method'] else None,
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
                       protocol, port, credential_type,
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
                    id=row['id'],
                    server_name=row['server_name'],
                    connection_method=ConnectionMethod(row['connection_method']) if row['connection_method'] else ConnectionMethod.POWERSHELL_REMOTING,
                    auth_method=row['auth_method'],
                    protocol=row['protocol'],
                    port=row['port'],
                    credential_type=row['credential_type'],
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
            return int(state_id or 0)

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
