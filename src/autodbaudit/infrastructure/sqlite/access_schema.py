"""
Access status schema for remote access preparation.

Tracks:
- OS type (Windows/Linux)
- Access method (WinRM/SSH/SQL-only)
- Original state snapshots for revert
- Changes made during preparation
"""

from __future__ import annotations

# Schema for access_status table
ACCESS_SCHEMA = """
-- ============================================================================
-- Access Preparation Status
-- Tracks remote access capability for each target
-- ============================================================================

CREATE TABLE IF NOT EXISTS access_status (
    id INTEGER PRIMARY KEY,
    target_id TEXT NOT NULL UNIQUE,
    hostname TEXT NOT NULL,
    
    -- OS and access type
    os_type TEXT NOT NULL DEFAULT 'unknown',  -- 'windows', 'linux', 'unknown'
    access_method TEXT NOT NULL DEFAULT 'none',  -- 'winrm', 'ssh', 'sql_only', 'none'
    access_status TEXT NOT NULL DEFAULT 'unknown',  -- 'ready', 'partial', 'failed', 'manual'
    access_error TEXT,
    
    -- Original state for revert
    original_snapshot TEXT,  -- JSON: settings before changes
    changes_made TEXT,  -- JSON array: each change logged
    
    -- Timestamps
    prepared_at TEXT,
    last_verified_at TEXT,
    
    -- Manual override
    manual_override INTEGER DEFAULT 0,
    override_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_access_status_target ON access_status(target_id);
CREATE INDEX IF NOT EXISTS idx_access_status_status ON access_status(access_status);
"""

# Schema for remediation tracking
REMEDIATION_SCHEMA = """
-- ============================================================================
-- Remediation Runs
-- Tracks each remediation execution
-- ============================================================================

CREATE TABLE IF NOT EXISTS remediation_runs (
    id INTEGER PRIMARY KEY,
    audit_run_id INTEGER REFERENCES audit_runs(id),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'applied', 'failed', 'rolled_back'
    findings_count INTEGER DEFAULT 0,
    applied_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    scripts_path TEXT,
    rollback_path TEXT
);

-- ============================================================================
-- Remediation Items
-- Individual finding remediation status
-- ============================================================================

CREATE TABLE IF NOT EXISTS remediation_items (
    id INTEGER PRIMARY KEY,
    remediation_run_id INTEGER REFERENCES remediation_runs(id),
    finding_key TEXT NOT NULL,
    finding_type TEXT NOT NULL,  -- 'sa_account', 'login', 'config', etc.
    
    -- Scripts
    script_content TEXT,
    rollback_content TEXT,
    
    -- Status
    status TEXT NOT NULL DEFAULT 'generated',  -- 'generated', 'applied', 'failed', 'skipped'
    error_message TEXT,
    applied_at TEXT,
    
    UNIQUE(remediation_run_id, finding_key)
);

CREATE INDEX IF NOT EXISTS idx_remediation_items_run ON remediation_items(remediation_run_id);
CREATE INDEX IF NOT EXISTS idx_remediation_items_status ON remediation_items(status);
"""


def get_full_schema() -> str:
    """Get combined schema for access and remediation tables."""
    return ACCESS_SCHEMA + REMEDIATION_SCHEMA
