# Technical Debt & Known Issues

**Last Updated:** 2025-12-20 17:15

---

## 🔴 CRITICAL (Causing Active Bugs)

### 1. ~~Tests Don't Call sync_service.sync()~~ 
**STATUS: PARTIALLY RESOLVED** ✅

Created `test_ultimate_e2e.py` with 5 comprehensive tests covering all 16 sheets.
- All sheets annotation persistence (16/16 pass)
- Multi-sync stability verified
- Exception state transitions verified
- CLI stats match detected exceptions
- Per-sheet exception detection (15/16 support exceptions)

**Remaining:** Full integration test calling `sync_service.sync()` with mock SQL Server data.

### 2. Sheet Config Mismatches (Possibly)

User reports exceptions not detected, notes lost.
Need to audit ALL sheets:
- Excel writer columns
- annotation_sync config
- EXCEL_COLUMNS.md docs

### 3. Triggers Sheet Missing "Purpose" Column

E2E robust tests expect "Purpose" column but Triggers only has "Notes".
Tests `test_triggers_purpose_persistence` and `test_all_sheet_columns_exist` fail.
**Fix:** Either add Purpose column to Triggers or update tests.

---

## 🟡 MEDIUM (Code Quality)

### 1. annotation_sync.py Too Large

**Lines:** 1100+
**Should split into:**
- annotation_reader.py
- annotation_writer.py
- annotation_store.py
- exception_detector.py

### 2. Column Name Inconsistency

Some sheets use "Last Revised", others "Last Reviewed".
Should standardize.

---

## 🟢 LOW (Documented Quirks)

### 1. Triggers Sheet - Informational Only

No exception tracking. Only Purpose + Last Revised.
**Status:** DOCUMENTED ✅

### 2. Linked Servers Column Order

Purpose before Justification (unusual order).
**Status:** DOCUMENTED ✅

---

## Files to Archive

Moved to `docs/archive/`:
- SESSION_HANDOFF_2025-12-18_REFACTOR.md
- SESSION_HANDOFF_2025-12-19_BUGFIXES.md
- SESSION_HANDOFF_2025-12-19_TEST_COVERAGE.md
- E2E_IMPLEMENTATION_PLAN.md
- E2E_PHASE20_FINDINGS.md
- E2E_TESTING_STATUS.md
- HOTFIX_ORCHESTRATION.md
- SCHEMA_ALIGNMENT_ANALYSIS.md
