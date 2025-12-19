# Technical Debt & Known Issues

**Last Updated:** 2025-12-20 01:45

---

## 🔴 CRITICAL (Causing Active Bugs)

### 1. Tests Don't Call sync_service.sync()

Current E2E tests only test annotation_sync methods in isolation.
They don't test actual CLI flow which is broken.

**Fix:** Create test that calls sync_service.sync() with real data.

### 2. Sheet Config Mismatches (Possibly)

User reports exceptions not detected, notes lost.
Need to audit ALL sheets:
- Excel writer columns
- annotation_sync config
- EXCEL_COLUMNS.md docs

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
