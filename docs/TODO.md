# TODO Tracker

> **Last Updated**: 2025-12-16

---

## 🔴 High Priority (Current Sprint)

- [ ] **Phase 20B**: Action Log schema redesign
- [ ] **Phase 20C**: Q2 - SQL Agent off = WARNING logic
- [ ] **Manual E2E Test Execution** - User conducting "0 to 100" verification
- [x] **Phase 20A**: Foundation - Status columns, ##...## exclusion ✅ (2025-12-16)
  - [x] `parse_datetime_flexible()` for robust date handling
  - [x] Merged cell fix in annotation sync
  - [x] Q1: ##...## system logins excluded
  - [x] Q3: Role Matrix info-only
  - [x] STATUS_COLUMN + LAST_REVIEWED_COLUMN on all 14 sheets

---

## 🟡 Medium Priority

- [ ] **Dynamic Configuration**: Refactor `data_collector.py` to read `audit_config.json` rules instead of hardcoded `SECURITY_SETTINGS`.
- [ ] **Cross-Version Testing** - Verify SQL 2008 R2 compatibility explicitly
- [ ] **--deploy-hotfixes** - Implement the stubbed hotfix module

---

## ✅ Completed

### 2025-12-13: Developer Experience
- [x] **Colored Logging**: INFO=cyan, WARNING=yellow, ERROR=red, DEBUG=gray
- [x] **Config Examples**: Added comprehensive `.example.json` files with full schema
- [x] **Git Exclusions**: Actual config files excluded, examples preserved

### 2025-12-13: Version Build Compliance Checking
- [x] **Config**: Added `expected_builds` to audit_config.json for per-version targets
- [x] **Instances Sheet**: Added "Version Status" column with PASS/WARN styling
- [x] **Finding**: Version mismatches saved as WARN finding in SQLite
- [x] **Sync Stats**: Added debug logging for "since last sync" calculation

### 2025-12-13: Finalize Command Enhancement
- [x] **--finalize**: Added comprehensive safety checks (blocks if FAIL/WARN exist without exception)
- [x] **--force**: Added bypass flag for safety checks
- [x] **--finalize-status**: Added preview command to check readiness
- [x] **Archive**: Creates final Excel archive in `finalized/` folder
- [x] **Instance Name Fix**: Fixed Actions sheet showing "DEFAULT" for all instances
- [x] **Date Persistence**: Sync now preserves user-edited dates from existing Excel
- [x] **Rollback Scripts**: Now uncommented by default (ready to execute)

### 2025-12-13: Action Indicator Column
- [x] **Excel**: Added ⏳ Action column to 8 sheets (SA Account, Configuration, Logins, Roles, Linked Servers, Backups, Orphaned Users)
- [x] **Styling**: Added ACTION_BG color and ACTION Fill to excel_styles.py
- [x] **Helper**: Added ACTION_COLUMN definition and apply_action_needed_styling() to base.py
- [x] **Docs**: Updated excel_report_layout.md with new feature documentation
- [x] **Simulation Runner**: Created run_simulation.py with apply/revert modes
- [x] **SQL Fixes**: Patched 2019+.sql for SQL 2008 R2 compatibility (THROW -> RAISERROR)
- [x] **Instance ID**: Fixed multiple default instances via port detection

### 2025-12-12: E2E Prep & Architecture Refinement
- [x] **Schema Fix**: Solved `run_type` and `action_log` missing/crash (Fresh Start)
- [x] **Docs**: Created `E2E_TESTING_GUIDE.md` and updated `PROJECT_STATUS.md`
- [x] **Simulation**: Created `simulate_update.py` for version drift testing
- [x] **Sync Logic**: Verified time-travel diffing logic with unit tests
- [x] **Visuals**: Added Icons (🛡️/⚠️) and Headers to Remediation & Rollback scripts
- [x] **Security**: Moved passwords/secrets to separate `.secrets` file in output

### 2025-12-11: Environment Setup & Audit Test
- [x] Moved sql_targets.json to config/ folder
- [x] Added credential file loading
- [x] First audit on SQL 2025 Docker verified
- [x] Identified true SQLite schema (schema.py v2)

### 2025-12-09: Remediation & Status
- [x] `--apply-remediation` with dry-run/rollback
- [x] Smart Script Generation (4 categories)
- [x] `--status` Dashboard
- [x] SQLite Data Persistence (Findings)

---

## ⚠️ Known Issues

### "Ghost Tables"
The database schema contains tables like `logins`, `server_info`, `backups` that are currently **EMPTY**. The code only populates `findings` and `audit_runs`. This is by design for the current "Result-Based" architecture but may be confusing.

### Excel Overwrites
Currently, `main.py` tends to overwrite `audit_report_latest.xlsx`. A decision is needed on whether to keep historical Excel reports permanently or rely on the Database as the only history.

---

*Last Updated: 2025-12-15*

