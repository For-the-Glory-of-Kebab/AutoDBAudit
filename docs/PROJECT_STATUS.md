# Project Status

> **Purpose**: Current state of implementation for new developers.

---

## Quick Status

| Component | Status | Notes |
|-----------|--------|-------|
| Audit (`--audit`) | ✅ Complete | Collects 9 finding types |
| Remediation Scripts | ✅ Complete | TSQL templates for 5 types |
| Sync (`--sync`) | ⚠️ Partial | Needs `action_log` table |
| Finalize (`--finalize`) | ⚠️ Partial | Needs refactor for final design |
| Excel Columns | ⚠️ Pending | Need Notes/Reason columns |

---

## What Works Now

### Commands
```bash
python main.py --audit               # ✅ Full audit to Excel + SQLite
python main.py --generate-remediation # ✅ TSQL scripts
python main.py --finalize            # ⚠️ Diff only, no action_log
python main.py --apply-exceptions    # ⚠️ Reads Excel, needs columns
python main.py --check-drivers       # ✅ ODBC check
```

### Data Flow
- ✅ SQL Server → data_collector → Excel + SQLite
- ✅ SQLite → remediation_service → TSQL scripts
- ⚠️ Diff logic exists but action_log table missing
- ⚠️ Excel annotations read but columns not in sheets

---

## What Needs Work

### Priority 1: Schema Changes

Need to add `action_log` table:
```sql
CREATE TABLE action_log (
    id INTEGER PRIMARY KEY,
    initial_run_id INTEGER,
    entity_key TEXT,
    action_type TEXT,
    action_date TEXT,        -- Real timestamp
    action_description TEXT,
    captured_at TEXT
);
```

### Priority 2: Excel Columns

Add to each sheet:
- `Notes` column
- `Reason` column
- `Status Override` column (for exceptions)

### Priority 3: Refactor Commands

- `--sync`: Separate from `--finalize`
- `--sync`: Use `action_log` with real timestamps
- `--finalize`: Read Excel, persist everything

---

## File Map

| File | Purpose | Status |
|------|---------|--------|
| `audit_service.py` | Main audit orchestration | ✅ |
| `data_collector.py` | SQL Server data collection | ✅ |
| `remediation_service.py` | TSQL generation | ✅ |
| `finalize_service.py` | Diff logic | ⚠️ Needs refactor |
| `exception_service.py` | Excel → SQLite | ⚠️ Needs columns |
| `cli.py` | Command handlers | ⚠️ Needs --sync |
| `schema.py` | SQLite tables | ⚠️ Needs action_log |
| `report_writer.py` | Excel generation | ⚠️ Needs columns |

---

## Reading Order for New Devs

1. `docs/AUDIT_WORKFLOW.md` - Understand the lifecycle
2. `docs/SCHEMA_DESIGN.md` - Understand data model
3. `docs/CLI_REFERENCE.md` - Understand commands
4. `src/autodbaudit/application/data_collector.py` - Core collection logic
5. `src/autodbaudit/infrastructure/sqlite/schema.py` - All tables

---

*Last Updated: 2025-12-09*
