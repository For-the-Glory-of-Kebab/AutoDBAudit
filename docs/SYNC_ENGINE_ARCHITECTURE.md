# Sync Engine Architecture & State Machine Specification

> **Version**: 1.0 | **Date**: 2025-12-18  
> **Status**: APPROVED FOR IMPLEMENTATION  
> **Purpose**: Complete technical specification for sync engine refactor

---

## Table of Contents
1. [Problem Statement](#1-problem-statement)
2. [Architecture Overview](#2-architecture-overview)
3. [State Machine](#3-state-machine)
4. [Entity Mutation Catalog](#4-entity-mutation-catalog)
5. [Action Log System](#5-action-log-system)
6. [Stats Service](#6-stats-service)
7. [Excel↔DB Sync Protocol](#7-exceldb-sync-protocol)
8. [Edge Cases & Robustness](#8-edge-cases--robustness)
9. [Implementation Plan](#9-implementation-plan)

---

## 1. Problem Statement

### Current Issues
| Issue | Impact |
|-------|--------|
| 650-line monolithic `sync()` method | Untestable, fragile |
| Nested functions hide dependencies | Can't unit test |
| No single source of truth for state transitions | Inconsistent behavior |
| Duplicate counting logic across files | Stats mismatch |
| Exceptions lost between syncs | Data loss |
| CLI stats wrong | User confusion |

### Success Criteria
- [ ] All state transitions defined in ONE place
- [ ] Stats from ONE function (CLI, Excel, --finalize)
- [ ] Action log: no duplicates, no data loss
- [ ] Multi-sync stability: Sync 1→2→3 = consistent
- [ ] Exception persistence: survives multiple syncs

---

## 2. Architecture Overview

### Module Structure
```
src/autodbaudit/
├── domain/
│   ├── models.py           # (existing)
│   ├── change_types.py     # [NEW] Enums: ChangeType, RiskLevel
│   └── state_machine.py    # [NEW] THE state transition authority
├── application/
│   ├── stats_service.py    # [NEW] Single source for all stats
│   ├── diff/               # [NEW] Finding & entity comparison
│   │   ├── __init__.py
│   │   ├── findings_diff.py
│   │   └── entity_diff.py  # (refactored)
│   ├── actions/            # [NEW] Action detection & recording
│   │   ├── __init__.py
│   │   ├── action_detector.py
│   │   └── action_recorder.py
│   ├── sync_service.py     # [REWRITE] Thin orchestrator
│   └── annotation_sync.py  # [REFACTOR] Cleanup
```

### Data Flow
```
┌─────────────────────────────────────────────────────────────────────┐
│                         --sync COMMAND                               │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
         ┌──────────────────┐      ┌──────────────────┐
         │ Read Annotations │      │   Run Re-Audit   │
         │   from Excel     │      │  (current state) │
         └────────┬─────────┘      └────────┬─────────┘
                  │                         │
                  ▼                         ▼
         ┌──────────────────┐      ┌──────────────────┐
         │ Detect Exception │      │   Diff Findings  │
         │    Changes       │      │  (baseline/prev) │
         └────────┬─────────┘      └────────┬─────────┘
                  │                         │
                  └──────────┬──────────────┘
                             ▼
                  ┌──────────────────┐
                  │ ACTION DETECTOR  │
                  │ (consolidate)    │
                  └────────┬─────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │ Action     │  │  Stats     │  │ Excel      │
    │ Recorder   │  │  Service   │  │ Writer     │
    │ (DB)       │  │  (compute) │  │ (output)   │
    └────────────┘  └────────────┘  └────────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │   CLI OUTPUT     │
                  └──────────────────┘
```

---

## 3. State Machine

### 3.1 Finding States
```python
class FindingStatus(Enum):
    PASS = "PASS"      # Compliant
    FAIL = "FAIL"      # Non-compliant (security issue)
    WARN = "WARN"      # Attention needed
```

### 3.2 Exception States
```python
class ExceptionState(Enum):
    NONE = "none"          # No exception
    DOCUMENTED = "documented"  # Has justification
    CLEARED = "cleared"    # Was exception, now cleared
```

### 3.3 Complete State Combination Matrix

Every finding row exists in one of these states:

| # | DB Status | Has Justification | Review Status | Effective State | Counted As |
|---|-----------|-------------------|---------------|-----------------|------------|
| 1 | PASS | No | - | Compliant | ✅ OK |
| 2 | PASS | Yes | - | Compliant+Note | ✅ OK (note saved) |
| 3 | PASS | - | Exception | **Invalid** | Clear dropdown |
| 4 | FAIL | No | - | Active Issue | ❌ Issue |
| 5 | FAIL | Yes | - | **Documented Exception** | ✓ Exception |
| 6 | FAIL | No | Exception | **Documented Exception** | ✓ Exception |
| 7 | FAIL | Yes | Exception | **Documented Exception** | ✓ Exception |
| 8 | WARN | No | - | Active Warning | ⚠️ Warning |
| 9 | WARN | Yes | - | **Documented Exception** | ✓ Exception |
| 10 | WARN | No | Exception | **Documented Exception** | ✓ Exception |

### 3.4 State Transitions (All Possible)

```
Previous State      → Current State      = Transition          → Action
─────────────────────────────────────────────────────────────────────────
FAIL                → PASS               = FIXED               → Log "Fixed"
WARN                → PASS               = FIXED               → Log "Fixed"
PASS                → FAIL               = REGRESSION          → Log "Regression"
PASS                → WARN               = REGRESSION          → Log "Regression"
(none)              → FAIL               = NEW_ISSUE           → Log "New Issue"
(none)              → WARN               = NEW_ISSUE           → Log "New Issue"
FAIL                → FAIL               = STILL_FAILING       → No log (unless exception change)
FAIL+Exception      → PASS               = FIXED               → Log "Fixed", clear exception
FAIL+Exception      → FAIL (no just.)    = EXCEPTION_REMOVED   → Log "Exception Removed"
FAIL                → FAIL+Justification = EXCEPTION_ADDED     → Log "Exception Documented"
PASS+Note           → FAIL               = REGRESSION          → Log "Regression" (note→exception!)
FIXED               → FAIL               = RE_REGRESSION       → Log "Regression"
```

### 3.5 Priority Rules (Concurrent Events)

When multiple things happen in ONE sync:

```python
PRIORITY = [
    "FIXED",           # 1st - Fix always wins
    "REGRESSION",      # 2nd
    "EXCEPTION_ADDED", # 3rd (only if not fixed)
    "EXCEPTION_REMOVED", # 4th
    "STILL_FAILING",   # Last (no log)
]
```

**Critical Rule**: If FIXED + EXCEPTION_ADDED both apply → **FIXED wins**, exception cleared.

### 3.6 State Machine Function

```python
def classify_transition(
    old_status: FindingStatus | None,
    new_status: FindingStatus | None,
    old_has_exception: bool,
    new_has_exception: bool,
    instance_was_scanned: bool,
) -> TransitionResult:
    """
    THE authoritative function for classifying state transitions.
    
    Returns:
        TransitionResult with change_type, should_log, counted_as
    """
    # If instance wasn't scanned, we know nothing - no transition
    if not instance_was_scanned and old_status is not None:
        return TransitionResult(ChangeType.UNKNOWN, should_log=False)
    
    # Row didn't exist before
    if old_status is None:
        if new_status in (FindingStatus.FAIL, FindingStatus.WARN):
            return TransitionResult(ChangeType.NEW_ISSUE, should_log=True)
        return TransitionResult(ChangeType.NO_CHANGE, should_log=False)
    
    # Row no longer exists (or PASS)
    if new_status is None or new_status == FindingStatus.PASS:
        if old_status in (FindingStatus.FAIL, FindingStatus.WARN):
            return TransitionResult(ChangeType.FIXED, should_log=True)
        return TransitionResult(ChangeType.NO_CHANGE, should_log=False)
    
    # PASS → FAIL/WARN
    if old_status == FindingStatus.PASS:
        return TransitionResult(ChangeType.REGRESSION, should_log=True)
    
    # FAIL/WARN → FAIL/WARN (still failing)
    # Check for exception changes
    if not old_has_exception and new_has_exception:
        return TransitionResult(ChangeType.EXCEPTION_ADDED, should_log=True)
    if old_has_exception and not new_has_exception:
        return TransitionResult(ChangeType.EXCEPTION_REMOVED, should_log=True)
    
    return TransitionResult(ChangeType.STILL_FAILING, should_log=False)
```

---

## 4. Entity Mutation Catalog

### 4.1 Mutation Categories

| Category | Description |
|----------|-------------|
| `ADD` | Entity created/appeared |
| `REMOVE` | Entity deleted/disappeared |
| `MODIFY` | Property changed |
| `ENABLE` | Enabled (was disabled) |
| `DISABLE` | Disabled (was enabled) |
| `COMPLY` | Became compliant |
| `VIOLATE` | Became non-compliant |

### 4.2 Complete Entity Mutation Table

| Entity Type | Mutation | DB Field | Logged? |
|-------------|----------|----------|---------|
| **SA Account** | Renamed | name | ✅ |
| | Disabled | is_disabled | ✅ |
| | Enabled | is_disabled | ✅ Critical |
| | Default DB Changed | default_database | ⚠️ Info |
| **Login** | Added | - | ✅ |
| | Removed | - | ✅ |
| | Renamed | name | ✅ |
| | Disabled | is_disabled | ✅ |
| | Enabled | is_disabled | ✅ |
| | Password Policy Off | is_policy_checked | ✅ Critical |
| | Password Policy On | is_policy_checked | ✅ Fix |
| | Password Expiration Off | is_expiration_checked | ✅ |
| | Password Expiration On | is_expiration_checked | ✅ |
| | Default DB Changed | default_database | ⚠️ Info |
| **Role Membership** | Added | - | ✅ (Critical if sysadmin) |
| | Removed | - | ✅ |
| **Config Setting** | Value Changed | config_value | ✅ |
| | Compliant | status | ✅ Fix |
| | Non-Compliant | status | ✅ Regression |
| **Service** | Started | status | ✅ |
| | Stopped | status | ✅ |
| | Startup Changed | startup_type | ✅ |
| | Account Changed | service_account | ✅ |
| **Database** | Created | - | ✅ |
| | Dropped | - | ✅ |
| | Trustworthy On | is_trustworthy | ✅ Critical |
| | Trustworthy Off | is_trustworthy | ✅ Fix |
| | Owner Changed | owner | ⚠️ Info |
| | Recovery Changed | recovery_model | ⚠️ Info |
| **DB User** | Added | - | ✅ |
| | Removed | - | ✅ |
| | Orphaned | has_login | ✅ Critical |
| | Mapped | has_login | ✅ Fix |
| | Guest Enabled | - | ✅ Critical |
| | Guest Disabled | - | ✅ Fix |
| **DB Role Member** | Added | - | ✅ (Critical if db_owner) |
| | Removed | - | ✅ |
| **Linked Server** | Added | - | ✅ |
| | Removed | - | ✅ |
| | Credential Changed | remote_login | ✅ |
| | Using sa | remote_login | ✅ Critical |
| **Trigger** | Created | - | ✅ |
| | Dropped | - | ✅ |
| | Enabled | is_disabled | ✅ |
| | Disabled | is_disabled | ✅ |
| **Backup** | Missing | last_backup | ✅ Critical |
| | Restored | last_backup | ✅ Fix |
| | Stale | days_since | ⚠️ Warning |
| **Protocol** | Enabled | enabled | ✅ |
| | Disabled | enabled | ✅ |
| **Encryption** | Key Created | - | ⚠️ Info |
| | Key Backed Up | backup_date | ✅ |
| | TDE Enabled | is_encrypted | ✅ |
| | TDE Disabled | is_encrypted | ✅ |
| **Instance** | Version Updated | version | ⚠️ Info |
| | Product Level | product_level | ⚠️ Info |

---

## 5. Action Log System

### 5.1 Core Principles

1. **Append-Only**: Never delete rows
2. **No Duplicates**: (entity_key, change_type, sync_run_id) = unique
3. **User Editable**: Date and Notes can be modified
4. **Persistence**: User edits survive syncs

### 5.2 Schema

```sql
CREATE TABLE action_log (
    id INTEGER PRIMARY KEY,
    initial_run_id INTEGER NOT NULL,
    sync_run_id INTEGER,
    entity_key TEXT NOT NULL,
    action_type TEXT NOT NULL,      -- Fixed, Regression, Exception, etc.
    status TEXT NOT NULL,           -- open, closed, exception
    action_date TEXT NOT NULL,      -- ISO format, when first detected
    user_date_override TEXT,        -- User's manual date (if different)
    description TEXT,
    finding_type TEXT,              -- Category: Login, Config, etc.
    notes TEXT,                     -- User commentary
    UNIQUE(initial_run_id, entity_key, action_type, sync_run_id)
);
```

### 5.3 Deduplication Logic

```python
def should_log_action(
    entity_key: str,
    change_type: ChangeType,
    sync_run_id: int,
    existing_actions: list[Action]
) -> bool:
    """Check if this action should be logged."""
    
    # Check for exact duplicate in THIS sync
    for action in existing_actions:
        if (action.entity_key == entity_key and
            action.action_type == change_type.value and
            action.sync_run_id == sync_run_id):
            return False  # Already logged this sync
    
    return True
```

### 5.4 Date Handling

```python
def get_display_date(action: Action) -> datetime:
    """Get the date to display (user override takes precedence)."""
    if action.user_date_override:
        return parse_date(action.user_date_override)
    return parse_date(action.action_date)

def update_action_from_excel(action_id: int, user_date: str, notes: str):
    """Persist user's Excel edits back to DB."""
    UPDATE action_log 
    SET user_date_override = ?, notes = ?
    WHERE id = ?
```

---

## 6. Stats Service

### 6.1 Single Source of Truth

```python
class StatsService:
    """
    THE authoritative source for all statistics.
    
    All consumers (CLI, Excel Cover, --finalize) use this.
    """
    
    def __init__(self, store: HistoryStore):
        self.store = store
    
    def calculate(
        self,
        baseline_run_id: int,
        current_run_id: int,
        previous_run_id: int | None = None,
    ) -> SyncStats:
        """Calculate all stats from one place."""
        
        baseline_findings = self.store.get_findings(baseline_run_id)
        current_findings = self.store.get_findings(current_run_id)
        annotations = self.store.get_all_annotations()
        
        # Current state counts
        active_issues = self._count_active(current_findings, annotations)
        exceptions = self._count_exceptions(current_findings, annotations)
        compliant = self._count_compliant(current_findings)
        
        # Changes from baseline
        baseline_diff = self._diff(baseline_findings, current_findings, annotations)
        
        # Changes from previous sync (if exists)
        if previous_run_id:
            prev_findings = self.store.get_findings(previous_run_id)
            recent_diff = self._diff(prev_findings, current_findings, annotations)
        else:
            recent_diff = baseline_diff
        
        return SyncStats(
            total_findings=len(current_findings),
            active_issues=active_issues,
            documented_exceptions=exceptions,
            compliant_items=compliant,
            fixed_since_baseline=baseline_diff.fixed,
            regressions_since_baseline=baseline_diff.regressions,
            new_issues_since_baseline=baseline_diff.new_issues,
            fixed_since_last=recent_diff.fixed,
            regressions_since_last=recent_diff.regressions,
            new_issues_since_last=recent_diff.new_issues,
        )
```

### 6.2 Counting Rules

```python
def _count_active(self, findings, annotations) -> int:
    """Count active issues (FAIL/WARN without exception)."""
    count = 0
    for f in findings:
        if f['status'] in ('FAIL', 'WARN'):
            key = f['entity_key']
            if not self._is_exceptioned(key, annotations):
                count += 1
    return count

def _is_exceptioned(self, key: str, annotations: dict) -> bool:
    """Check if a key has valid exception."""
    if key not in annotations:
        return False
    ann = annotations[key]
    has_justification = bool(ann.get('justification'))
    has_status = ann.get('review_status') == 'Exception'
    return has_justification or has_status
```

---

## 7. Excel↔DB Sync Protocol

### 7.1 Unique Keys per Sheet

| Sheet | Key Formula | Collision Risk |
|-------|-------------|----------------|
| Instances | `{Server}\|{Instance}` | Low |
| SA Account | `{Server}\|{Instance}\|{CurrentName}` | Low |
| Server Logins | `{Server}\|{Instance}\|{LoginName}` | Low |
| Sensitive Roles | `{Server}\|{Instance}\|{Role}\|{Member}` | Low |
| Configuration | `{Server}\|{Instance}\|{Setting}` | Low |
| Services | `{Server}\|{Instance}\|{ServiceName}` | Low |
| Databases | `{Server}\|{Instance}\|{Database}` | Low |
| Database Users | `{Server}\|{Instance}\|{Database}\|{UserName}` | Low |
| Database Roles | `{Server}\|{Instance}\|{Database}\|{Role}\|{Member}` | Low |
| Orphaned Users | `{Server}\|{Instance}\|{Database}\|{UserName}` | Low |
| Linked Servers | `{Server}\|{Instance}\|{LinkedServerName}` | Low |
| Triggers | `{Server}\|{Instance}\|{Scope}\|{TriggerName}` | Low |
| Backups | `{Server}\|{Instance}\|{Database}\|{RecoveryModel}` | Medium* |
| Client Protocols | `{Server}\|{Instance}\|{Protocol}` | Low |
| Encryption | `{Server}\|{Instance}\|{Type}\|{Name}` | Low |
| Audit Settings | `{Server}\|{Instance}\|{Setting}` | Low |
| **Actions** | `{ID}` (DB-generated integer) | None |

*Backups key includes RecoveryModel because same DB with different models = different backup requirements.

### 7.2 Read Protocol

```python
def read_from_excel(sheet, config):
    """Read annotations from Excel sheet."""
    
    header_row = find_header_row(sheet)
    key_cols = [find_column(header_row, k) for k in config['key_cols']]
    edit_cols = {name: find_column(header_row, name) for name in config['editable_cols']}
    
    # Track merged cell values
    last_key_values = {}
    
    for row in sheet.iter_rows(min_row=header_row + 1):
        # Build key (handle merged cells)
        key_parts = []
        for i, col_idx in enumerate(key_cols):
            cell = row[col_idx]
            value = get_cell_value(cell)
            if value is None and is_merged(cell):
                value = last_key_values.get(i, '')
            else:
                last_key_values[i] = value
            key_parts.append(str(value or ''))
        
        entity_key = '|'.join(key_parts)
        
        # Read editable values
        values = {}
        for name, col_idx in edit_cols.items():
            values[config['editable_cols'][name]] = get_cell_value(row[col_idx])
        
        yield entity_key, values
```

### 7.3 Write Protocol

```python
def write_to_excel(sheet, config, annotations):
    """Write annotations back to Excel sheet."""
    
    header_row = find_header_row(sheet)
    key_cols = [find_column(header_row, k) for k in config['key_cols']]
    edit_cols = get_editable_column_indices(header_row, config)
    
    last_key_values = {}
    
    for row in sheet.iter_rows(min_row=header_row + 1):
        # Build key (same merge handling)
        entity_key = build_key(row, key_cols, last_key_values)
        
        if entity_key in annotations:
            ann = annotations[entity_key]
            for excel_name, db_field in config['editable_cols'].items():
                if db_field in ann and ann[db_field] is not None:
                    col_idx = edit_cols[excel_name]
                    row[col_idx].value = ann[db_field]
```

### 7.4 Error Handling

| Scenario | Action |
|----------|--------|
| Key not found in Excel | Log warning, skip |
| Key not found in DB | Create new annotation |
| Parse error (date) | Use original value, log warning |
| Merged cell empty | Use last tracked value |
| File locked | Abort gracefully, no partial write |
| Invalid Review Status | Default to "Needs Review" |

---

## 8. Edge Cases & Robustness

### 8.1 Instance Unavailable

**Scenario**: Instance was in baseline but can't connect now.

**Risk**: All its findings disappear → falsely marked as "Fixed"

**Solution**:
```python
def is_valid_for_fixed_check(entity_key: str, scanned_instances: set[str]) -> bool:
    """Only mark as Fixed if we actually scanned the instance."""
    server_instance = extract_server_instance(entity_key)
    return server_instance in scanned_instances
```

### 8.2 Concurrent Exception + Fix

**Scenario**: User adds justification, but SQL issue was also fixed.

**Rule**: Fix wins, exception is not recorded.

```python
if transition.change_type == ChangeType.FIXED:
    # Clear any pending exception
    clear_exception(entity_key)
    return log_action("Fixed", ...)
```

### 8.3 Note on PASS Row → Becomes FAIL

**Scenario**: PASS row had a note. Now it's FAIL.

**Result**: Note immediately becomes exception (no extra action needed).

```python
# The existing note qualifies as exception documentation
# Just log: "Regression (pre-documented)"
```

### 8.4 Multi-Sync Duplication Prevention

**Scenario**: Same exception detected in Sync 2, 3, 4...

**Solution**: Check (entity_key, change_type) in action_log before inserting.

```python
def record_action(entity_key, change_type, sync_run_id):
    existing = find_action(entity_key, change_type) 
    if existing and existing.sync_run_id != sync_run_id:
        # Different sync - still don't re-log same event type
        # Unless it's a NEW occurrence (regressed again, etc.)
        if not is_new_occurrence(existing, current_state):
            return  # Skip duplicate
```

### 8.5 Exception Edit (Not New Exception)

**Scenario**: User modifies justification text.

**Action**: Log "Exception Updated" (optional), but do NOT increment exception count.

```python
if old_justification != new_justification and new_justification:
    if old_justification:  # Already had one
        action_type = "Exception Updated"  # Info only
        increment_exception_count = False
    else:
        action_type = "Exception Documented"
        increment_exception_count = True
```

### 8.6 Row Reordering in Excel

**Scenario**: User sorts Actions sheet by date.

**Impact**: Row positions change, merged cells might break.

**Solution**: 
- Actions sheet uses DB ID for matching (not row position)
- Read ALL rows, match by ID column
- Handle None/empty ID gracefully (skip orphan rows)

### 8.7 Excel File Recovery

**Scenario**: Excel file corrupted/deleted.

**Recovery**: Regenerate from SQLite (source of truth).

```bash
python main.py --regenerate-excel
```

---

## 9. Implementation Plan

### Phase 1: Domain Layer (2 hrs)
```
src/autodbaudit/domain/
├── change_types.py    # Enums
└── state_machine.py   # Transition logic

Tests:
tests/test_state_machine.py
```

### Phase 2: Stats Service (2 hrs)
```
src/autodbaudit/application/
└── stats_service.py   # Single source of truth

Tests:
tests/test_stats_service.py
```

### Phase 3: Diff Module (3 hrs)
```
src/autodbaudit/application/diff/
├── __init__.py
├── findings_diff.py   # Pure diff function
└── entity_diff.py     # Refactored

Tests:
tests/test_findings_diff.py
```

### Phase 4: Action System (2 hrs)
```
src/autodbaudit/application/actions/
├── __init__.py
├── action_detector.py
└── action_recorder.py

Tests:
tests/test_action_recorder.py
```

### Phase 5: Excel Sync (2 hrs)
- Review all sheet key uniqueness
- Add robust error handling
- Test merged cell handling

### Phase 6: Sync Orchestrator (3 hrs)
- Rewrite sync_service.py (~100 lines)
- Wire all modules
- CLI output formatting

### Phase 7: E2E Testing (2 hrs)
- Use run_simulation.py
- Multi-sync stability
- All edge cases from Section 8

---

## Appendix: Test Scenarios

### A. Basic Flows
- [ ] Fresh audit → All FAIL show ⏳
- [ ] Add justification → ✓ Exception, logged
- [ ] Fix in SQL → Logged as Fixed
- [ ] PASS + justification → Note saved

### B. Multi-Sync Stability
- [ ] Sync×3 no changes → Counts stable
- [ ] Exception in Sync 2 → Not re-logged Sync 3
- [ ] Action log not duplicating

### C. Edge Cases
- [ ] Instance unavailable → Not falsely Fixed
- [ ] Exception + Fix → Fix wins
- [ ] Note on PASS → Becomes exception when FAIL
- [ ] Regression of fixed item
- [ ] Exception update ≠ new exception count
- [ ] Row reordering doesn't break

---

*Document Complete - Ready for Implementation*
