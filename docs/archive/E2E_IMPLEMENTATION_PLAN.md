# Comprehensive E2E Testing - Implementation Plan

> **Date**: 2025-12-19  
> **Status**: APPROVED  
> **Synced to**: docs/E2E_STATE_MATRIX.md (canonical state matrix)

---

## Objective

Create automated E2E tests verifying ALL exception/sync state transitions using centralized logic.

---

## Key Rules (From User)

1. **Status auto-populated**: When user adds justification to FAIL row, system auto-sets "Exception" status
2. **No clearing on PASS**: PASS rows with "Exception" dropdown → ignore (don't clear, don't log "removed")
3. **Centralized logic**: All exception determination uses `state_machine.py` and `stats_service.py`
4. **Field resilience**: Bad input → keep original, log warning

---

## Test File Structure

```python
# tests/test_comprehensive_e2e.py
class TestComprehensiveE2E(unittest.TestCase):
    """All 12 scenarios in one test file."""
    
    def test_01_fail_plus_justification_is_exception(self)
    def test_02_pass_plus_justification_is_note_only(self)
    def test_03_pass_with_exception_dropdown_ignored(self)
    def test_04_second_sync_no_duplicate_log(self)
    def test_05_fix_clears_exception(self)
    def test_06_regression(self)
    def test_07_regression_with_note_auto_exception(self)
    def test_08_exception_removed(self)
    def test_09_exception_persists(self)
    def test_10_bad_date_resilience(self)
    def test_11_third_sync_stability(self)
    def test_12_exception_text_edit(self)
```

---

## Implementation

See `tests/test_comprehensive_e2e.py` for full implementation.
