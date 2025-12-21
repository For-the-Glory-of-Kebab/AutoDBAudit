# Atomic E2E Test Specifications

> **Date**: 2025-12-21  
> **Status**: ACTIVE REFERENCE DOCUMENT  
> **Purpose**: Detailed specification of all test scenarios, assertions, and edge cases

---

## Table of Contents
1. [Field Types & Validation Rules](#1-field-types--validation-rules)
2. [Exception Logic (Canonical)](#2-exception-logic-canonical)
3. [State Transitions (Complete)](#3-state-transitions-complete)
4. [Per-Sheet Test Scenarios](#4-per-sheet-test-scenarios)
5. [Action Log Verification](#5-action-log-verification)
6. [Stats Verification](#6-stats-verification)
7. [Edge Cases & Gotchas](#7-edge-cases--gotchas)

---

## 1. Field Types & Validation Rules

### 1.1 Editable Field Types

| Field Type | Column Names | Valid Values | Persistence |
|------------|--------------|--------------|-------------|
| **Notes** | Notes, Purpose | Any text | Always preserved |
| **Date** | Last Reviewed, Last Revised | ISO date, Excel date, free text | Preserve original on error |
| **Justification** | Justification, Exception Reason | Any text | Triggers exception if discrepant |
| **Review Status** | Review Status | "Exception", "Needs Review", empty | Dropdown validation |

### 1.2 Column Naming Variations

> [!WARNING]
> Different sheets use different column names for the same concept!

| Concept | Variations |
|---------|------------|
| Justification | `Justification`, `Exception Reason` |
| Date | `Last Reviewed`, `Last Revised` |
| Notes | `Notes`, `Purpose` (Linked Servers only) |

### 1.3 Validation Rules

```python
# Review Status validation
VALID_REVIEW_STATUSES = ["Exception", "Needs Review", ""]

# Date parsing - accept multiple formats
def parse_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    try:
        return dateutil.parser.parse(value)
    except:
        return value  # Keep as-is, log warning

# Text fields - preserve exactly
def normalize_text(value):
    if value is None:
        return None
    return str(value).strip() or None
```

---

## 2. Exception Logic (Canonical)

### 2.1 Exception Definition

A row is **exceptioned** if and only if:

```python
def is_exception(status: str, justification: str, review_status: str) -> bool:
    """
    Canonical exception check - SINGLE SOURCE OF TRUTH.
    
    This function MUST be used everywhere:
    - Exception detection
    - Action logging  
    - CLI stats
    - Excel indicators
    """
    is_discrepant = status in ("FAIL", "WARN")
    has_justification = bool(justification and justification.strip())
    has_exception_status = review_status == "Exception"
    
    return is_discrepant and (has_justification or has_exception_status)
```

### 2.2 Exception State Table

| Row Status | Justification | Review Status | Is Exception? | Action |
|------------|---------------|---------------|---------------|--------|
| PASS | No | - | ❌ No | - |
| PASS | Yes | - | ❌ No | Saved as note |
| PASS | - | Exception | ❌ **Invalid** | Ignore dropdown |
| FAIL | No | - | ❌ No | Active issue |
| FAIL | Yes | - | ✅ **Yes** | Exception documented |
| FAIL | No | Exception | ✅ **Yes** | Exception via dropdown |
| FAIL | Yes | Exception | ✅ **Yes** | Full exception |
| WARN | No | - | ❌ No | Active warning |
| WARN | Yes | - | ✅ **Yes** | Exception documented |
| WARN | No | Exception | ✅ **Yes** | Exception via dropdown |

### 2.3 Auto-Population Rules

| Condition | System Action |
|-----------|---------------|
| FAIL/WARN + Justification added | Auto-set Review Status to "Exception" |
| PASS + Exception dropdown | **Ignore** (don't clear, don't log "removed") |
| PASS + Justification | Keep as note (no status change) |

---

## 3. State Transitions (Complete)

### 3.1 All Valid Transitions

| # | Previous State | Current State | ChangeType | Should Log? | Notes |
|---|----------------|---------------|------------|-------------|-------|
| 1 | None (new) | FAIL | NEW_ISSUE | ✅ Yes | First appearance |
| 2 | None (new) | WARN | NEW_ISSUE | ✅ Yes | First appearance |
| 3 | None (new) | PASS | NO_CHANGE | ❌ No | Nothing to report |
| 4 | FAIL | PASS | FIXED | ✅ Yes | Issue resolved |
| 5 | WARN | PASS | FIXED | ✅ Yes | Warning resolved |
| 6 | FAIL + Exc | PASS | FIXED | ✅ Yes | Exception becomes history |
| 7 | PASS | FAIL | REGRESSION | ✅ Yes | Was compliant, now failing |
| 8 | PASS | WARN | REGRESSION | ✅ Yes | Was compliant, now warning |
| 9 | PASS + Note | FAIL | REGRESSION | ✅ Yes | Note becomes auto-exception! |
| 10 | FAIL | FAIL | STILL_FAILING | ❌ No | No change |
| 11 | WARN | WARN | STILL_FAILING | ❌ No | No change |
| 12 | FAIL | FAIL + Just | EXCEPTION_ADDED | ✅ Yes | Documented exception |
| 13 | FAIL | FAIL + Status | EXCEPTION_ADDED | ✅ Yes | Via dropdown |
| 14 | FAIL + Exc | FAIL (cleared) | EXCEPTION_REMOVED | ✅ Yes | User removed both |
| 15 | FAIL + Exc | FAIL + Exc | NO_CHANGE | ❌ No | Stable |
| 16 | FAIL + Exc(v1) | FAIL + Exc(v2) | EXCEPTION_UPDATED | ⚠️ Optional | Text changed |
| 17 | FAIL | None | UNKNOWN | ❌ No | Instance unavailable? |

### 3.2 Priority Rules (Concurrent Events)

When multiple events happen in ONE sync:

```python
PRIORITY = [
    ChangeType.FIXED,           # 1st - Fix always wins
    ChangeType.REGRESSION,      # 2nd  
    ChangeType.EXCEPTION_ADDED, # 3rd (only if not fixed)
    ChangeType.EXCEPTION_REMOVED, # 4th
    ChangeType.STILL_FAILING,   # Last (no log)
]
```

**Critical**: If FIXED + EXCEPTION_ADDED both apply → **FIXED wins**, exception cleared.

### 3.3 What Does NOT Trigger "Exception Removed"

> [!CAUTION]
> These should **NEVER** log "Exception Removed":

1. ❌ PASS row with "Exception" dropdown → just ignore
2. ❌ Exception row becomes PASS → that's FIXED (not removed)
3. ❌ PASS row had justification → stays PASS → just a note
4. ❌ User adds exception dropdown to PASS row → ignore on regeneration

**Only trigger when**:
- Row is **still FAIL/WARN**, AND
- User **explicitly cleared BOTH** justification AND status

---

## 4. Per-Sheet Test Scenarios

### 4.1 Universal Test Template (All Sheets)

```python
class SheetTestTemplate:
    """
    Every sheet must pass ALL of these tests.
    Customize key_columns and editable_columns per sheet.
    """
    
    # Layer 1: Simple Fields
    def test_L1_01_add_single_note(self):
        """Add note to row 2, verify exact value after sync."""
        
    def test_L1_02_add_multiple_notes_random(self):
        """Add 1-5 notes to random rows, verify all preserved."""
        
    def test_L1_03_modify_note(self):
        """Change existing note, verify update applied."""
        
    def test_L1_04_clear_note(self):
        """Clear note, verify empty after sync."""
        
    def test_L1_05_add_date(self):
        """Add date value, verify format preserved."""
        
    def test_L1_06_multi_sync_notes_stable(self):
        """Sync 3 times, notes remain exactly as set."""
        
    def test_L1_07_no_scrambling(self):
        """Add notes to rows 2,4,6 - verify row 3,5 untouched."""
        
    # Layer 2: Exception Detection  
    def test_L2_01_fail_plus_justification_is_exception(self):
        """FAIL row + justification = exception detected."""
        
    def test_L2_02_fail_plus_status_is_exception(self):
        """FAIL row + status dropdown = exception detected."""
        
    def test_L2_03_fail_plus_both_is_exception(self):
        """FAIL row + justification + status = exception."""
        
    def test_L2_04_multiple_exceptions_random(self):
        """Add 1-5 exceptions to random FAIL rows."""
        
    def test_L2_05_no_duplicate_detection(self):
        """Sync twice, same exception not re-logged."""
        
    def test_L2_06_warn_plus_justification_is_exception(self):
        """WARN row + justification = exception detected."""
        
    # Layer 3: Non-Discrepant Rows
    def test_L3_01_pass_plus_justification_is_note(self):
        """PASS row + justification = note only, NOT exception."""
        
    def test_L3_02_pass_plus_status_ignored(self):
        """PASS row + exception status = ignored."""
        
    def test_L3_03_no_exception_count_for_pass(self):
        """Stats should show 0 exceptions for PASS rows."""
        
    def test_L3_04_pass_note_survives_syncs(self):
        """PASS row note preserved across 3 syncs."""
        
    # Layer 4: State Transitions
    def test_L4_01_fail_to_pass_is_fixed(self):
        """FAIL → PASS = FIXED logged."""
        
    def test_L4_02_pass_to_fail_is_regression(self):
        """PASS → FAIL = REGRESSION logged."""
        
    def test_L4_03_exception_to_pass_is_fixed(self):
        """FAIL + Exception → PASS = FIXED (exception history)."""
        
    def test_L4_04_exception_cleared_is_removed(self):
        """FAIL + Exception → FAIL (no just/status) = REMOVED."""
        
    def test_L4_05_still_failing_no_log(self):
        """FAIL → FAIL = no new log entry."""
        
    def test_L4_06_pass_with_note_regresses_is_auto_exception(self):
        """PASS + note → FAIL = REGRESSION + auto-exception."""
        
    def test_L4_07_fix_beats_exception(self):
        """FAIL + Exception added in same sync as PASS = FIXED wins."""
        
    # Layer 5: Multi-Sync Stability
    def test_L5_01_three_sync_stability(self):
        """3 syncs, no modifications, counts stable."""
        
    def test_L5_02_progressive_modifications(self):
        """Sync 1: add, Sync 2: modify, Sync 3: verify."""
        
    def test_L5_03_no_action_log_duplicates(self):
        """Same exception across syncs = 1 log entry total."""
        
    def test_L5_04_mixed_operations(self):
        """Add some, modify some, clear some, verify all."""
        
    # Layer 6: Combinations
    def test_L6_01_notes_and_justification_together(self):
        """Same row has both notes and justification."""
        
    def test_L6_02_mixed_pass_fail_annotations(self):
        """Some PASS with notes, some FAIL with exceptions."""
        
    def test_L6_03_random_chaos(self, seed):
        """Random mix of all operations, verify consistency."""
```

### 4.2 Sheet-Specific Configurations

```python
SHEET_TEST_CONFIGS = {
    "SA Account": {
        "key_columns": ["Server", "Instance", "Current Name"],
        "editable_columns": ["Review Status", "Justification", "Last Reviewed", "Notes"],
        "supports_exceptions": True,
        "sample_data": {"Current Name": "sa_renamed", "Is Disabled": "✓", ...},
    },
    "Linked Servers": {
        "key_columns": ["Server", "Instance", "Linked Server"],
        "editable_columns": ["Review Status", "Justification", "Last Reviewed"],
        # NOTE: NO "Purpose" column per EXCEL_COLUMNS.md!
        "supports_exceptions": True,
        "known_issues": ["Column detection 'Server' vs 'Linked Server' bug"],
    },
    "Triggers": {
        "key_columns": ["Server", "Instance", "Scope", "Database", "Trigger Name"],
        "editable_columns": ["Review Status", "Justification", "Last Reviewed"],
        "supports_exceptions": True,
        "notes": "Scope-based keys",
    },
    "Encryption": {
        "key_columns": ["Server", "Instance", "Key Type", "Key Name"],
        "editable_columns": ["Notes"],
        "supports_exceptions": False,  # Notes only!
    },
    # ... all 20 sheets ...
}
```

---

## 5. Action Log Verification

### 5.1 Action Log Schema

```sql
CREATE TABLE action_log (
    id INTEGER PRIMARY KEY,
    initial_run_id INTEGER NOT NULL,
    sync_run_id INTEGER,
    entity_key TEXT NOT NULL,
    action_type TEXT NOT NULL,      -- Fixed, Regression, Exception, etc.
    status TEXT NOT NULL,           -- open, closed, exception
    action_date TEXT NOT NULL,      -- ISO format
    user_date_override TEXT,        -- User's manual date
    description TEXT,
    finding_type TEXT,              -- Category: Login, Config, etc.
    notes TEXT,                     -- User commentary
    UNIQUE(initial_run_id, entity_key, action_type, sync_run_id)
);
```

### 5.2 Verification Assertions

```python
def assert_action_logged(
    entity_key: str,
    expected_type: ChangeType,
    sync_run_id: int,
):
    """Verify action was logged exactly once."""
    entries = get_action_log_entries(entity_key=entity_key, sync_run_id=sync_run_id)
    matching = [e for e in entries if e["action_type"] == expected_type.value]
    assert len(matching) == 1, f"Expected 1 {expected_type} entry, got {len(matching)}"

def assert_no_action_logged(
    entity_key: str,
    unwanted_type: ChangeType,
):
    """Verify action was NOT logged."""
    entries = get_action_log_entries(entity_key=entity_key)
    matching = [e for e in entries if e["action_type"] == unwanted_type.value]
    assert len(matching) == 0, f"Unexpected {unwanted_type} entry found"

def assert_no_duplicates():
    """Verify no duplicate action entries exist."""
    all_entries = get_all_action_log_entries()
    keys = [(e["entity_key"], e["action_type"], e["sync_run_id"]) for e in all_entries]
    assert len(keys) == len(set(keys)), "Duplicate action log entries found"
```

### 5.3 Expected Action Mapping

| Event | action_type | status |
|-------|-------------|--------|
| New FAIL | NEW_ISSUE | open |
| FAIL → PASS | FIXED | closed |
| PASS → FAIL | REGRESSION | open |
| Exception added | EXCEPTION_ADDED | exception |
| Exception removed | EXCEPTION_REMOVED | open |
| Exception text changed | EXCEPTION_UPDATED | exception |

---

## 6. Stats Verification

### 6.1 CLI Stats Structure

```python
@dataclass
class SyncStats:
    # Current State
    total_findings: int
    active_issues: int      # FAIL/WARN without exception
    documented_exceptions: int
    compliant_items: int    # PASS
    
    # Changes from Baseline
    fixed_since_baseline: int
    regressions_since_baseline: int
    new_issues_since_baseline: int
    
    # Changes from Last Sync
    fixed_since_last: int
    regressions_since_last: int
    new_issues_since_last: int
```

### 6.2 Verification Rules

```python
def verify_stats(stats: SyncStats, expected: dict):
    """Verify CLI stats match expected values."""
    
    for key, expected_value in expected.items():
        actual_value = getattr(stats, key)
        assert actual_value == expected_value, (
            f"Stats mismatch: {key} expected {expected_value}, got {actual_value}"
        )

# Example test
def test_exception_count_accurate():
    # Add 3 exceptions
    for row in [2, 4, 6]:
        harness.add_annotation(row, "Justification", "Test reason")
    
    result = harness.run_sync_cycle()
    
    verify_stats(result.cli_stats, {
        "documented_exceptions": 3,
        "active_issues": total_fail_rows - 3,
    })
```

---

## 7. Edge Cases & Gotchas

### 7.1 Column Detection Issues

> [!CAUTION]
> **THE ROOT CAUSE OF CURRENT FAILURES**

```python
# BUG: Partial string matching
if key_col.lower() in header.lower():  # "server" in "linked server" = True!

# FIX: Exact match first, then partial
if key_col.lower() == header.lower():  # Exact match
    return col_idx
# ... then fallback to partial
```

**Test for this**:
```python
def test_server_vs_linked_server_column_detection():
    """'Server' column must not match 'Linked Server' header."""
    # Create Linked Servers sheet
    # Add data to both 'Server' and 'Linked Server' columns
    # Verify key detection uses correct column
```

### 7.2 Merged Cell Handling

```python
# When reading merged cells, track last value
last_key_values = {}

for row in sheet.iter_rows():
    for i, col_idx in enumerate(key_cols):
        cell = row[col_idx]
        value = cell.value
        
        if value is None and is_merged(cell):
            value = last_key_values.get(i, '')
        else:
            last_key_values[i] = value
```

**Test for this**:
```python
def test_merged_cell_key_detection():
    """Keys in merged cells should use parent cell value."""
```

### 7.3 Instance Unavailable

```python
def test_instance_unavailable_not_false_fixed():
    """
    If instance wasn't scanned, don't mark findings as FIXED.
    
    Scenario:
    - Baseline: Instance A has 5 FAILs
    - Sync: Instance A unreachable
    - Result: Should NOT show 5 FIXED
    """
```

### 7.4 Date Format Chaos

```python
def test_date_format_variations():
    """Various date formats should be handled gracefully."""
    test_dates = [
        "2025-12-21",           # ISO
        "12/21/2025",           # US format
        "21-Dec-2025",          # Human
        "not a date",           # Invalid
        "",                     # Empty
        None,                   # Null
    ]
    # All should preserve original value if unparseable
```

### 7.5 Whitespace Handling

```python
def test_whitespace_trimming():
    """Whitespace-only values should be treated as empty."""
    harness.add_annotation(2, "Justification", "   ")
    result = harness.run_sync_cycle()
    
    # Should NOT be treated as having justification
    assert result.exception_count == 0
```

### 7.6 Row Reordering (Actions Sheet)

```python
def test_actions_sheet_row_reorder():
    """Actions sheet uses ID matching, not row position."""
    # 1. Create actions
    # 2. Manually reorder rows in Excel (simulate user sort)
    # 3. Sync
    # 4. Verify correct actions matched by ID
```

---

## Quick Reference: Test Coverage Checklist

For each sheet, verify:

- [ ] **L1**: Notes add/modify/clear
- [ ] **L1**: Dates preserved
- [ ] **L1**: No data scrambling
- [ ] **L2**: Exception via justification
- [ ] **L2**: Exception via status
- [ ] **L2**: No duplicate detection
- [ ] **L3**: PASS + justification = note only
- [ ] **L3**: PASS + status = ignored
- [ ] **L4**: FIXED transition
- [ ] **L4**: REGRESSION transition
- [ ] **L4**: EXCEPTION_REMOVED
- [ ] **L5**: 3+ sync stability
- [ ] **L5**: No action duplicates
- [ ] **L6**: Mixed operations
- [ ] **Actions**: Correct entries logged
- [ ] **Stats**: Correct counts

---

## 8. Controlled Randomization Strategy

### 8.1 The Problem with Pure Randomness

Pure random testing is dangerous because:
- Seed says "test 0 exceptions" → unacceptable
- Seed says "run 10 million syncs" → impractical
- Random might never hit a critical combination
- Can't reliably reproduce failures

### 8.2 Constrained Randomization Design

```python
class ConstrainedRandomizer:
    """
    Controlled randomization with GUARANTEED coverage.
    
    Key Principle: Random variations WITHIN guaranteed bounds.
    """
    
    def __init__(self, seed: int = None):
        self.seed = seed or int(time.time())
        self.rng = random.Random(self.seed)
        self._log_seed()
    
    def _log_seed(self):
        """Always log seed for reproducibility."""
        logger.info(f"[RANDOMIZER] Seed={self.seed} - save this to reproduce!")
    
    # === CONSTRAINTS ===
    # These guarantee minimum coverage
    
    MIN_EXCEPTIONS_TO_TEST = 2
    MAX_EXCEPTIONS_TO_TEST = 5
    MIN_SYNCS = 2
    MAX_SYNCS = 5
    MIN_ROWS_MODIFIED = 2
    MAX_ROWS_MODIFIED = 8
    
    def count_exceptions(self) -> int:
        """Random count BUT always >= MIN."""
        return self.rng.randint(
            self.MIN_EXCEPTIONS_TO_TEST, 
            self.MAX_EXCEPTIONS_TO_TEST
        )
    
    def count_syncs(self) -> int:
        """Random sync count BUT always >= MIN."""
        return self.rng.randint(self.MIN_SYNCS, self.MAX_SYNCS)
    
    def select_rows(self, available: List[int], category: str) -> List[int]:
        """
        Select random rows but ENSURE mix of PASS and FAIL.
        
        Args:
            available: Available row numbers
            category: 'pass', 'fail', or 'mixed'
        """
        count = self.rng.randint(
            self.MIN_ROWS_MODIFIED,
            min(self.MAX_ROWS_MODIFIED, len(available))
        )
        return self.rng.sample(available, count)
```

### 8.3 Guaranteed Coverage Matrix

Every test run MUST hit all of these:

| Category | Minimum | Maximum | What |
|----------|---------|---------|------|
| Discrepant rows with exception | 2 | 5 | FAIL + justification |
| Discrepant rows NO exception | 1 | 3 | FAIL, no justification |
| Non-discrepant with note | 2 | 4 | PASS + justification (note only) |
| Non-discrepant clean | 1 | 3 | PASS, no annotations |
| Sync cycles | 2 | 5 | Always multi-sync |
| Modifications per sync | 1 | 3 | Add, modify, or clear |

### 8.4 Coverage Enforcement

```python
class CoverageTracker:
    """
    Tracks what the randomizer covered to ensure completeness.
    """
    
    def __init__(self):
        self.coverage = {
            'fail_with_just': 0,
            'fail_with_status': 0,
            'fail_with_both': 0,
            'fail_no_exception': 0,
            'pass_with_note': 0,
            'pass_clean': 0,
            'syncs_run': 0,
            'modifications': 0,
        }
    
    def validate(self):
        """Assert minimum coverage was achieved."""
        assert self.coverage['fail_with_just'] >= 1, "Must test justification-only"
        assert self.coverage['fail_with_status'] >= 1, "Must test status-only"
        assert self.coverage['pass_with_note'] >= 1, "Must test PASS + note"
        assert self.coverage['syncs_run'] >= 2, "Must test multi-sync"
```

### 8.5 Example: Exception Detection Test

```python
def test_L2_exception_detection_randomized(self, seed=None):
    """
    Randomized exception detection BUT with guaranteed coverage.
    """
    rand = ConstrainedRandomizer(seed)
    tracker = CoverageTracker()
    
    # Get available FAIL rows (from mock data)
    fail_rows = self.get_discrepant_rows()  # e.g., [2, 4, 6, 8]
    pass_rows = self.get_non_discrepant_rows()  # e.g., [3, 5, 7]
    
    # === GUARANTEED: At least 1 of each type ===
    # Justification only
    just_rows = rand.select_rows(fail_rows[:2], 'fail')
    for row in just_rows:
        self.add_annotation(row, 'Justification', rand.random_text())
        tracker.coverage['fail_with_just'] += 1
    
    # Status only
    status_rows = rand.select_rows(fail_rows[2:3], 'fail')
    for row in status_rows:
        self.add_annotation(row, 'Review Status', 'Exception')
        tracker.coverage['fail_with_status'] += 1
    
    # PASS + note (NOT exception)
    note_rows = rand.select_rows(pass_rows, 'pass')
    for row in note_rows:
        self.add_annotation(row, 'Justification', rand.random_text())
        tracker.coverage['pass_with_note'] += 1
    
    # Run random number of syncs
    for _ in range(rand.count_syncs()):
        self.run_sync_cycle()
        tracker.coverage['syncs_run'] += 1
    
    # Validate coverage
    tracker.validate()
    
    # Assert expectations
    self.assert_exception_count(len(just_rows) + len(status_rows))
```

---

## 9. Invalid Input & Graceful Handling

### 9.1 Every Field Must Be Tested With Invalid Data

| Field | Invalid Inputs to Test | Expected Behavior |
|-------|------------------------|-------------------|
| Review Status | "Invalid", "exception", "EXCEPTION", 123, None, "" | Ignore invalid, keep default |
| Justification | Whitespace-only "   ", Unicode garbage, Very long (10000 chars) | Treat whitespace as empty, preserve rest |
| Last Reviewed | "not a date", "12/32/2025", "yesterday", 12345, None | Keep original, log warning |
| Notes | Binary data, SQL injection, HTML tags | Preserve as-is (text field) |
| Purpose | Same as Notes | Preserve as-is |

### 9.2 Test Scenarios

```python
class TestInvalidInputHandling:
    """Every sheet must pass these tests."""
    
    def test_invalid_review_status_ignored(self):
        """Invalid Review Status values should be ignored."""
        invalid_values = [
            "Invalid",
            "exception",  # lowercase
            "NEEDS_REVIEW",
            123,
            True,
            "Exception with extra text",
        ]
        for val in invalid_values:
            self.add_annotation(row=2, col='Review Status', value=val)
            self.run_sync_cycle()
            # Should NOT count as exception
            self.assert_exception_count(0)
    
    def test_whitespace_justification_is_empty(self):
        """Whitespace-only justification = no exception."""
        self.add_annotation(row=2, col='Justification', value='   \t\n  ')
        self.run_sync_cycle()
        self.assert_exception_count(0)
    
    def test_bad_date_preserves_original(self):
        """Invalid date should preserve original, not crash."""
        self.add_annotation(row=2, col='Last Reviewed', value='not a date')
        result = self.run_sync_cycle()
        # Should log warning but not fail
        self.assert_no_errors(result)
        # Original value should be preserved
        self.assert_value_preserved(row=2, col='Last Reviewed')
    
    def test_very_long_text_preserved(self):
        """Long text should be preserved without truncation."""
        long_text = 'A' * 10000
        self.add_annotation(row=2, col='Notes', value=long_text)
        self.run_sync_cycle()
        self.assert_value_exact(row=2, col='Notes', expected=long_text)
    
    def test_unicode_preserved(self):
        """Unicode characters should be preserved."""
        unicode_text = '日本語 🔥 العربية émoji'
        self.add_annotation(row=2, col='Notes', value=unicode_text)
        self.run_sync_cycle()
        self.assert_value_exact(row=2, col='Notes', expected=unicode_text)
    
    def test_special_characters_preserved(self):
        """SQL-like special chars should be preserved, not interpreted."""
        special = "O'Brien; DROP TABLE users;--"
        self.add_annotation(row=2, col='Notes', value=special)
        self.run_sync_cycle()
        self.assert_value_exact(row=2, col='Notes', expected=special)
```

### 9.3 Graceful Error Handling Tests

```python
def test_excel_file_locked(self):
    """Should error gracefully if Excel file is open."""
    # Lock the file
    with open(self.excel_path, 'r+b') as f:
        result = self.run_sync_cycle()
    # Should NOT crash, should log error
    self.assert_graceful_error(result, contains='file is open')

def test_db_connection_lost(self):
    """Should handle DB connection loss gracefully."""
    self.close_db_connection()
    result = self.run_sync_cycle()
    self.assert_graceful_error(result)
```

---

## 10. Instance Unavailability Testing

### 10.1 The Problem

If an instance is scanned in Sync 1 but unavailable in Sync 2:
- All its FAIL findings "disappear"
- Naive logic would mark them as FIXED (WRONG!)
- User loses exception documentation

### 10.2 Correct Behavior

| Sync 1 | Sync 2 Instance Status | Expected Result |
|--------|------------------------|----------------|
| FAIL | Unavailable | UNKNOWN (not FIXED) |
| FAIL + Exception | Unavailable | Exception preserved, no action log |
| PASS | Unavailable | No change |

### 10.3 Test Scenarios

```python
class TestInstanceUnavailability:
    """Test behavior when instances become unavailable between syncs."""
    
    def test_unavailable_instance_not_marked_fixed(self):
        """
        If instance was FAIL but is now unavailable, should NOT be FIXED.
        """
        # Sync 1: Instance has 3 FAIL findings
        self.run_sync_cycle(instances=['instance1'], findings=[
            {'key': 'instance1|login1', 'status': 'FAIL'},
            {'key': 'instance1|login2', 'status': 'FAIL'},
            {'key': 'instance1|login3', 'status': 'FAIL'},
        ])
        
        # Sync 2: Instance unavailable (no findings returned)
        self.run_sync_cycle(instances=[], findings=[])
        
        # Should NOT log "FIXED" for these
        fixed_actions = self.get_actions(type='FIXED')
        assert len(fixed_actions) == 0, "Should not mark unavailable as FIXED"
    
    def test_exception_preserved_when_unavailable(self):
        """
        Exception documentation survives instance unavailability.
        """
        # Sync 1: Add exception to FAIL finding
        self.run_sync_cycle(findings=[{'key': 'k1', 'status': 'FAIL'}])
        self.add_annotation(row=2, col='Justification', value='Documented')
        self.run_sync_cycle(findings=[{'key': 'k1', 'status': 'FAIL'}])
        
        # Sync 3: Instance unavailable
        self.run_sync_cycle(instances=[], findings=[])
        
        # Exception should still be in DB
        ann = self.get_annotation('k1')
        assert ann['justification'] == 'Documented'
    
    def test_instance_returns_after_unavailable(self):
        """
        When instance comes back, findings should resume correctly.
        """
        # Sync 1: FAIL findings
        self.run_sync_cycle(findings=[{'key': 'k1', 'status': 'FAIL'}])
        
        # Sync 2: Unavailable
        self.run_sync_cycle(instances=[], findings=[])
        
        # Sync 3: Back online, now PASS
        self.run_sync_cycle(findings=[{'key': 'k1', 'status': 'PASS'}])
        
        # NOW it should be FIXED
        fixed_actions = self.get_actions(type='FIXED')
        assert len(fixed_actions) == 1
    
    def test_partial_instance_availability(self):
        """
        Some instances available, some not.
        """
        # Sync 1: Two instances with FAILs
        self.run_sync_cycle(findings=[
            {'key': 'inst1|login', 'status': 'FAIL'},
            {'key': 'inst2|login', 'status': 'FAIL'},
        ])
        
        # Sync 2: Only inst1 available, and it's now PASS
        self.run_sync_cycle(
            scanned_instances=['inst1'],
            findings=[{'key': 'inst1|login', 'status': 'PASS'}]
        )
        
        # inst1 should be FIXED, inst2 should be UNKNOWN
        fixed = self.get_actions(type='FIXED')
        assert len(fixed) == 1
        assert 'inst1' in fixed[0]['entity_key']
```

### 10.4 Implementation Requirement

```python
def is_valid_for_fixed_check(entity_key: str, scanned_instances: set[str]) -> bool:
    """
    Only mark as FIXED if we actually scanned the instance.
    
    This prevents false FIXED when instance is just unavailable.
    """
    # Extract server|instance from entity key
    parts = entity_key.split('|')
    if len(parts) >= 2:
        server_instance = f"{parts[0]}|{parts[1]}"
        return server_instance in scanned_instances
    return False
```

---

## 11. Schema Consistency Checklist (Per Sheet)

Before testing each sheet, verify:

- [ ] `EXCEL_COLUMNS.md` matches actual `writer.py` columns
- [ ] `annotation_sync.py` `key_cols` match actual headers
- [ ] `annotation_sync.py` `editable_cols` match actual headers
- [ ] Status/Action column detection works
- [ ] Key column detection doesn't have substring collisions

### Example: Linked Servers Validation

```python
def test_linked_servers_schema_consistency(self):
    """Ensure code matches docs for Linked Servers."""
    from autodbaudit.infrastructure.excel.linked_servers import LINKED_SERVER_COLUMNS
    from autodbaudit.application.annotation_sync import SHEET_ANNOTATION_CONFIG
    
    # Get actual column names from writer
    writer_cols = [col.name for col in LINKED_SERVER_COLUMNS]
    
    # Get config from annotation_sync
    config = SHEET_ANNOTATION_CONFIG['Linked Servers']
    
    # Verify key columns exist in writer  
    for key_col in config['key_cols']:
        assert key_col in writer_cols, f"Key col '{key_col}' not in writer"
    
    # Verify editable columns exist in writer
    for edit_col in config['editable_cols'].keys():
        assert edit_col in writer_cols, f"Edit col '{edit_col}' not in writer"
```

---

*This document is the authoritative reference for E2E test implementation.*
