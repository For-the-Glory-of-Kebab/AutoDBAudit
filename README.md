# AutoDBAudit

**SQL Server Security Audit Tool** - Complete security compliance workflow with audit, remediation, and exception tracking.

## 🎯 Project Goal

> **A person with ZERO SQL experience should be able to fully conduct the audit, fix discrepancies, and deliver the final result ready for scoring.**

The tool generates **smart remediation scripts** that:
- ✅ **Auto-execute** safe fixes (orphaned users, dangerous settings)
- ⚠️ **Log passwords** when disabling SA account
- 📋 **Comment out** dangerous operations for human review
- 📖 **Provide instructions** for manual tasks (backups, upgrades)

---

## Workflow Overview

```bash
# 1. Initial audit → Excel + SQLite
python main.py --audit

# 2. Generate smart remediation scripts
python main.py --generate-remediation

# 3. Preview changes (dry run)
python main.py --apply-remediation --dry-run

# 4. Execute remediation
python main.py --apply-remediation

# 5. Check status dashboard
python main.py --status

# 6. If rollback needed
python main.py --apply-remediation --rollback

# 7. Add Notes in Excel for exceptions

# 8. Finalize → Persist to SQLite
python main.py --finalize --excel output/sql_audit_edited.xlsx
```

See [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) for full command reference.

---

## Current Status

| Command | Status | Notes |
|---------|--------|-------|
| `--audit` | ✅ Working | Excel + SQLite output |
| `--generate-remediation` | ✅ Working | 4-category scripts + rollback |
| `--apply-remediation` | ✅ Working | With --dry-run, --rollback |
| `--status` | ✅ Working | Dashboard summary |
| `--sync` | ✅ Working | Progress tracking |
| `--finalize` | ⚠️ Partial | Basic implementation |
| `--deploy-hotfixes` | ⏳ Pending | Stubs only |

See [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) for comprehensive details.

---


## Quick Start (5 minutes)

### 1. Setup Environment
```powershell
# Clone/navigate to project directory
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure SQL Targets
Edit `sql_targets.json` with your SQL Server connection details:
```json
{
  "targets": [
    {
      "id": "my-server",
      "server": "localhost",
      "port": 1433,
      "auth": "sql",
      "username": "audit_user",
      "password": "secret"
    }
  ]
}
```

### 3. Run Audit
```powershell
$env:PYTHONPATH="$PWD\src"
python main.py --audit
```

---

## Documentation

All documentation is in the [`docs/`](docs/) folder:

| Document | Purpose |
|----------|---------|
| [INDEX.md](docs/INDEX.md) | Documentation index |
| [PROJECT_STATUS.md](docs/PROJECT_STATUS.md) | Current implementation state |
| [AUDIT_WORKFLOW.md](docs/AUDIT_WORKFLOW.md) | Complete lifecycle |
| [CLI_REFERENCE.md](docs/CLI_REFERENCE.md) | Command reference |
| [SCHEMA_REFERENCE.md](docs/SCHEMA_REFERENCE.md) | SQLite tables |
| [TODO.md](docs/TODO.md) | Work items |


---

## Excel Report Sheets (17)

| # | Sheet | Purpose |
|---|-------|---------|
| 1 | Cover | Summary with pass/fail/warn counts |
| 2 | Instances | SQL Server inventory |
| 3 | SA Account | SA account security status |
| 4 | Server Logins | Login audit |
| 5 | Sensitive Roles | sysadmin/securityadmin members |
| 6 | Configuration | sp_configure settings |
| 7 | Services | SQL Server services |
| 8 | Databases | Database properties |
| 9 | Database Users | Per-database users |
| 10 | Database Roles | Role memberships |
| 11 | Orphaned Users | Users without logins |
| 12 | Linked Servers | Linked server config |
| 13 | Triggers | Server/database triggers |
| 14 | Backups | Backup status |
| 15 | Audit Settings | Audit configuration |
| 16 | Encryption | SMK/DMK/TDE status |
| 17 | Actions | Remediation tracking |

See [docs/excel_report_layout.md](docs/excel_report_layout.md) for column details.

---

## Pending Features

| Feature | Status |
|---------|--------|
| `--deploy-hotfixes` | Design complete, not implemented |
| Permission Grants sheet | Planned |

---

## Architecture

### Key Design Patterns
- **Strategy Pattern** - `QueryProvider` for SQL 2008 vs 2012+ queries
- **Mixin Pattern** - Each Excel sheet is a separate mixin class
- **Dataclasses** - Typed configuration objects

### Entry Points
1. `main.py` → `cli.py` → `audit_service.py` → `data_collector.py` → `writer.py`

---

## Dependencies

| Package | Purpose |
|---------|---------|
| pyodbc | SQL Server connectivity |
| openpyxl | Excel generation |
| pywin32 | Windows credential encryption |

**No pandas/numpy** - Intentionally minimal.

---

## Testing

```powershell
# Verify setup
python test_setup.py

# Generate full report (test mode)
$env:PYTHONPATH="$PWD\src"
python test_multi_instance.py
```

---

## Documentation

| File | Purpose |
|------|---------|
| [db-requirements.md](db-requirements.md) | 28 security requirements being audited |
| [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) | What's done, what's next |
| [docs/TODO.md](docs/TODO.md) | Task tracker |
| [docs/excel_report_layout.md](docs/excel_report_layout.md) | Sheet column documentation |

---

*Last updated: 2025-12-08*
