# E2E Test Findings - Phase 20
> **Date**: 2025-12-16
> **Status**: Triage & Planning
> **Mode**: Interactive/Collaborative

---

## 🎯 Key Insight

**The issues are interconnected.** Most problems trace back to:
1. **Annotation Sync reliability** - wrong columns, date parsing, merged cell handling
2. **Action Log schema** - append-only design not fully implemented
3. **Discrepancy detection** - inconsistent logic across sheets

**Recommended Approach**: Fix foundations first, then features.

---

## 📊 Revised Batch Strategy

| Phase | Focus | Why First |
|-------|-------|-----------|
| **A** | Foundation: Annotation Sync & Date Parsing | Everything depends on this |
| **B** | Foundation: Action Log Schema & Logic | Audit trail integrity |
| **C** | Discrepancy Logic Review | Per-sheet fixes |
| **D** | Stats & Reporting | Needs accurate data first |
| **E** | CLI & Finalize | Depends on all above |
| **F** | UX Polish | Last priority |

---

## Phase A: Foundation - Annotation Sync & Date Parsing 🔴

### A.1: Robust DateTime Parsing
**Problem**: Date formats like `12/16/2025` or `12/16/2025 10:49` don't register.

**Requirements**:
- Single `parse_datetime_flexible()` function
- Handle: `MM/DD/YYYY`, `YYYY-MM-DD`, `DD/MM/YYYY`, with/without time
- Handle: Excel date numbers vs strings
- Log parse errors (don't fail silently)
- Extra spaces should not break parsing

---

### A.2: Column-to-Data Mapping Audit
**Problem**: DateTime leaking into Notes column (Server Logins). Justifications not counting (Sensitive Roles).

**Action**: Comprehensive audit of annotation_sync SHEET_CONFIGS:
- [ ] Verify `key_cols` match actual Excel column positions
- [ ] Verify `editable_cols` map to correct columns
- [ ] Add column index assertions/logging
- [ ] Handle merged cells correctly in row detection

---

### A.3: Merged Cell Handling in Annotation Read
**Problem**: When Server/Instance cells are merged, some rows' justifications don't get read.

**Root Cause Investigation**: Does `_read_sheet_annotations()` check merged ranges? Probably reading empty cells.

---

## Phase B: Foundation - Action Log Schema & Logic 🔴

### B.1: Actions Sheet as Append-Only Changelog
**Current Problems**:
- Exception documentation not always appearing
- Date sync not working correctly
- First-run vs subsequent-run inconsistencies

**Design Clarification (Collab Needed)**:
```
ACTIONS SHEET BEHAVIOR:
- action_date: Immutable after first detection (NOT renewed on each sync)
- notes: User-editable (syncs back)
- New entries: Fixed, Regressed, Exception Documented, New Finding
- Never delete rows, only append
```

**Schema Review**: Does current action_log table match this design?

---

### B.2: Exception Documentation Logging
**Expected Flow**:
1. User adds Justification to ⏳ row
2. On `--sync`, detect new justification
3. Add "Exception Documented" entry to Actions sheet
4. Change ⏳ to ✅ (documented indicator)
5. This row should no longer count as "outstanding"

**Current Bug**: Not working for Backup sheet, Linked Servers sheet.

---

## Phase C: Discrepancy Logic Review 🟡

### C.1: Server Logins - ##MS_Policy*## Logins
**Question**: Are `##MS_PolicyEventProcessingLogin##` etc. discrepant?

**Research Finding**: These are SQL Server Policy-Based Management internal logins.
- Created automatically when PBM is used
- The `##` wrapper indicates system-generated
- Similar to certificate-mapped logins

**Recommendation**: Exclude from discrepancy (mark as system account).

---

### C.2: Services Sheet - SQL Agent Logic
**Question**: Is SQL Agent stopped/disabled a discrepancy?

**Current Logic**: Essential services (DB Engine, SQL Agent) when stopped = discrepancy
**Concern**: User may legitimately disable Agent on some servers

**Options**:
- (a) Keep as discrepancy (needs justification if disabled)
- (b) Only check if it's *supposed* to be running but isn't
- (c) Make configurable in audit_config.json

---

### C.3: Services Sheet - Instance Grouping
**Problems**:
- `MSSQL$LEGACY` = Database Engine (correct but separate)
- `MSSQLSERVER`, `MSSQLServerADHelper100` = "Other" (wrong)
- Docker `MSSQLSERVER` = "Other" (wrong)

**Fix**: Improve service type detection patterns.

---

### C.4: Client Protocols - Shared Memory Detection
**Problem**: Shared Memory shows disabled when enabled.

**Root Cause**: `CONNECTIONPROPERTY('net_transport')` shows *current* connection protocol, not *all enabled* protocols.

**Options**:
- (a) Accept limitation, add explanatory note
- (b) Research registry/DMV for actual enabled status
- (c) Return static "typically enabled" for Windows

---

### C.5: Databases Sheet - Trustworthy
**Explanation for user**:
- `TRUSTWORTHY = ON` allows database code to impersonate SQL Server logins
- **Security Risk**: Cross-database attacks, privilege escalation
- System DBs like `msdb` may need it ON (not discrepant)
- User DBs with TRUSTWORTHY ON = security concern = discrepancy

---

### C.6: Database Users - Guest User Logic
**Problem**: Guest discrepant in some DBs but not others.

**Expected Logic**:
- `guest` in `msdb`, `tempdb` = Expected (PASS)
- `guest` ENABLED in user databases = Discrepancy (they can access without explicit permission)
- `guest` DISABLED in user databases = PASS

**Action**: Verify this logic is correctly implemented.

---

### C.7: Role Matrix - Justification Field
**Problem**: No way to justify db_owner in Role Matrix.

**Decision Needed**:
- (a) Add Justification column to Role Matrix
- (b) Users justify in Database Roles sheet instead

---

### C.8: Backup Sheet - Exceptions Not Working
**New Finding**: `--finalize-status` shows most failures from Backup sheet despite exceptionalization.

**Investigate**: Is Backup sheet annotation sync configured correctly?

---

### C.9: Linked Servers - Sync Issue  
**New Finding**: 3 linked servers show discrepant despite exceptionalization.

**Investigate**: Linked Servers annotation sync config.

---

### C.10: Remote Access - Restart Required?
**Question**: Does disabling "remote access" require SQL Server restart?

**Answer**: Yes, `remote access` is a static setting requiring restart.

**Enhancement Request**:
- Query `sys.configurations` for `is_dynamic = 0` on changed settings
- Flag in remediation script: "⚠️ Requires SQL Server restart"
- Possibly query pending restart status from registry

---

## Phase D: Stats & Reporting Accuracy 🟡

### D.1: Console Stats vs Cover Sheet Mismatch
**Observed**:
- Cover Sheet: 17 critical, 30 warnings
- Console: 43 still failing

**Root Cause**: Different counting methods. Need unified metric.

---

### D.2: Verbose Sync Output
**Request**: Show counts for:
- Justifications synced
- Notes synced
- Dates synced
- Fixes (FAIL→PASS)
- Regressions (PASS→FAIL)
- Exceptions documented
- Outstanding items by category

---

### D.3: New CLI Command: --report
**Request**: Comprehensive console report of current state.
```
python main.py --report
```
Output: All fails, warnings, stats in readable format (mirrors Excel).

---

## Phase E: CLI & Finalize 🟡

### E.1: --finalize Path Resolution
**Error**: `No Excel file found. Close file and retry.`

**Fix**: Review file path logic in FinalizeService.

**DEPENDENCY**: Requires Phase A (annotation sync) working first.

---

## Phase F: UX Polish 🟢

### F.1: Toggle for "Mark as OK"
**Request**: Dropdown with "✓ Reviewed" instead of requiring text justification.

---

### F.2: Text Wrap for Long Fields
**Request**: Default text wrap for Justification/Notes columns.

---

### F.3: LAST_REVISED Column Universal
**Question**: Add to all sheets for consistency?

---

### F.4: Auto-Fit Width & Font Consistency
**Request**: Better default column widths, consistent fonts.

---

### F.5: Merged Notes Handling
**Recommendation**: ⚠️ SKIP - Too risky, breaks on reorder.

---

## Decision Points Summary

| # | Question | Options | Your Choice |
|---|----------|---------|-------------|
| 1 | ##MS_Policy*## logins | (a) Exclude from discrepancy (b) Keep as discrepant | |
| 2 | SQL Agent disabled | (a) Discrepancy (b) Only if supposed to run (c) Configurable | |
| 3 | Role Matrix justification | (a) Add column (b) Use DB Roles sheet | |
| 4 | LAST_REVISED universal | (a) Yes all sheets (b) Only some | |
| 5 | "Mark as OK" toggle | (a) Yes add dropdown (b) Keep justification-only | |

---

*Document Version: 2.0 | Revised Strategy | 2025-12-16*
