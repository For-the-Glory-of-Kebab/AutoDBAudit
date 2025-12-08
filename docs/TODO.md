# TODO Tracker

> **Purpose**: Track pending implementation items across the project.  
> **Update**: When you complete a TODO, move it to the "Completed" section.

---

## Completed – CLI Integration (2025-12-08)

- [x] Integrate `ExcelReportWriter` into `AuditService.run_audit()`
- [x] Create `AuditDataCollector` for modular data collection
- [x] CLI `--audit` command generates 17-sheet Excel report
- [ ] Connect SQLite history store to audit flow (deferred)
- [ ] Implement `--finalize` command for annotation persistence (deferred)

---

## Active – Code Quality

- [ ] Fix remaining lint warnings for `open()` encoding in `config_loader.py`
- [ ] Refine broad exception catches to specific types (data_collector.py)
- [ ] Remove unused imports across codebase

---

## Planned – Additional Features

- [ ] Permission Grants sheet (Requirement 28)
- [ ] Role Membership Matrix visualization
- [ ] Security Change Tracking (diff between audits)
- [ ] Implement `HotfixPlanner.load_mappings()`
- [ ] Implement `HotfixExecutor._run_remote_command()` via PowerShell Remoting
- [ ] Add Rich/Typer for better terminal UI
- [ ] Add progress bars for long operations

---

### Infrastructure Restructure (2025-12-08)
- [x] Create `sql/` subfolder (connector.py, query_provider.py)
- [x] Create `sqlite/` subfolder (store.py, schema.py)
- [x] Update all imports across codebase
- [x] Delete obsolete files (excel_report.py, sql_queries.py)

### Encryption Sheet (2025-12-08)
- [x] Add SMK/DMK/TDE queries to query_provider.py
- [x] Create `encryption.py` Excel sheet mixin
- [x] Add encryption data collection to data_collector.py
- [x] Report now has 17 sheets

### Excel Reporting (2025-12-08)
- [x] Implement `infrastructure/excel/` modular architecture
- [x] Create all 16 sheets with headers and styling
- [x] Add conditional formatting (icons, colors)
- [x] Implement server/instance grouping with color rotation
- [x] Add dropdown validation to all boolean/enum columns
- [x] Document sheets in `docs/excel_report_layout.md`

### Query Provider (2025-12-07)
- [x] Query folder restructure (sql2008 + sql2019plus)
- [x] Strategy pattern for SQL 2008-2025+ compatibility
- [x] All audit queries version-compatible

### Foundation (2025-12-06)
- [x] Project scaffold and documentation (Phase 0)
- [x] Modern Python 3.11+ typing throughout
- [x] Lazy logging conversion
- [x] Domain-driven project structure

---

*Last updated: 2025-12-08*
