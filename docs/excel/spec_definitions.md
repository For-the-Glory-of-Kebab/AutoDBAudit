# Excel Sheet Specifications

This document defines the schema, key columns, and behavior for every sheet in the Audit Report.
**Source of Truth**: `src/autodbaudit/domain/sheet_registry.py`

## Glossary
*   **Entity Type**: The internal DB identifier for this type of record.
*   **Key Columns**: The combination of columns that makes a row unique (Primary Key).
*   **Editable Columns**: Columns the user is expected to modify. Changes here are synced back to the DB.
*   **UUID Support**: Whether the sheet has a hidden Column A for row tracking.

---

## 🔒 Security Sheets

### SA Account
Tracks the status of the `sa` account on each instance.
*   **Entity Type**: `sa_account`
*   **UUID**: Yes
*   **Key Columns**:
    *   `Server`
    *   `Instance`
*   **Editable Columns**:
    *   `Review Status`: Dropdown (Needs Review / Exception)
    *   `Justification`: **Primary Annotation**. Reason why SA is active/renamed.
    *   `Last Reviewed`: Date
    *   `Notes`: General notes

### Configuration
Tracks `sp_configure` settings (e.g., xp_cmdshell, remote access).
*   **Entity Type**: `config`
*   **UUID**: Yes
*   **Key Columns**:
    *   `Server`
    *   `Instance`
    *   `Setting` (e.g., "xp_cmdshell")
*   **Editable Columns**:
    *   `Review Status`
    *   `Exception Reason` (Maps to `justification`): **Primary Annotation**.
    *   `Last Reviewed`

### Server Logins
Audits SQL Logins, Windows Users, and Groups on the server.
*   **Entity Type**: `login`
*   **UUID**: Yes
*   **Key Columns**:
    *   `Server`
    *   `Instance`
    *   `Login Name`
*   **Editable Columns**:
    *   `Review Status`
    *   `Justification`: **Primary Annotation**.
    *   `Last Reviewed`
    *   `Notes`

### Sensitive Roles
Tracks members of high-privilege Server Roles (sysadmin, securityadmin, etc.).
*   **Entity Type**: `server_role`
*   **UUID**: Yes
*   **Key Columns**:
    *   `Server`
    *   `Instance`
    *   `Role` (e.g., "sysadmin")
    *   `Member` (The principal name)
*   **Editable Columns**:
    *   `Review Status`
    *   `Justification`: **Primary Annotation**.
    *   `Last Reviewed`

### Services
Tracks the service account and status of SQL Engine and Agent services.
*   **Entity Type**: `service`
*   **UUID**: Yes
*   **Key Columns**:
    *   `Server`
    *   `Instance`
    *   `Service Name`
*   **Editable Columns**:
    *   `Review Status`
    *   `Justification`: **Primary Annotation**.
    *   `Last Reviewed`

### Client Protocols
Audits enabled network protocols (Shared Memory, Named Pipes, TCP/IP).
*   **Entity Type**: `protocol`
*   **UUID**: Yes
*   **Key Columns**:
    *   `Server`
    *   `Instance`
    *   `Protocol`
*   **Editable Columns**:
    *   `Review Status`
    *   `Justification`: **Primary Annotation**.
    *   `Last Reviewed`

### Linked Servers
Audits linked server configurations and their security context.
*   **Entity Type**: `linked_server`
*   **UUID**: Yes
*   **Key Columns**:
    *   `Server`
    *   `Instance`
    *   `Linked Server` (Name)
*   **Editable Columns**:
    *   `Review Status`
    *   `Purpose` (Maps to `purpose` in DB): **Primary Annotation**.
    *   `Justification`: For security exceptions.
    *   `Last Reviewed`

### Audit Settings
Tracks SQL Server Audit specifications and states.
*   **Entity Type**: `audit_settings`
*   **UUID**: Yes
*   **Key Columns**:
    *   `Server`
    *   `Instance`
    *   `Setting`
*   **Editable Columns**:
    *   `Review Status`
    *   `Exception Reason` (Maps to `justification`)
    *   `Last Reviewed`
    *   `Notes`

---

## 🗄️ Database Object Sheets

### Databases
General audit of databases (Owner, Trustworthy bit, etc.).
*   **Entity Type**: `database`
*   **UUID**: Yes
*   **Key Columns**:
    *   `Server`
    *   `Instance`
    *   `Database`
*   **Editable Columns**:
    *   `Review Status`
    *   `Justification`
    *   `Last Reviewed`
    *   `Notes`

### Database Users
Users mapped within specific databases.
*   **Entity Type**: `db_user`
*   **UUID**: Yes
*   **Key Columns**:
    *   `Server`
    *   `Instance`
    *   `Database`
    *   `User Name`
*   **Editable Columns**:
    *   `Review Status`
    *   `Justification`
    *   `Last Reviewed`
    *   `Notes`

### Database Roles
Members of fixed database roles (db_owner, etc.).
*   **Entity Type**: `db_role`
*   **UUID**: Yes
*   **Key Columns**:
    *   `Server`
    *   `Instance`
    *   `Database`
    *   `Role`
    *   `Member`
*   **Editable Columns**:
    *   `Review Status`
    *   `Justification`
    *   `Last Reviewed`

### Permission Grants
Explicit permissions granted/denied (GRANT/DENY).
*   **Entity Type**: `permission`
*   **UUID**: Yes
*   **Key Columns**:
    *   `Server`
    *   `Instance`
    *   `Scope`
    *   `Grantee`
    *   `Permission`
*   **Editable Columns**:
    *   `Review Status`
    *   `Justification`
    *   `Last Reviewed`
    *   `Notes`

### Orphaned Users
Users in databases that have no matching Login on the server.
*   **Entity Type**: `orphaned_user`
*   **UUID**: Yes
*   **Key Columns**:
    *   `Server`
    *   `Instance`
    *   `Database`
    *   `User Name`
*   **Editable Columns**:
    *   `Review Status`
    *   `Justification`
    *   `Last Reviewed`

### Triggers
Server and Database level DDL triggers.
*   **Entity Type**: `trigger`
*   **UUID**: Yes
*   **Key Columns**:
    *   `Server`
    *   `Instance`
    *   `Scope`
    *   `Trigger Name`
*   **Editable Columns**:
    *   `Review Status`
    *   `Notes`: **Primary Annotation**.
    *   `Justification`
    *   `Last Reviewed`

### Backups
Backup history and gaps.
*   **Entity Type**: `backup`
*   **UUID**: Yes
*   **Key Columns**:
    *   `Server`
    *   `Instance`
    *   `Database`
*   **Editable Columns**:
    *   `Review Status`
    *   `Justification`
    *   `Last Reviewed`
    *   `Notes`

---

## ℹ️ Special / Info Sheets

### Action Log (Actions)
A history of all detected changes and items requiring attention.
*   **Entity Type**: `action`
*   **UUID**: No (Uses `ID` column).
*   **Key Columns**: `ID`
*   **Editable Columns**:
    *   `Notes`
    *   `Detected Date` (User can override date)
    *   User can also add **MANUAL ROWS** here which are synced to DB as manual actions.

### Instances
Inventory of scanned instances.
*   **Entity Type**: `instance`
*   **UUID**: No
*   **Key Columns**: `Config Name`, `Server`, `Instance`
*   **Editable Columns**: `Notes`, `Last Revised`

### Role Matrix
Pivot view of permissions.
*   **Entity Type**: `role_matrix`
*   **UUID**: No
*   **Editable**: No (Read-only view).

### Encryption
Keys and Certificates.
*   **Entity Type**: `encryption`
*   **UUID**: Yes
*   **Key Columns**: `Server`, `Instance`, `Key Type`, `Key Name`
*   **Editable Columns**: `Notes`
