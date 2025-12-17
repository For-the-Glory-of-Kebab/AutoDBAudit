# TODO Tracker

> **Last Updated**: 2025-12-17

---

## 🔴 High Priority (Current Sprint)

- [ ] **E2E Verification** - Run `--sync` and verify:
  - Exception counting matches manual count
  - Action Log sheet is populated
  - All justified items show ✅ indicator
- [ ] **User Testing** - User conducts "0 to 100" verification

---

## 🟡 Medium Priority

- [ ] **Dynamic Configuration** - Refactor `data_collector.py` to read `audit_config.json` rules instead of hardcoded `SECURITY_SETTINGS`
- [ ] **Cross-Version Testing** - Verify SQL 2008 R2 compatibility explicitly
- [ ] **--deploy-hotfixes** - Implement the stubbed hotfix module
- [ ] **Client Protocols User Notes** - Add distinct "User Notes" column separate from system "Notes"

---

## ✅ Completed (2025-12-17)

### Sync Engine Rebuild
- [x] **Phase 1: Core Infrastructure** - action_log schema consolidated, upsert_action returns ID
- [x] **Phase 2: Action Sheet Sync** - ID-based matching, user date/notes preserved
- [x] **Phase 3: Entity Diffing** - NEW entity_diff.py with 29 change types
- [x] **Phase 4: Instance Availability** - Unavailable instances handled correctly

### Sync Stabilization (2025-12-17)
- [x] **Excel File Lock** - Error out if file is open
- [x] **Exception Logic** - Check row status, ignore PASS rows
- [x] **Stats Accuracy** - Recalculate total exceptions from final report
- [x] **Issue Counts** - Exclude documented exceptions from "Drift/Issues" count
- [x] **Infinite Loop Fix** - Dedented `write_all_to_excel` in SyncService
- [x] **Action Log Crash** - Fixed SyntaxError in `add_action` method
- [x] **SA Account Key Collision** - Added "Current Name" to key columns
- [x] **Notes Column Detection** - Added to Sensitive Roles and other sheets
- [x] **Client Protocols Phantom Bug** - Removed "Notes" from editable columns
- [x] **Date Parsing** - ISO `T` separator support in `parse_datetime_flexible`
- [x] **Method Name Fix** - `get_last_successful_sync_run` → `get_previous_sync_run`

---

## ✅ Previously Completed

### 2025-12-16: Phase 20 Foundation
- [x] STATUS_COLUMN + LAST_REVIEWED_COLUMN on all 14 sheets
- [x] `parse_datetime_flexible()` for robust date handling
- [x] Merged cell fix in annotation sync
- [x] Q1: ##...## system logins excluded
- [x] Q3: Role Matrix info-only

### 2025-12-13: Version Build Compliance Checking
- [x] Added `expected_builds` to audit_config.json
- [x] Instances Sheet: "Version Status" column with PASS/WARN styling
- [x] Finalize command with safety checks
- [x] Action Indicator Column (⏳) on 8 sheets
- [x] Simulation Runner `run_simulation.py`

### 2025-12-12: E2E Prep & Architecture Refinement
- [x] Schema Fix: `run_type` and `action_log` crash (Fresh Start)
- [x] Sync Logic: Time-travel diffing logic with unit tests
- [x] Colored Logging: INFO=cyan, WARNING=yellow, ERROR=red

---

## ⚠️ Known Issues

### Results-Based Persistence
The database schema contains tables like `logins`, `server_info`, `backups` that are **EMPTY** by design. The code only populates `findings` and `audit_runs`. This is intentional for the current architecture.

### Excel Overwrites
Currently, `main.py` overwrites `audit_report_latest.xlsx`. Historical reports are stored in timestamped files.

---

*Keep this file synchronized with PROJECT_STATUS.md and session handoffs*
