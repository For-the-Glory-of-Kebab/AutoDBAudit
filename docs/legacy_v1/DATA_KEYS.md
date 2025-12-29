# Data Keys & UUID Design

**Version**: 1.2
**Role**: Reference for row identification strategies (Composite Keys vs. UUIDs).

## 1. The "Row UUID" Strategy

### Problem
Entity keys (like names) change over time. Renaming a login shouldn't break its audit history or disconnect its attached notes.

### Solution
Every row in every sheet is assigned a **UUID v4** (or stable 8-char hex).
*   **Storage**: Excel Column A (Hidden, Width=0).
*   **Persistence**: Stored in `annotations.row_uuid`.
*   **Logic**:
    *   **New Row**: Generate UUID.
    *   **Sync**: Match by UUID first. Match by Entity Key second (fallback).
    *   **Resurrection**: If a row disappears and reappears, it gets a new UUID unless matched by Key within a time window.

---

## 2. Composite Key Formats

If UUID is missing (legacy data), we fallback to **Composite Keys**. All keys are **lowercased** for matching.

### General Pattern
`{entity_type}|{server}|{instance}|{...specific_keys}`

### Per-Sheet Definitions

| Sheet | Key Components | Example |
| :--- | :--- | :--- |
| **Instances** | Server, Instance | `instance\|srv\|def` |
| **SA Account** | Srv, Inst, Name | `sa_account\|srv\|def\|sa` |
| **Logins** | Srv, Inst, LoginName | `login\|srv\|def\|admin` |
| **Roles** | Srv, Inst, Role, Member | `role\|srv\|def\|sysadmin\|joe` |
| **Config** | Srv, Inst, Setting | `config\|srv\|def\|xp_cmdshell` |
| **Services** | Srv, Inst, ServiceName | `service\|srv\|def\|sqlagent` |
| **Databases** | Srv, Inst, DBName | `database\|srv\|def\|master` |
| **DB Users** | Srv, Inst, DB, User | `db_user\|srv\|def\|master\|dbo` |
| **Permissions** | Srv, Inst, Scope, DB, Grantee, Perm, Entity | `perm\|...` |
| **Linked Srv** | Srv, Inst, LinkedSrv | `linked_server\|srv\|def\|remotesrv` |

### Special Handling
*   **Icons**: Keys are stripped of status icons (e.g., `🔌 Connect` -> `connect`).
*   **Merged Cells**: Missing key parts inherit from the row above (visual grouping logic).

---

## 3. Database Schema Reference

The SQLite database (`audit_history.db`) relies on these keys for the `findings` and `annotations` tables.

### Annotations Table
```sql
CREATE TABLE annotations (
    id INTEGER PRIMARY KEY,
    row_uuid TEXT UNIQUE,        -- Priority Match
    entity_key TEXT,             -- Fallback Match
    entity_type TEXT,
    purpose TEXT,
    justification TEXT,
    review_status TEXT,
    last_reviewed TEXT
);
```
