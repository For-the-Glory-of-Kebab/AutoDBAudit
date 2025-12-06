# TODO Tracker

> **Purpose**: Track pending implementation items across the project.  
> **Update**: When you complete a TODO, move it to the "Completed" section.

---

## Phase 1 – Code Structure (Current)

- [ ] Fix remaining lint warnings for `open()` encoding in `config_loader.py`
- [ ] Refine broad exception catches to specific types

---

## Phase 2 – Domain & SQLite

- [ ] Implement `HistoryService.create_audit_run()` and other CRUD methods
- [ ] Create SQLite schema DDL in `infrastructure/history_store.py`
- [ ] Add schema versioning and migrations
- [ ] Consider adding `sql2022plus` folder if 2022/2025 need specific queries

---

## Phase 3 – Excel Reporting

- [ ] Implement `infrastructure/excel_writer.py` using openpyxl
- [ ] Create sheets: Audit Summary, Compliance, Discrepancies, ActionLog
- [ ] Add conditional formatting (icons, colors)
- [ ] Add charts (compliance pie, trend line)
- [ ] Support incremental mode (append to existing workbook)

---

## Phase 4 – Audit Logic

- [ ] Implement requirement checks in `application/audit_service.py`
- [ ] Create SQL queries in `queries/sql2008/` and `queries/sql2019plus/`
- [ ] Handle SQL 2008 R2 syntax differences (no STRING_AGG, TRY_CAST)
- [ ] Add discrepancy analysis and findings

---

## Phase 5 – Hotfix Orchestration

- [ ] Implement `HotfixPlanner.load_mappings()` 
- [ ] Implement `HotfixExecutor._run_remote_command()` via PowerShell Remoting
- [ ] Add pre-flight checks (disk space, connectivity)
- [ ] Implement resume and retry logic

---

## Phase 6 – Remediation Scripts

- [ ] Implement `RemediationService.generate_scripts()`
- [ ] Create T-SQL templates per requirement
- [ ] Implement comment-aware parsing for exception detection
- [ ] Track applied vs skipped actions

---

## Phase 7 – CLI Polish

- [ ] Add Rich/Typer for better terminal UI
- [ ] Add progress bars for long operations
- [ ] Implement `--hotfix-plan` dry-run mode
- [ ] Add confirmation prompts for destructive operations

---

## Requirements Expansion (New)

- [ ] Implement Linked Servers audit (Req 24-25)
- [ ] Implement Security Matrix audit sheets:
  - [ ] Server Logins sheet (by type: Windows/SQL)
  - [ ] Server Roles sheet
  - [ ] Database Users sheet (per DB)
  - [ ] Role Memberships sheet
  - [ ] Permission Grants sheet

---

## Completed

*(Move items here when done)*

- [x] Project scaffold and documentation (Phase 0)
- [x] Query folder restructure (sql2008 + sql2019plus)
- [x] Modern Python 3.11+ typing throughout
- [x] Lazy logging conversion

---

*Last updated: 2025-12-06*
