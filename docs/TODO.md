# TODO Tracker

> **Last Updated**: 2025-12-12

---

## 🔴 High Priority (Current Sprint)

- [ ] **Manual E2E Test Execution** - User conducting "0 to 100" verification
- [ ] 🧠 **Phase 4: Refinement & Advanced Logic**
  - [ ] **Excel**: Add indicator for discrepancies missing Fix/Justification
  - [ ] **Architecture**: Review Excel Lifecycle (One Working Copy vs Many Snapshots)
  - [ ] **Logic**: Handle Reversion (Pass -> Fail) in Action Log (Gray out previous fix?)

---

## 🟡 Medium Priority

- [ ] **Dynamic Configuration**: Refactor `data_collector.py` to read `audit_config.json` rules instead of hardcoded `SECURITY_SETTINGS`.
- [ ] **Cross-Version Testing** - Verify SQL 2008 R2 compatibility explicitly
- [ ] **--deploy-hotfixes** - Implement the stubbed hotfix module

---

## ✅ Completed

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

*Last Updated: 2025-12-12*
