# SQLite Schema Design

> **Purpose**: Reference for all SQLite tables and their relationships.

---

## Database File

`output/audit_history.db`

---

## Core Tables

### `audit_runs`

Tracks each audit execution.

```sql
CREATE TABLE audit_runs (
    id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT DEFAULT 'running',  -- running, completed, failed, finalized
    report_path TEXT,
    targets_file TEXT,
    run_type TEXT DEFAULT 'audit'   -- audit, sync, finalize
);
```

**Key fields**:
- `status`: Lifecycle state. Only one run should be `finalized` per audit cycle.
- `run_type`: Distinguishes initial audit from sync/finalize runs.

---

### `servers` and `instances`

Server and instance tracking.

```sql
CREATE TABLE servers (
    id INTEGER PRIMARY KEY,
    hostname TEXT NOT NULL UNIQUE,
    first_seen TEXT,
    last_seen TEXT
);

CREATE TABLE instances (
    id INTEGER PRIMARY KEY,
    server_id INTEGER REFERENCES servers(id),
    instance_name TEXT NOT NULL,
    edition TEXT,
    version TEXT,
    UNIQUE(server_id, instance_name)
);
```

---

### `findings`

Individual audit findings (PASS/FAIL/WARN).

```sql
CREATE TABLE findings (
    id INTEGER PRIMARY KEY,
    audit_run_id INTEGER REFERENCES audit_runs(id),
    instance_id INTEGER REFERENCES instances(id),
    
    finding_type TEXT NOT NULL,    -- sa_account, config, login, database, etc.
    entity_name TEXT NOT NULL,     -- The specific item (e.g., "sa", "xp_cmdshell")
    entity_key TEXT NOT NULL,      -- Composite: "server|instance|entity_name"
    
    status TEXT NOT NULL,          -- PASS, FAIL, WARN
    risk_level TEXT,               -- critical, high, medium, low
    description TEXT,
    recommendation TEXT,
    details TEXT,                  -- JSON for extra data
    
    collected_at TEXT NOT NULL,
    
    UNIQUE(audit_run_id, entity_key, finding_type)
);
```

**Entity Key Pattern**: `server|instance|entity_name`
- Example: `prod-sql01|MSSQLSERVER|xp_cmdshell`
- Used to track items across audit runs

---

### `action_log`

Records remediation actions with real timestamps.

```sql
CREATE TABLE action_log (
    id INTEGER PRIMARY KEY,
    initial_run_id INTEGER REFERENCES audit_runs(id),
    final_run_id INTEGER REFERENCES audit_runs(id),
    
    entity_key TEXT NOT NULL,
    finding_type TEXT NOT NULL,
    
    action_type TEXT NOT NULL,     -- fixed, excepted, regression, new
    action_date TEXT NOT NULL,     -- When fix was detected (real timestamp)
    action_description TEXT,       -- Auto-generated or user-provided
    
    captured_at TEXT NOT NULL,     -- When --sync detected the change
    
    UNIQUE(initial_run_id, entity_key, finding_type)
);
```

**Timestamp behavior**:
- `action_date`: Set when `--sync` first detects the fix. Preserved on subsequent syncs.
- `captured_at`: Always current time when the record is created.

---

### `annotations`

User-provided notes and justifications.

```sql
CREATE TABLE annotations (
    id INTEGER PRIMARY KEY,
    entity_type TEXT NOT NULL,     -- login, config, database, etc.
    entity_key TEXT NOT NULL,      -- server|instance|entity_name
    field_name TEXT NOT NULL,      -- notes, reason, status_override
    field_value TEXT,
    status_override TEXT,          -- Accept, Reject, Exception
    created_at TEXT NOT NULL,
    modified_at TEXT,
    modified_by TEXT,
    UNIQUE(entity_type, entity_key, field_name)
);
```

---

### `annotation_history`

Audit trail for annotation changes.

```sql
CREATE TABLE annotation_history (
    id INTEGER PRIMARY KEY,
    annotation_id INTEGER REFERENCES annotations(id),
    old_value TEXT,
    new_value TEXT,
    changed_at TEXT NOT NULL,
    changed_by TEXT,
    audit_run_id INTEGER
);
```

---

## Data Collection Tables

These store raw audit data for reference:

| Table | Content |
|-------|---------|
| `server_info` | OS, hardware, SQL installation |
| `config_settings` | sp_configure values |
| `logins` | Server logins |
| `databases` | Database properties |
| `db_users` | Database users per DB |
| `linked_servers` | Linked server configs |
| `backups` | Backup history |
| `triggers` | Server/DB triggers |
| `audit_settings` | SQL Server audit config |

---

## Relationships

```
audit_runs (1) ─────┬───── (N) findings
                    │
                    ├───── (N) action_log
                    │
                    └───── (N) annotation_history

servers (1) ───── (N) instances (1) ───── (N) findings

annotations ───── (N) annotation_history
```

---

## Helper Functions (schema.py)

| Function | Purpose |
|----------|---------|
| `save_finding()` | Insert finding during audit |
| `get_findings_for_run()` | Retrieve findings for a run |
| `compare_findings()` | Diff two runs |
| `upsert_annotation()` | Insert/update annotation |
| `get_annotations_for_entity()` | Get all notes for an entity |

---

*Document Version: 1.0 | Last Updated: 2025-12-09*
