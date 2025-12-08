# AutoDBAudit - Project Status

> **TL;DR**: CLI works, generates 17-sheet Excel report. SQLite not wired yet.

---

## Current State (2025-12-08)

### ✅ Working
| What | Command/File |
|------|--------------|
| Full audit to Excel | `python main.py --audit` |
| 17-sheet report | All sheets populate with real data |
| Multi-instance | Audits all servers in `sql_targets.json` |
| SQL 2008-2025+ | Version-specific queries work |

### ⚠️ Exists But Not Wired
| What | Why |
|------|-----|
| SQLite HistoryStore | Code in `sqlite/store.py`, not called from `audit_service.py` |
| Schema v2 | Defined in `sqlite/schema.py`, never executed |

### ❌ Not Implemented
| What | Notes |
|------|-------|
| `--finalize` command | Would persist Excel annotations to SQLite |
| Historical diff | Requires SQLite first |
| Permission Grants sheet | Requirement #28 |

---

## Architecture Overview

```
main.py
  └── cli.py (argparse)
        └── AuditService.run_audit()
              ├── ConfigLoader.load() → sql_targets.json
              ├── SqlConnector.connect() for each target
              ├── AuditDataCollector.collect_all()
              │     └── Executes queries via QueryProvider
              └── EnhancedReportWriter.save()
                    └── Generates 17-sheet Excel
```

---

## File Quick Reference

| File | Purpose |
|------|---------|
| `cli.py` | Entry point, argument parsing |
| `audit_service.py` | Orchestrates the audit flow |
| `data_collector.py` | Collects all data from SQL Server |
| `sql/connector.py` | `SqlConnector` class with version detection |
| `sql/query_provider.py` | 2008 vs 2012+ query strategies (~1400 lines) |
| `excel/writer.py` | `EnhancedReportWriter` with 17 sheet mixins |

---

## Next Steps (Priority Order)

1. **SQLite Integration** - Wire `HistoryStore` into `audit_service.py`
2. **`--finalize` Command** - Read Excel annotations, store in SQLite
3. **Permission Grants Sheet** - Requirement #28
4. **Historical Diff** - Compare audit runs

---

*Last updated: 2025-12-08*
