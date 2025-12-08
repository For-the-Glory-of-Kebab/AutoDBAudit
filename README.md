# AutoDBAudit

**SQL Server Security Audit Tool** - Generates comprehensive 17-sheet Excel reports for security compliance auditing across multiple SQL Server instances (2008 R2 - 2025+).

---

## What Works Today ✅

| Command | What It Does |
|---------|--------------|
| `python main.py --audit` | Connects to configured SQL Servers, collects security data, generates Excel report |

**Output**: `output/sql_audit_YYYYMMDD_HHMMSS.xlsx` (17 sheets)

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
copy config\sql_targets.example.json config\sql_targets.json
notepad config\sql_targets.json
```
Edit `sql_targets.json` with your SQL Server connection details.

### 3. Run Audit
```powershell
$env:PYTHONPATH="d:\Raja-Initiative\src"
python main.py --audit
```

---

## Project Structure

```
src/autodbaudit/
├── application/              # Business logic
│   ├── audit_service.py      # Main orchestrator (run_audit)
│   └── data_collector.py     # Collects data from SQL Server
├── infrastructure/           # External integrations
│   ├── sql/                  # SQL Server connectivity
│   │   ├── connector.py      # SqlConnector class
│   │   └── query_provider.py # Version-specific SQL queries
│   ├── sqlite/               # (Exists but not wired up yet)
│   └── excel/                # Excel generation (21 files)
│       └── writer.py         # EnhancedReportWriter (17 sheets)
└── interface/
    └── cli.py                # Command-line interface
```

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
