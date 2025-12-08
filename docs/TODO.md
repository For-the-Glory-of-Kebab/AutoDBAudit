# TODO Tracker

> **Purpose**: Track pending implementation items across the project.  
> **Update**: When you complete a TODO, move it to the "Completed" section.

---

## Active – CLI Integration

- [ ] Integrate `ExcelReportWriter` into `AuditService.run_audit()`
- [ ] Connect SQLite history store to audit flow
- [ ] Generate `.db` file alongside Excel output
- [ ] Implement `--finalize` command for annotation persistence

---

## Active – Code Quality

- [ ] Fix remaining lint warnings for `open()` encoding in `config_loader.py`
- [ ] Refine broad exception catches to specific types
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

## Completed ✅

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
