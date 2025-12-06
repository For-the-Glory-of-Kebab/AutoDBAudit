# SQLite Schema – History Store

> **Purpose**: The SQLite database (`output/history.db`) is the **canonical store** for all audit, remediation, and hotfix history. Excel reports are generated *from* this database—they are views, not source-of-truth.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              history.db                                     │
├─────────────────┬───────────────────────┬───────────────────────────────────┤
│ Audit Tracking  │ Remediation Tracking  │ Hotfix Tracking                   │
├─────────────────┼───────────────────────┼───────────────────────────────────┤
│ audit_runs      │ actions               │ hotfix_runs                       │
│ servers         │ exceptions            │ hotfix_targets                    │
│ instances       │                       │ hotfix_steps                      │
│ requirements    │                       │                                   │
│ requirement_results                     │                                   │
└─────────────────┴───────────────────────┴───────────────────────────────────┘
```

---

## Table Definitions

### `audit_runs`

Tracks each audit execution.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `organization` | TEXT NOT NULL | Organization name (from config) |
| `audit_date` | TEXT NOT NULL | ISO date of audit (YYYY-MM-DD) |
| `started_at` | TEXT NOT NULL | ISO timestamp when audit started |
| `completed_at` | TEXT | ISO timestamp when audit completed (NULL if in progress) |
| `status` | TEXT NOT NULL | `running`, `completed`, `failed` |
| `config_hash` | TEXT | SHA256 of config used (for reproducibility) |
| `notes` | TEXT | Optional notes |

**Example row:**
```
id=1, organization="Acme Corp", audit_date="2025-12-06", started_at="2025-12-06T10:00:00",
completed_at="2025-12-06T10:15:00", status="completed", config_hash="abc123...", notes=NULL
```

---

### `servers`

Master list of SQL Server hosts observed across audits.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `hostname` | TEXT NOT NULL | Server hostname or IP |
| `first_seen_audit_id` | INTEGER | FK → `audit_runs.id` (when first discovered) |
| `last_seen_audit_id` | INTEGER | FK → `audit_runs.id` (most recent audit) |
| `is_active` | INTEGER NOT NULL DEFAULT 1 | 1 = active, 0 = decommissioned |

**Unique constraint:** `(hostname)`

---

### `instances`

SQL Server instances on each server.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `server_id` | INTEGER NOT NULL | FK → `servers.id` |
| `instance_name` | TEXT NOT NULL | Instance name (empty string for default) |
| `sql_version` | TEXT | e.g., "15.0.4298.1" |
| `sql_edition` | TEXT | e.g., "Standard", "Enterprise" |
| `sql_version_major` | INTEGER | 10 = 2008, 15 = 2019, 16 = 2022 |
| `first_seen_audit_id` | INTEGER | FK → `audit_runs.id` |
| `last_seen_audit_id` | INTEGER | FK → `audit_runs.id` |

**Unique constraint:** `(server_id, instance_name)`

---

### `requirements`

Reference table of audit requirements (from `db-requirements.md`).

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Requirement number (e.g., 4, 10, 15) |
| `code` | TEXT NOT NULL | Short code (e.g., "Req04", "Req10") |
| `title` | TEXT NOT NULL | Brief title |
| `description` | TEXT | Full description |
| `severity` | TEXT NOT NULL | `critical`, `warning`, `info` |
| `category` | TEXT | Category grouping |

**Note:** This table is seeded at first run and updated only when requirements change.

---

### `requirement_results`

Per-instance, per-audit results for each requirement.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `audit_run_id` | INTEGER NOT NULL | FK → `audit_runs.id` |
| `instance_id` | INTEGER NOT NULL | FK → `instances.id` |
| `requirement_id` | INTEGER NOT NULL | FK → `requirements.id` |
| `status` | TEXT NOT NULL | `pass`, `fail`, `exception`, `not_applicable` |
| `finding` | TEXT | Details of what was found |
| `evidence` | TEXT | Raw query output or data (JSON) |
| `checked_at` | TEXT NOT NULL | ISO timestamp |

**Unique constraint:** `(audit_run_id, instance_id, requirement_id)`

**Example row:**
```
id=42, audit_run_id=1, instance_id=3, requirement_id=4, status="fail",
finding="SA account enabled and not renamed", evidence='{"sa_enabled":true,...}',
checked_at="2025-12-06T10:05:00"
```

---

### `actions`

Remediation actions taken (scripts executed).

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `audit_run_id` | INTEGER NOT NULL | FK → `audit_runs.id` |
| `instance_id` | INTEGER NOT NULL | FK → `instances.id` |
| `requirement_id` | INTEGER NOT NULL | FK → `requirements.id` |
| `script_file` | TEXT | Path to the remediation script |
| `action_type` | TEXT NOT NULL | `applied`, `skipped`, `failed` |
| `executed_at` | TEXT | ISO timestamp |
| `result_message` | TEXT | Output or error message |
| `executed_by` | TEXT | Username who ran it |

---

### `exceptions`

Documented exceptions (issues intentionally not fixed).

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `audit_run_id` | INTEGER NOT NULL | FK → `audit_runs.id` |
| `instance_id` | INTEGER NOT NULL | FK → `instances.id` |
| `requirement_id` | INTEGER NOT NULL | FK → `requirements.id` |
| `reason` | TEXT NOT NULL | Justification for exception |
| `approved_by` | TEXT | Who approved the exception |
| `approved_at` | TEXT | ISO timestamp |
| `expires_at` | TEXT | Optional expiry date |

---

### `hotfix_runs`

Tracks each hotfix deployment session.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `started_at` | TEXT NOT NULL | ISO timestamp |
| `completed_at` | TEXT | ISO timestamp (NULL if in progress) |
| `status` | TEXT NOT NULL | `running`, `completed`, `partial`, `failed` |
| `initiated_by` | TEXT | Username |
| `notes` | TEXT | Optional notes |

---

### `hotfix_targets`

Per-server status within a hotfix run.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `hotfix_run_id` | INTEGER NOT NULL | FK → `hotfix_runs.id` |
| `server_id` | INTEGER NOT NULL | FK → `servers.id` |
| `pre_build` | TEXT | Build version before patching |
| `post_build` | TEXT | Build version after patching |
| `status` | TEXT NOT NULL | `pending`, `in_progress`, `success`, `partial`, `failed`, `skipped` |
| `requires_restart` | INTEGER | 1 = yes, 0 = no |
| `error_message` | TEXT | Error details if failed |

---

### `hotfix_steps`

Individual installer executions on a target.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `hotfix_target_id` | INTEGER NOT NULL | FK → `hotfix_targets.id` |
| `step_order` | INTEGER NOT NULL | Sequence number (1, 2, 3...) |
| `installer_file` | TEXT NOT NULL | Filename of the hotfix installer |
| `description` | TEXT | e.g., "CU22 for SQL Server 2019" |
| `status` | TEXT NOT NULL | `pending`, `running`, `success`, `failed` |
| `started_at` | TEXT | ISO timestamp |
| `completed_at` | TEXT | ISO timestamp |
| `exit_code` | INTEGER | Installer exit code |
| `output` | TEXT | Stdout/stderr (truncated) |

---

## Relationships Diagram

```
audit_runs ───────┬────────────────────────────────┐
    │             │                                │
    │             ▼                                ▼
    │        servers ◄──────────────────────┬─ hotfix_targets
    │             │                         │       │
    │             ▼                         │       ▼
    │        instances                      │  hotfix_steps
    │             │                         │
    ▼             ▼                         │
requirement_results ◄───── requirements     │
    │                                       │
    ▼                                       │
 actions                                    │
 exceptions                                 │
                                            │
hotfix_runs ────────────────────────────────┘
```

---

## Data Flows

### During an Audit Run

1. **Insert** `audit_runs` row with status=`running`
2. **Upsert** `servers` for each target (update `last_seen_audit_id`)
3. **Upsert** `instances` with detected version info
4. For each requirement check:
   - **Insert** `requirement_results` with status=`pass`/`fail`
5. **Update** `audit_runs.status` = `completed`, set `completed_at`

### During Remediation

1. Load open `requirement_results` with status=`fail` from latest audit
2. Generate scripts; user reviews and uncomments
3. For each executed script:
   - **Insert** `actions` with `action_type`=`applied` or `failed`
4. For skipped scripts:
   - **Insert** `actions` with `action_type`=`skipped`
   - Optionally **Insert** `exceptions` with justification
5. Re-run affected checks, **Update** `requirement_results.status` if now passing

### During Hotfix Deployment

1. **Insert** `hotfix_runs` with status=`running`
2. For each target server:
   - **Insert** `hotfix_targets` with status=`pending`
   - For each installer:
     - **Insert** `hotfix_steps` with status=`pending`
     - Run installer, **Update** step status/output
   - **Update** `hotfix_targets.status` based on step outcomes
3. **Update** `hotfix_runs.status` = `completed` / `partial` / `failed`

### Report Generation

- Query `audit_runs` + `requirement_results` + joins
- Aggregate compliance stats per requirement
- Compare across audits for trend data
- Render to Excel sheets via `openpyxl`

---

## Indexes (Recommended)

```sql
CREATE INDEX idx_rr_audit_run ON requirement_results(audit_run_id);
CREATE INDEX idx_rr_instance ON requirement_results(instance_id);
CREATE INDEX idx_rr_requirement ON requirement_results(requirement_id);
CREATE INDEX idx_actions_audit ON actions(audit_run_id);
CREATE INDEX idx_hotfix_targets_run ON hotfix_targets(hotfix_run_id);
CREATE INDEX idx_hotfix_steps_target ON hotfix_steps(hotfix_target_id);
```

---

## Guidelines for Future Schema Changes

1. **Don't silently change schema**  
   If you need to alter a table, add a version table or bump a schema version constant. Implement migration logic.

2. **Prefer additive changes**  
   Add new columns with `DEFAULT` values or new tables. Avoid renaming/dropping columns.

3. **Keep backward compatible when possible**  
   Old DBs should open with new code (with graceful defaults for missing columns).

4. **Document migrations**  
   If a migration is needed, document it clearly in this file and in code comments.

5. **Use explicit SQL**  
   No ORM magic. All schema DDL should be readable in one place (e.g., `infrastructure/history_store.py`).

---

## Schema Version

Store schema version in a metadata table:

```sql
CREATE TABLE schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
INSERT INTO schema_meta VALUES ('version', '1');
```

Check on startup; run migrations if version mismatch.

---

*Last updated: 2025-12-06*
