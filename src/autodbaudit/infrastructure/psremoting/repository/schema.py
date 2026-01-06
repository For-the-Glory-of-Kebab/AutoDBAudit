"""
Schema creation and column backfill for psremoting persistence.
"""
# pylint: disable=line-too-long

import sqlite3


def ensure_tables(cursor: sqlite3.Cursor) -> None:
    """Create psremoting tables if missing."""
    cursor.execute(
        """
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
        """
    )

    cursor.execute(
        """
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
        """
    )

    cursor.execute(
        """
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
        """
    )

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_psremoting_profiles_server ON psremoting_profiles(server_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_psremoting_profiles_success ON psremoting_profiles(successful, last_successful_attempt)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_psremoting_attempts_profile ON psremoting_attempts(profile_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_psremoting_attempts_timestamp ON psremoting_attempts(attempt_timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_psremoting_attempts_layer ON psremoting_attempts(layer, success)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_psremoting_server_state_profile ON psremoting_server_state(profile_id, state_type)")


def ensure_columns(cursor: sqlite3.Cursor) -> None:
    """Add newly introduced columns to existing tables to avoid runtime KeyErrors."""
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
