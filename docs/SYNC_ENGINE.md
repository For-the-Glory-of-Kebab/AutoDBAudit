# Sync Engine & State Machine

**Version**: 1.2
**Role**: Technical Reference for the Sync Engine, State Machine, and Persistence Layer.

## 1. Architecture Overview

The Sync Engine is a "Thin Orchestrator" that coordinates between:
1.  **Data Collector** (SQL Server)
2.  **Excel Reporter** (Human UI)
3.  **History Store** (SQLite Persistence)

### Data Flow
```
[SQL Server] --audit--> [SQLite Baseline]
                              |
[Excel UI] --sync--> [Diff Engine] <-- [SQLite]
                              |
                        [State Machine]
                              |
                       [Action Recorder]
                              |
                      [Appended Log]
```

---

## 2. State Machine Logic

The state machine is the **single source of truth** for all finding transitions.

### 2.1 State Definitions
*   **PASS**: Compliant.
*   **FAIL**: Non-compliant security issue.
*   **WARN**: Potential issue requiring review.
*   **EXCEPTION**: A FAIL/WARN finding with a valid technical justification.

### 2.2 Transition Matrix
| From | To | Event | Logged As |
| :--- | :--- | :--- | :--- |
| FAIL | PASS | Fix | **Fixed** |
| PASS | FAIL | Regression | **Regression** |
| (None) | FAIL | New Finding | **New Issue** |
| FAIL | FAIL+Note | Documentation | **Exception Documented** |
| FAIL+Note | FAIL | Removal | **Exception Removed** |

### 2.3 Priority Rules
When multiple events occur simultaneously (e.g., User adds note AND fixes issue):
1.  **Fixed** (Highest Priority)
2.  Regression
3.  Exception Documented

---

## 3. Entity Mutation Catalog

The system tracks specific mutations for 19 entity types.

| Entity | Critical Mutations (Logged) | Info Mutations |
| :--- | :--- | :--- |
| **SA Account** | Enable, Rename | Default DB Change |
| **Logins** | Add, Remove, Enable, Policy Off | - |
| **Roles** | Add Member (Sysadmin) | - |
| **Config** | Value Change | - |
| **Databases** | Trustworthy ON, Guest Enabled | Owner Change |
| **Linked Servers** | Add, Remove, Admin Access | - |
| **Backups** | Missing Backup | Age Warning |

---

## 4. Excel <-> DB Protocol

### 4.1 Key Uniqueness
Every sheet uses a deterministic composite key to match rows between runs.
*Example*: `Sensitive Roles` Key = `{Server}|{Instance}|{Role}|{Member}`

### 4.2 Handling Merged Cells
The reader handles Excel merged cells (visual grouping) by propagating the last seen non-empty value for key columns (Server/Instance).

### 4.3 Bidirectional Sync
*   **Read**: User Notes, Justifications, Review Status, Manual Dates.
*   **Write**: Status Icons (FAIL/PASS), Action Log updates, Indicator Flags (⏳).

---

## 5. Persistence Schema (`action_log`)

The Action Log is an **append-only** audit trail.

```sql
CREATE TABLE action_log (
    id INTEGER PRIMARY KEY,
    initial_run_id INTEGER,
    sync_run_id INTEGER,
    entity_key TEXT,
    action_type TEXT,      -- Fixed, Regression, etc.
    action_date TEXT,      -- Detected Timestamp
    user_date_override TEXT, -- User Manual Timestamp
    notes TEXT,
    UNIQUE(initial_run_id, entity_key, action_type, sync_run_id)
);
```

**Deduplication**: The unique constraint prevents double-logging the same event in the same sync cycle.

---

## 6. Stats Calculation (`StatsService`)

All statistics (CLI, Excel Cover, Verification) come from `StatsService`.
It calculates:
1.  **Active Issues**: FAIL findings without valid exception.
2.  **Fixed**: Count of "Fixed" actions since baseline.
3.  **Regressed**: Count of "Regression" actions.
4.  **Exceptions**: Count of active justifications.

---

## 7. Edge Cases

### 7.1 Instance Unavailable
If a server is offline during sync, its missing findings are **NOT** marked as fixed. The system requires successful connectivity to validate a fix.

### 7.2 Restoration
If `sql_audit.xlsx` is lost, it can be regenerated fully from `audit_history.db` using the `--regenerate-excel` command (future feature).
