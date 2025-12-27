# Excel System Overview

The AutoDBAudit application uses Excel not just as a static reporting tool, but as a **bidirectional data interface**. The Excel file is effectively a user-editable database view.

## Core Concepts

### 1. The "Excel as Database" Paradigm
*   **Source of Truth**: The SQLite database (`audit_history.db`) is the ultimate source of truth for *findings* (what the server looks like).
*   **User's Truth**: The Excel file is the source of truth for *annotations* (User Notes, Justifications, Review Status).
*   **Synchronization**: The `--sync` command reconciles these two worlds.

### 2. Row Stability & UUIDs
To ensure that your notes stay attached to the correct row even if the data changes slightly (e.g., a server is renamed or sorted differently):
*   **Hidden Column A**: Every sheet has a hidden first column (Column A) containing a stable **8-character UUID** (e.g., `A7F3B2C1`).
*   **Generation**: UUIDs are generated when a finding is first seen.
*   **Persistence**: The UUID never changes for that specific finding entity.
*   **Fallback**: If a UUID is lost (e.g., user deletes column A), the system falls back to a "Legacy Key" composed of the natural keys (Server + Instance + Entity Name).

### 3. Key Columns
Every sheet has defined **Key Columns** that uniquely identify a row.
*   *Example (Server Logins)*: `Server`, `Instance`, `Login Name`.
*   These columns correspond to the "Entity Key" in the database.

### 4. Interactive Columns
Users interact with specific columns to annotate findings:
*   **⏳/✅ Indicator (Column B)**: Visual status.
    *   ⏳ (Orange): Needs Review (Discrepancy found).
    *   ✅ (Blue): Exception Documented (Discrepancy accepted).
    *   ❌ (Red): Critical Failure.
    *   (Empty): Pass.
*   **Review Status**: A dropdown with strict values:
    *   `⏳ Needs Review`: Default for new issues.
    *   `✓ Exception`: User explicitly marks this as an exception.
*   **Justification**: The "Exception Reason". Filling this documentation makes the row compliant (changes ⏳ to ✅).
*   **Notes**: General engineering notes (does not affect compliance).

## Data Flow

1.  **Audit**: System scans SQL Servers -> Finds Issues -> Assigns UUIDs -> Writes to Excel.
2.  **Annotate**: User opens Excel -> Adds "Justification" for a specific login -> Saves.
3.  **Sync**: System reads Excel -> Finds row by UUID -> Saves "Justification" to SQLite -> Updates Stats -> Re-generates Excel with ✅ indicator.

## Sheet Architecture

All sheets follow a strict inheritance structure in code (`BaseSheetMixin`), ensuring consistent styling, behavior, and error handling.
See [Sheet Specifications](spec_definitions.md) for details on each sheet.

## Detailed Sheet Designs
*   **[Instances Sheet](sheets/instances.md)**: Inventory, Merging rules, and IP formatting.
*   **[SA Account](sheets/sa_account.md)**: Status and Boolean logic.
*   **[Server Logins](sheets/server_logins.md)**: Login Types and Password Policy.
*   **[Sensitive Roles](sheets/sensitive_roles.md)**: Role dropdowns (`sysadmin`) and Member Types.
*   **[Configuration](sheets/config.md)**: Risk Levels (Crit/High/Med/Low) and Settings.

*   **[Client Protocols](sheets/client_protocols.md)**: Enabled/Active boolean logic.
*   **[Databases](sheets/databases.md)**: Owner checks, Trustworthy bit, and Encryption status.
*   **[Database Users](sheets/database_users.md)**: Models Orphaned Users and Role Memberships.
*   **[Database Roles](sheets/database_roles.md)**: Role membership flattening.
*   **[Role Matrix](sheets/role_matrix.md)**: Pivot view of all access (Read-Only).
*   **[Permission Grants](sheets/permission_grants.md)**: Grant/Deny styling.
*   **[Orphaned Users](sheets/orphaned_users.md)**: SID formatting.
*   **[Linked Servers](sheets/linked_servers.md)**: Remote Login risk (`sa` vs mapping) and Purpose annotation.
*   **[Triggers](sheets/triggers.md)**: DDL vs DML triggers.
*   **[Backups](sheets/backups.md)**: RPO-based Critical/Warning status.
*   **[Audit Settings](sheets/audit_settings.md)**: Compliance targets.
*   **[Encryption](sheets/encryption.md)**: Key hierarchy (Read-Only).
*   **[Actions](sheets/actions.md)**: The append-only audit log.
