# AutoDBAudit

**SQL Server Security Audit Tool** - Complete security compliance workflow with audit, remediation, and exception tracking.

---

## Workflow Overview

```bash
# 1. Initial audit → Excel + SQLite
python main.py --audit

# 2. Generate remediation scripts
python main.py --generate-remediation

# 3. Execute fixes (in SSMS or via app)

# 4. Sync progress (repeat as needed)
python main.py --sync

# 5. Add Notes/Reasons in Excel for exceptions

# 6. Finalize → Persist to SQLite
python main.py --finalize --excel output/sql_audit_edited.xlsx
```

See [docs/AUDIT_WORKFLOW.md](docs/AUDIT_WORKFLOW.md) for complete lifecycle.

---

## Current Status

| Command | Status |
|---------|--------|
| `--audit` | ✅ Complete |
| `--generate-remediation` | ✅ Complete |
| `--sync` | ⚠️ In Progress |
| `--finalize` | ⚠️ In Progress |
| `--apply-exceptions` | ⚠️ In Progress |

---

## Quick Start (5 minutes)

### 1. Setup Environment
```powershell
cd d:\Raja-Initiative
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure SQL Targets
```powershell
copy sql_targets.example.json sql_targets.json
notepad sql_targets.json
```

### 3. Run Audit
```powershell
$env:PYTHONPATH="d:\Raja-Initiative\src"
python main.py --audit
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| [AUDIT_WORKFLOW.md](docs/AUDIT_WORKFLOW.md) | Complete lifecycle |
| [SCHEMA_DESIGN.md](docs/SCHEMA_DESIGN.md) | SQLite tables |
| [CLI_REFERENCE.md](docs/CLI_REFERENCE.md) | Command reference |
| [PROJECT_STATUS.md](docs/PROJECT_STATUS.md) | Implementation state |
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

## What's NOT Working Yet

| Feature | Status |
|---------|--------|
| SQLite historical tracking | Code exists, not wired |
| `--finalize` command | Not implemented |
| Permission Grants sheet | Planned |
| Remediation scripts | Planned |

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
$env:PYTHONPATH="d:\Raja-Initiative\src"
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
