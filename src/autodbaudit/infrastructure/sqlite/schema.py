"""
Extended SQLite schema for comprehensive audit data.

This module adds additional tables beyond the basic history_store.py:
- Server info (OS, paths, memory)
- Configuration settings (sp_configure)
- Logins and role memberships
- Database users and roles
- Linked servers
- Triggers
- Backup history
- Annotations (manual notes that persist across audits)

Schema Version: 2
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Schema version 2 DDL statements
SCHEMA_V2_TABLES = """
-- ============================================================================
-- Server Information (OS, Installation)
-- ============================================================================

CREATE TABLE IF NOT EXISTS server_info (
    id INTEGER PRIMARY KEY,
    instance_id INTEGER NOT NULL UNIQUE REFERENCES instances(id) ON DELETE CASCADE,
    audit_run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
    -- OS Info
    os_platform TEXT,
    os_name TEXT,
    os_version TEXT,
    -- Hardware
    cpu_count INTEGER,
    memory_gb REAL,
    -- SQL Installation
    sql_start_time TEXT,
    collation TEXT,
    windows_auth_only INTEGER,
    is_clustered INTEGER,
    is_hadr_enabled INTEGER,
    -- Paths
    default_data_path TEXT,
    default_log_path TEXT,
    default_backup_path TEXT,
    -- Timestamps
    collected_at TEXT NOT NULL
);

-- ============================================================================
-- Configuration Settings (sp_configure)
-- ============================================================================

CREATE TABLE IF NOT EXISTS config_settings (
    id INTEGER PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id) ON DELETE CASCADE,
    audit_run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
    setting_name TEXT NOT NULL,
    configured_value INTEGER,
    running_value INTEGER,
    min_value INTEGER,
    max_value INTEGER,
    is_dynamic INTEGER,
    is_advanced INTEGER,
    description TEXT,
    -- Assessment
    required_value INTEGER,
    status TEXT,  -- 'pass', 'fail', 'warn', 'exception'
    risk_level TEXT, -- 'critical', 'high', 'medium', 'low'
    collected_at TEXT NOT NULL,
    UNIQUE(instance_id, audit_run_id, setting_name)
);

-- ============================================================================
-- Server Logins
-- ============================================================================

CREATE TABLE IF NOT EXISTS logins (
    id INTEGER PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id) ON DELETE CASCADE,
    audit_run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
    login_name TEXT NOT NULL,
    principal_id INTEGER,
    sid TEXT,
    login_type TEXT,  -- WINDOWS_LOGIN, SQL_LOGIN, WINDOWS_GROUP, CERTIFICATE
    is_disabled INTEGER,
    default_database TEXT,
    default_language TEXT,
    create_date TEXT,
    modify_date TEXT,
    -- Password info (SQL logins only)
    password_last_set TEXT,
    is_expired INTEGER,
    is_locked INTEGER,
    must_change_password INTEGER,
    bad_password_count INTEGER,
    password_policy_enforced INTEGER,
    password_expiration_enabled INTEGER,
    is_empty_password INTEGER,
    -- SA account flags
    is_sa_account INTEGER,
    is_sa_renamed INTEGER,
    -- Timestamps
    collected_at TEXT NOT NULL,
    UNIQUE(instance_id, audit_run_id, login_name)
);

-- ============================================================================
-- Server Role Memberships
-- ============================================================================

CREATE TABLE IF NOT EXISTS login_role_memberships (
    id INTEGER PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id) ON DELETE CASCADE,
    audit_run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
    role_name TEXT NOT NULL,
    member_login TEXT NOT NULL,
    member_type TEXT,
    member_disabled INTEGER,
    member_create_date TEXT,
    collected_at TEXT NOT NULL,
    UNIQUE(instance_id, audit_run_id, role_name, member_login)
);

-- ============================================================================
-- Databases
-- ============================================================================

CREATE TABLE IF NOT EXISTS databases (
    id INTEGER PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id) ON DELETE CASCADE,
    audit_run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
    database_id INTEGER,
    database_name TEXT NOT NULL,
    owner TEXT,
    create_date TEXT,
    collation TEXT,
    recovery_model TEXT,
    compatibility_level INTEGER,
    state TEXT,
    user_access TEXT,
    -- Size
    data_size_mb REAL,
    log_size_mb REAL,
    -- Flags
    is_auto_close INTEGER,
    is_auto_shrink INTEGER,
    is_read_only INTEGER,
    is_trustworthy INTEGER,
    is_db_chaining INTEGER,
    is_broker_enabled INTEGER,
    is_encrypted INTEGER,
    containment TEXT,
    -- Timestamps
    collected_at TEXT NOT NULL,
    UNIQUE(instance_id, audit_run_id, database_name)
);

-- ============================================================================
-- Database Users
-- ============================================================================

CREATE TABLE IF NOT EXISTS database_users (
    id INTEGER PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id) ON DELETE CASCADE,
    audit_run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
    database_name TEXT NOT NULL,
    user_name TEXT NOT NULL,
    principal_id INTEGER,
    user_type TEXT,
    default_schema TEXT,
    mapped_login TEXT,
    authentication_type TEXT,
    create_date TEXT,
    modify_date TEXT,
    -- Flags
    is_orphaned INTEGER,
    is_guest_enabled INTEGER,
    collected_at TEXT NOT NULL,
    UNIQUE(instance_id, audit_run_id, database_name, user_name)
);

-- ============================================================================
-- Database Role Memberships
-- ============================================================================

CREATE TABLE IF NOT EXISTS database_role_memberships (
    id INTEGER PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id) ON DELETE CASCADE,
    audit_run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
    database_name TEXT NOT NULL,
    role_name TEXT NOT NULL,
    member_name TEXT NOT NULL,
    member_type TEXT,
    collected_at TEXT NOT NULL,
    UNIQUE(instance_id, audit_run_id, database_name, role_name, member_name)
);

-- ============================================================================
-- Linked Servers
-- ============================================================================

CREATE TABLE IF NOT EXISTS linked_servers (
    id INTEGER PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id) ON DELETE CASCADE,
    audit_run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
    linked_server_name TEXT NOT NULL,
    product TEXT,
    provider TEXT,
    data_source TEXT,
    catalog TEXT,
    location TEXT,
    -- Flags
    is_remote_login_enabled INTEGER,
    is_rpc_out_enabled INTEGER,
    is_data_access_enabled INTEGER,
    -- Timestamps
    modify_date TEXT,
    collected_at TEXT NOT NULL,
    UNIQUE(instance_id, audit_run_id, linked_server_name)
);

-- ============================================================================
-- Linked Server Login Mappings
-- ============================================================================

CREATE TABLE IF NOT EXISTS linked_server_logins (
    id INTEGER PRIMARY KEY,
    linked_server_id INTEGER NOT NULL REFERENCES linked_servers(id) ON DELETE CASCADE,
    local_login TEXT,  -- NULL means "all logins"
    remote_login TEXT,
    uses_self_credential INTEGER,
    risk_level TEXT,  -- 'high_privilege', 'normal'
    collected_at TEXT NOT NULL
);

-- ============================================================================
-- Triggers
-- ============================================================================

CREATE TABLE IF NOT EXISTS triggers (
    id INTEGER PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id) ON DELETE CASCADE,
    audit_run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
    trigger_level TEXT NOT NULL,  -- 'SERVER' or 'DATABASE'
    database_name TEXT DEFAULT '',  -- Empty string for server triggers (SQLite UNIQUE workaround)
    trigger_name TEXT NOT NULL,
    parent_object TEXT,
    trigger_type TEXT,
    event_type TEXT,
    is_disabled INTEGER,
    is_instead_of INTEGER,
    is_ms_shipped INTEGER,
    create_date TEXT,
    modify_date TEXT,
    collected_at TEXT NOT NULL,
    UNIQUE(instance_id, audit_run_id, trigger_level, database_name, trigger_name)
);

-- ============================================================================
-- Backup History
-- ============================================================================

CREATE TABLE IF NOT EXISTS backup_history (
    id INTEGER PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id) ON DELETE CASCADE,
    audit_run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
    database_name TEXT NOT NULL,
    recovery_model TEXT,
    database_state TEXT,
    -- Last backup info (per type)
    last_full_backup_date TEXT,
    last_full_backup_size_mb REAL,
    last_diff_backup_date TEXT,
    last_log_backup_date TEXT,
    days_since_full_backup INTEGER,
    -- Job info
    has_backup_job INTEGER,
    backup_job_name TEXT,
    backup_job_enabled INTEGER,
    last_job_run_date TEXT,
    last_job_status TEXT,
    last_job_message TEXT,
    collected_at TEXT NOT NULL,
    UNIQUE(instance_id, audit_run_id, database_name)
);

-- ============================================================================
-- Audit Settings
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_settings (
    id INTEGER PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id) ON DELETE CASCADE,
    audit_run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
    default_trace_enabled INTEGER,
    c2_audit_mode INTEGER,
    common_criteria INTEGER,
    contained_db_auth INTEGER,
    collected_at TEXT NOT NULL,
    UNIQUE(instance_id, audit_run_id)
);

-- ============================================================================
-- Annotations (Manual Notes - Persisted Across Audits)
-- ============================================================================

CREATE TABLE IF NOT EXISTS annotations (
    id INTEGER PRIMARY KEY,
    entity_type TEXT NOT NULL,        -- 'login', 'linked_server', 'trigger', etc.
    entity_key TEXT NOT NULL,         -- Composite key: 'server|instance|name'
    field_name TEXT NOT NULL,         -- 'description', 'reason', 'justification', etc.
    field_value TEXT,
    status_override TEXT,             -- NULL, 'exception', 'approved', etc.
    created_at TEXT NOT NULL,
    modified_at TEXT,
    modified_by TEXT,
    UNIQUE(entity_type, entity_key, field_name)
);

-- ============================================================================
-- Annotation History (Track Changes)
-- ============================================================================

CREATE TABLE IF NOT EXISTS annotation_history (
    id INTEGER PRIMARY KEY,
    annotation_id INTEGER NOT NULL REFERENCES annotations(id) ON DELETE CASCADE,
    old_value TEXT,
    new_value TEXT,
    old_status TEXT,
    new_status TEXT,
    changed_at TEXT NOT NULL,
    changed_by TEXT,
    audit_run_id INTEGER REFERENCES audit_runs(id)
);

-- ============================================================================
-- Services (Collected via WMI/PowerShell, stored here)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sql_services (
    id INTEGER PRIMARY KEY,
    server_id INTEGER NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    audit_run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
    service_type TEXT NOT NULL,      -- 'Engine', 'Agent', 'Browser', 'FullText', etc.
    service_name TEXT NOT NULL,
    display_name TEXT,
    status TEXT,                     -- 'Running', 'Stopped', etc.
    startup_type TEXT,               -- 'Automatic', 'Manual', 'Disabled'
    service_account TEXT,
    account_type TEXT,               -- 'Domain', 'MSA', 'gMSA', 'Virtual', 'Builtin'
    is_compliant INTEGER,            -- Based on Req 6
    issue_description TEXT,
    collected_at TEXT NOT NULL,
    UNIQUE(server_id, audit_run_id, service_name)
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_logins_instance ON logins(instance_id, audit_run_id);
CREATE INDEX IF NOT EXISTS idx_logins_name ON logins(login_name);
CREATE INDEX IF NOT EXISTS idx_database_users_instance ON database_users(instance_id, audit_run_id);
CREATE INDEX IF NOT EXISTS idx_annotations_key ON annotations(entity_type, entity_key);
CREATE INDEX IF NOT EXISTS idx_backup_history_db ON backup_history(instance_id, database_name);
"""


def initialize_schema_v2(connection) -> None:
    """
    Initialize schema version 2 tables.
    
    Call after initialize_schema() from HistoryStore.
    
    Args:
        connection: SQLite connection from HistoryStore._get_connection()
    """
    logger.info("Initializing schema v2 tables...")
    
    # Execute all DDL statements
    connection.executescript(SCHEMA_V2_TABLES)
    
    # Update schema version
    connection.execute("""
        INSERT OR REPLACE INTO schema_meta (key, value)
        VALUES ('version', '2')
    """)
    
    connection.commit()
    logger.info("Schema v2 initialized successfully")


def get_annotation(
    connection,
    entity_type: str,
    entity_key: str,
    field_name: str
) -> str | None:
    """
    Get an annotation value.
    
    Args:
        connection: SQLite connection
        entity_type: Type like 'login', 'linked_server'
        entity_key: Key like 'SERVER|INSTANCE|loginname'
        field_name: Field like 'description', 'reason'
        
    Returns:
        The annotation value or None
    """
    row = connection.execute("""
        SELECT field_value FROM annotations
        WHERE entity_type = ? AND entity_key = ? AND field_name = ?
    """, (entity_type, entity_key, field_name)).fetchone()
    
    return row["field_value"] if row else None


def set_annotation(
    connection,
    entity_type: str,
    entity_key: str,
    field_name: str,
    field_value: str | None,
    status_override: str | None = None,
    modified_by: str | None = None,
    audit_run_id: int | None = None
) -> int:
    """
    Set or update an annotation, with history tracking.
    
    Args:
        connection: SQLite connection
        entity_type: Type like 'login', 'linked_server'
        entity_key: Key like 'SERVER|INSTANCE|loginname'
        field_name: Field like 'description', 'reason'
        field_value: The value to set
        status_override: Optional status override ('exception', etc.)
        modified_by: Who made the change
        audit_run_id: Which audit run this happened in
        
    Returns:
        Annotation ID
    """
    now = datetime.now(timezone.utc).isoformat()
    
    # Check for existing annotation
    existing = connection.execute("""
        SELECT id, field_value, status_override 
        FROM annotations
        WHERE entity_type = ? AND entity_key = ? AND field_name = ?
    """, (entity_type, entity_key, field_name)).fetchone()
    
    if existing:
        # Update existing and log history
        connection.execute("""
            INSERT INTO annotation_history 
            (annotation_id, old_value, new_value, old_status, new_status, changed_at, changed_by, audit_run_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            existing["id"],
            existing["field_value"],
            field_value,
            existing["status_override"],
            status_override,
            now,
            modified_by,
            audit_run_id
        ))
        
        connection.execute("""
            UPDATE annotations
            SET field_value = ?, status_override = ?, modified_at = ?, modified_by = ?
            WHERE id = ?
        """, (field_value, status_override, now, modified_by, existing["id"]))
        
        connection.commit()
        return existing["id"]
    
    else:
        # Insert new
        cursor = connection.execute("""
            INSERT INTO annotations 
            (entity_type, entity_key, field_name, field_value, status_override, created_at, modified_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (entity_type, entity_key, field_name, field_value, status_override, now, modified_by))
        
        connection.commit()
        return cursor.lastrowid


def build_entity_key(*parts: str) -> str:
    """
    Build a composite entity key from parts.
    
    Example:
        build_entity_key("PROD-SQL01", "INSTANCE1", "sa")
        # Returns: "PROD-SQL01|INSTANCE1|sa"
    """
    return "|".join(str(p) for p in parts)
