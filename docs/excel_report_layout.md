# Excel Report Layout

> **Status**: ✅ Excel report generation is **fully implemented** as of 2025-12-08.

---

## Overview

Excel reports are generated directly via `openpyxl` using a modular mixin-based architecture. Each sheet is a separate module in `src/autodbaudit/infrastructure/excel/`.

---

## Sheets Summary

| # | Sheet Name | Module | Purpose |
|---|------------|--------|---------|
| 1 | Cover | `cover.py` | Title page with summary stats |
| 2 | Actions | `actions.py` | Remediation action log |
| 3 | Instances | `instances.py` | SQL Server instance inventory |
| 4 | SA Account | `sa_account.py` | SA account security status |
| 5 | Server Logins | `logins.py` | Server login audit |
| 6 | Sensitive Roles | `roles.py` | sysadmin/securityadmin memberships |
| 7 | Configuration | `config.py` | sp_configure security settings |
| 8 | Services | `services.py` | SQL Server services |
| 9 | Databases | `databases.py` | Database inventory |
| 10 | Database Users | `db_users.py` | Database user audit |
| 11 | Database Roles | `db_roles.py` | Database role memberships |
| 12 | Orphaned Users | `orphaned_users.py` | Orphaned database users |
| 13 | Linked Servers | `linked_servers.py` | Linked server configuration |
| 14 | Triggers | `triggers.py` | Server/database triggers |
| 15 | Backups | `backups.py` | Backup status audit |
| 16 | Audit Settings | `audit_settings.py` | Login audit configuration |
| 17 | Encryption | `encryption.py` | SMK/DMK/TDE encryption status |
| 18 | Actions | `actions.py` | Remediation action log |

---

## Sheet Details

### 1. Cover
**Purpose**: Title page with summary statistics

Contains:
- Organization name
- Audit date
- Total pass/fail/warn counts
- Summary by category

---

### 2. Actions
**Columns**: ID, Server, Instance, Category, Finding, Risk Level, Recommendation, Status, Found Date, Assigned To, Due Date, Resolution Date, Resolution Notes

| Column | Type | Dropdown Options |
|--------|------|-----------------|
| Category | Enum | `SA Account`, `Configuration`, `Backup`, `Login`, `Permissions`, `Service`, `Database`, `Other` |
| Risk Level | Risk | `Critical`, `High`, `Medium`, `Low` |
| Status | Status | `⏳ Open`, `✓ Closed`, `⚠️ Exception` |

**Notes**: Manual columns (gray background): Assigned To, Due Date, Resolution Date, Resolution Notes

---

### 3. Instances
**Columns**: Config Name, Server, Instance, Machine Name, IP Address, Version, Build, SQL Year, Edition, Clustered, HADR, OS, CPU, RAM, Notes, Last Revised

| Column | Type | Dropdown Options |
|--------|------|-----------------|
| Clustered | Boolean | `✓`, `✗` |
| HADR | Boolean | `✓`, `✗` |

---

### 4. SA Account
**Columns**: Server, Instance, Status, Is Disabled, Is Renamed, Current Name, Default DB, Remediation Notes

| Column | Type | Dropdown Options |
|--------|------|-----------------|
| Status | Status | `PASS`, `FAIL`, `WARN` |
| Is Disabled | Boolean | `✓`, `✗` |
| Is Renamed | Boolean | `✓`, `✗` |

---

### 5. Server Logins
**Columns**: Server, Instance, Login Name, Login Type, Enabled, Password Policy, Default Database, Notes, Last Revised

| Column | Type | Dropdown Options |
|--------|------|-----------------|
| Enabled | Boolean | `✓ Yes`, `✗ No` |
| Password Policy | Boolean | `✓ Yes`, `✗ No`, `N/A` |

---

### 6. Sensitive Roles
**Columns**: Server, Instance, Role, Member, Member Type, Enabled, Justification, Last Revised

| Column | Type | Dropdown Options |
|--------|------|-----------------|
| Enabled | Boolean | `✓ Yes`, `✗ No` |

---

### 7. Configuration
**Columns**: Server, Instance, Setting, Current, Required, Status, Risk, Exception Reason

| Column | Type | Dropdown Options |
|--------|------|-----------------|
| Status | Status | `✅ PASS`, `❌ FAIL` |
| Risk | Risk | `Critical`, `High`, `Medium`, `Low` |

---

### 8. Services
**Columns**: Server, Instance, Service Name, Type, Status, Startup, Service Account, Compliant, Notes

| Column | Type | Dropdown Options |
|--------|------|-----------------|
| Status | Status | `✓ Running`, `✗ Stopped`, `Unknown` |
| Startup | Enum | `⚡ Auto`, `🔧 Manual`, `⛔ Disabled` |
| Compliant | Boolean | `✓`, `✗` |

---

### 9. Databases
**Columns**: Server, Instance, Database, Owner, Recovery, State, Data (MB), Log (MB), Trustworthy, Notes

| Column | Type | Dropdown Options |
|--------|------|-----------------|
| Recovery | Enum | `🛡️ Full`, `📦 Bulk-Logged`, `⚡ Simple` |
| State | Enum | `✓ Online`, `⛔ Offline`, `🔄 Restoring`, `⏳ Recovering`, `⚠️ Suspect`, `🚨 Emergency` |
| Trustworthy | Boolean | `✓ ON`, `✗ OFF`, `✓`, `✗` |

---

### 10. Database Users
**Columns**: Server, Instance, Database, User Name, Type, Mapped Login, Login Status, Compliant, Notes

| Column | Type | Dropdown Options |
|--------|------|-----------------|
| Login Status | Status | `✓ Mapped`, `🔧 System`, `⚠️ Orphaned` |
| Compliant | Status | `✓`, `⚠️ Review`, `❌ GUEST` |

---

### 11. Database Roles
**Columns**: Server, Instance, Database, Role, Member, Member Type, Risk, Justification

| Column | Type | Dropdown Options |
|--------|------|-----------------|
| Role | Enum | `👑 db_owner`, `⚙️ db_securityadmin`, `⚙️ db_accessadmin`, `⚙️ db_backupoperator`, `⚙️ db_ddladmin`, `📖 db_datareader`, `✏️ db_datawriter`, `db_denydatareader`, `db_denydatawriter`, `public`, `(Custom)` |
| Member Type | Enum | `🪟 Windows`, `🔑 SQL`, `📦 Role` |
| Risk | Risk | `🔴 High`, `🟡 Medium`, `🟢 Low`, `—` |

---

### 12. Orphaned Users
**Columns**: Server, Instance, Database, User Name, Type, Status, Remediation

| Column | Type | Dropdown Options |
|--------|------|-----------------|
| Type | Enum | `🪟 Windows`, `🔑 SQL` |
| Status | Status | `⚠️ Orphaned`, `✓ Fixed`, `❌ Removed` |

---

### 13. Linked Servers
**Columns**: Server, Instance, Linked Server, Provider, Data Source, RPC Out, Local Login, Remote Login, Impersonate, Risk, Purpose, Last Revised

| Column | Type | Dropdown Options |
|--------|------|-----------------|
| RPC Out | Boolean | `✓ Yes`, `✗ No` |
| Impersonate | Boolean | `✓ Yes`, `✗ No` |
| Risk | Risk | `🟢 Normal`, `🔴 HIGH` |

---

### 14. Triggers
**Columns**: Server, Instance, Level, Database, Trigger Name, Event, Enabled, Purpose

| Column | Type | Dropdown Options |
|--------|------|-----------------|
| Enabled | Boolean | `✓`, `✗` |

---

### 15. Backups
**Columns**: Server, Instance, Database, Recovery Model, Last Full Backup, Days Since, Backup Path, Size (MB), Status, Notes

| Column | Type | Dropdown Options |
|--------|------|-----------------|
| Status | Status | `PASS`, `WARN`, `FAIL` |

---

### 16. Audit Settings
**Columns**: Server, Instance, Setting, Current Value, Recommended, Status, Notes

| Column | Type | Dropdown Options |
|--------|------|-----------------|
| Status | Status | `PASS`, `FAIL` |

---

## Visual Features

### Server/Instance Grouping
- Server column merged for multiple instances
- Color rotation for visual distinction between servers
- Alternating shades within same server for instances

### Conditional Formatting
| Element | Rule | Visual |
|---------|------|--------|
| PASS | Boolean true or status pass | Green fill (#C8E6C9), green text |
| FAIL | Boolean false or status fail | Red fill (#FFCDD2), red text |
| WARN | Warning state | Yellow fill (#FFF9C4), dark text |
| INFO | System/expected state | Purple/blue fill |

### Dropdowns (Data Validation)
- All boolean and enum columns have dropdown lists
- Enables consistent manual editing
- Options include emojis for visual clarity

---

## Architecture

```
src/autodbaudit/infrastructure/excel/
├── __init__.py        # Module exports
├── base.py            # BaseSheetMixin, helper functions
├── server_group.py    # ServerGroupMixin for color/merging
├── writer.py          # ExcelReportWriter (combines all mixins)
├── instances.py       # Instances sheet
├── sa_account.py      # SA Account sheet
├── logins.py          # Server Logins sheet
├── roles.py           # Sensitive Roles sheet
├── config.py          # Configuration sheet
├── services.py        # Services sheet
├── databases.py       # Databases sheet
├── db_users.py        # Database Users sheet
├── db_roles.py        # Database Roles sheet
├── orphaned_users.py  # Orphaned Users sheet
├── linked_servers.py  # Linked Servers sheet
├── triggers.py        # Triggers sheet
├── backups.py         # Backups sheet
├── audit_settings.py  # Audit Settings sheet
├── cover.py           # Cover sheet
└── actions.py         # Actions sheet
```

---

*Last updated: 2025-12-08*
