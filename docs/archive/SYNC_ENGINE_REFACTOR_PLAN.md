# Sync Engine Modular Refactor - Implementation Plan

> **Goal**: Extract sync/diff/exception/action-logging logic into small, testable, maintainable modules with well-defined interfaces.

---

## Problem Statement

The current sync engine has critical architectural issues:

| Issue | Impact |
|-------|--------|
| **650-line monolithic `sync()` method** | Impossible to test individual pieces; changes break unrelated functionality |
| **Nested functions** (`calc_diff`, `is_exceptioned`) | Hidden dependencies, can't unit test |
| **3 massive files** all interacting | `sync_service.py` (719), `annotation_sync.py` (932), `entity_diff.py` (949) |
| **No single source of truth** for state transitions | Each file has its own interpretation of "Fixed", "Regression", "Exception" |
| **Minimal test coverage** | Only 2 test files with basic coverage |

### Current Symptoms
- Subsequent `--sync` calls lose exceptions
- Exception counts don't match manual count
- CLI stats are totally wrong
- Regressions/new findings not properly logged to Actions sheet
- Adding justification to non-discrepant rows behaves inconsistently

---

## User Review Required

> [!IMPORTANT]
> **Breaking Change**: This refactor will restructure the `application/` directory significantly. The public API (`SyncService.sync()`) will remain compatible, but internal function signatures will change.

> [!IMPORTANT]
> **Testing Strategy**: I need your input on manual verification steps. What's the best way for you to validate the sync logic after refactor? Do you have test databases or mock scenarios?

---

## Proposed Architecture

### New Directory Structure

```
src/autodbaudit/
├── domain/
│   ├── models.py           # (existing)
│   ├── state_machine.py    # [NEW] Single source of truth for transitions
│   ├── change_types.py     # [NEW] Enums: ChangeType, RiskLevel, EntityStatus
│   └── entity_types.py     # [NEW] EntityType enum + key builders
├── application/
│   ├── sync_service.py     # [REWRITE] Thin orchestrator (~100 lines)
│   ├── diff/               # [NEW] All diffing logic
│   │   ├── __init__.py
│   │   ├── findings_diff.py     # Pure func: compare findings lists
│   │   ├── entity_diff.py       # [MOVE] Refactored from existing
│   │   └── diff_coordinator.py  # Orchestrates all diffs
│   ├── actions/            # [NEW] Action detection & recording
│   │   ├── __init__.py
│   │   ├── action_detector.py   # Detects what actions occurred
│   │   ├── action_recorder.py   # Persists to DB
│   │   └── action_presenter.py  # Formats for Excel/CLI
│   └── exceptions/         # [NEW] Exception handling
│       ├── __init__.py
│       ├── exception_detector.py    # Detects new/changed
│       ├── exception_validator.py   # Is this row eligible?
│       └── exception_counter.py     # Stats calculation
```

### Core Design: State Machine

The **single source of truth** for all state transitions:

```python
# domain/state_machine.py

class FindingStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"

class ChangeType(Enum):
    FIXED = "Fixed"           # FAIL/WARN → PASS
    REGRESSION = "Regression" # PASS → FAIL/WARN
    NEW_ISSUE = "New"         # (not in baseline) → FAIL/WARN
    STILL_FAILING = "StillFailing"  # FAIL/WARN → FAIL/WARN
    EXCEPTION_ADDED = "ExceptionAdded"
    EXCEPTION_REMOVED = "ExceptionRemoved"
    NO_CHANGE = "NoChange"

@dataclass
class TransitionResult:
    change_type: ChangeType
    is_actionable: bool       # Should this go to Actions sheet?
    is_counted_as_issue: bool # Should this count toward "issues remaining"?
    risk_level: str

def classify_finding_change(
    old_status: FindingStatus | None,
    new_status: FindingStatus | None,
    has_exception: bool,
    instance_was_scanned: bool,
) -> TransitionResult:
    """
    THE authoritative function for classifying any finding change.
    """
    # All transition logic lives HERE ONLY
```

---

## Proposed Changes

### Domain Layer

#### [NEW] [state_machine.py](file:///f:/Raja-Initiative/src/autodbaudit/domain/state_machine.py)

- `FindingStatus` enum (PASS, FAIL, WARN)
- `ChangeType` enum (Fixed, Regression, New, StillFailing, etc.)
- `TransitionResult` dataclass
- `classify_finding_change()` - THE authoritative transition function
- `should_count_as_active_issue()` - Is this item an "open issue"?
- `should_action_be_logged()` - Does this transition warrant an action log entry?

#### [NEW] [change_types.py](file:///f:/Raja-Initiative/src/autodbaudit/domain/change_types.py)

- `RiskLevel` enum (Critical, High, Medium, Low, Info)
- `ActionStatus` enum (Open, Closed, Exception, Pending)

---

### Application Layer - Diff Module

#### [NEW] [diff/findings_diff.py](file:///f:/Raja-Initiative/src/autodbaudit/application/diff/findings_diff.py)

Pure functions for comparing findings:

```python
@dataclass
class FindingsDiffResult:
    fixed: list[str]           # Entity keys that were fixed
    regressions: list[str]     # Entity keys that regressed
    new_issues: list[str]      # Entity keys that are new failures
    still_failing: list[str]   # Entity keys still failing
    unchanged: list[str]       # Entity keys with no change

def diff_findings(
    old_findings: list[dict],
    new_findings: list[dict],
    valid_instance_keys: set[str],
    exception_keys: set[str],
    state_machine: StateMachine,
) -> FindingsDiffResult:
    """Compare two findings lists using the state machine."""
```

#### [MOVE/REFACTOR] [diff/entity_diff.py](file:///f:/Raja-Initiative/src/autodbaudit/application/diff/entity_diff.py)

Move existing `entity_diff.py` here, refactored to:
- Use the new `ChangeType` enum
- Return structured `EntityChange` objects that use state machine
- Smaller per-entity functions

---

### Application Layer - Actions Module

#### [NEW] [actions/action_detector.py](file:///f:/Raja-Initiative/src/autodbaudit/application/actions/action_detector.py)

Detects what actions occurred in a sync:

```python
@dataclass
class DetectedAction:
    entity_key: str
    change_type: ChangeType
    description: str
    risk_level: RiskLevel
    action_date: datetime
    server: str
    instance: str

def detect_actions(
    findings_diff: FindingsDiffResult,
    exception_changes: list[ExceptionChange],
    entity_changes: list[EntityChange],
) -> list[DetectedAction]:
    """Consolidate all detected actions from various sources."""
```

#### [NEW] [actions/action_recorder.py](file:///f:/Raja-Initiative/src/autodbaudit/application/actions/action_recorder.py)

Persists actions to database:

```python
def record_actions(
    store: HistoryStore,
    actions: list[DetectedAction],
    initial_run_id: int,
    sync_run_id: int,
) -> int:  # Returns count of actions recorded
```

#### [NEW] [actions/action_presenter.py](file:///f:/Raja-Initiative/src/autodbaudit/application/actions/action_presenter.py)

Formats actions for display:

```python
def format_for_excel(actions: list[DetectedAction]) -> list[dict]:
    """Format actions for Excel Actions sheet."""

def format_for_cli(actions: list[DetectedAction]) -> str:
    """Format actions for CLI output."""

def calculate_stats(actions: list[DetectedAction]) -> dict:
    """Calculate summary statistics for CLI display."""
```

---

### Application Layer - Exceptions Module

#### [NEW] [exceptions/exception_detector.py](file:///f:/Raja-Initiative/src/autodbaudit/application/exceptions/exception_detector.py)

```python
@dataclass
class ExceptionChange:
    entity_key: str
    change_type: Literal["added", "updated", "removed"]
    justification: str | None
    old_justification: str | None
    entity_status: FindingStatus

def detect_exception_changes(
    old_annotations: dict,
    new_annotations: dict,
    current_findings: list[dict],
) -> list[ExceptionChange]:
    """Detect new/changed/removed exceptions."""
```

#### [NEW] [exceptions/exception_validator.py](file:///f:/Raja-Initiative/src/autodbaudit/application/exceptions/exception_validator.py)

```python
def is_exception_eligible(
    entity_key: str,
    annotations: dict,
    findings: list[dict],
) -> bool:
    """
    Determine if an entity can have an exception.
    
    Rules:
    - Must be FAIL or WARN status (not PASS)
    - Must have justification OR review_status == "Exception"
    """

def validate_exception(
    entity_key: str,
    justification: str,
    status: FindingStatus,
) -> tuple[bool, str]:  # (is_valid, error_message)
```

#### [NEW] [exceptions/exception_counter.py](file:///f:/Raja-Initiative/src/autodbaudit/application/exceptions/exception_counter.py)

```python
def count_active_exceptions(
    annotations: dict,
    findings: list[dict],
) -> int:
    """Count total documented exceptions (discrepant + justified)."""

def count_active_issues(
    findings: list[dict],
    exception_keys: set[str],
) -> int:
    """Count issues remaining (FAIL/WARN minus exceptions)."""
```

---

### Application Layer - Sync Service Rewrite

#### [REWRITE] [sync_service.py](file:///f:/Raja-Initiative/src/autodbaudit/application/sync_service.py)

Simplified to ~100 lines as pure orchestrator:

```python
class SyncService:
    def sync(self, ...) -> dict:
        # Phase 1: Pre-flight checks
        initial_run_id = self._validate_baseline()
        
        # Phase 2: Read annotations from Excel
        old_annotations, new_annotations = self._sync_annotations(excel_path)
        
        # Phase 3: Detect exception changes
        exception_changes = exception_detector.detect_exception_changes(...)
        
        # Phase 4: Run re-audit
        current_run_id = self._run_reaudit(...)
        
        # Phase 5: Diff findings
        findings_diff = findings_diff.diff_findings(...)
        
        # Phase 6: Diff entities
        entity_changes = entity_diff.detect_all_changes(...)
        
        # Phase 7: Consolidate & record actions
        all_actions = action_detector.detect_actions(...)
        action_recorder.record_actions(...)
        
        # Phase 8: Calculate stats
        stats = action_presenter.calculate_stats(...)
        
        # Phase 9: Write Excel with annotations
        self._write_report(...)
        
        return stats
```

---

## Verification Plan

### Automated Tests

#### Unit Tests (New)

| Test File | What It Tests | Command |
|-----------|--------------|---------|
| `tests/test_state_machine.py` | All state transitions | `python -m pytest tests/test_state_machine.py -v` |
| `tests/test_findings_diff.py` | Findings comparison | `python -m pytest tests/test_findings_diff.py -v` |
| `tests/test_exception_validator.py` | Exception eligibility | `python -m pytest tests/test_exception_validator.py -v` |
| `tests/test_action_detector.py` | Action detection | `python -m pytest tests/test_action_detector.py -v` |

#### Integration Tests (Existing + Enhanced)

| Test File | What It Tests | Command |
|-----------|--------------|---------|
| `tests/test_sync_logic.py` | E2E sync workflow | `python -m pytest tests/test_sync_logic.py -v` |
| `test_sync_logic_root.py` | Additional sync scenarios | `python test_sync_logic_root.py` |

### Manual Verification

> [!IMPORTANT]  
> I need your input on manual verification. Specifically:
> 1. Do you have a test SQL Server instance I can use?
> 2. What's the best way to create known states for testing?
> 3. Can you provide sample Excel files with exceptions?

#### Proposed Manual Test Sequence

1. **Fresh Audit**: Run `python main.py --audit` on test instance
2. **Add Exception**: Edit Excel, add justification to a FAIL row
3. **First Sync**: Run `python main.py --sync` - verify:
   - CLI shows correct "1 exception added"
   - Actions sheet has "Exception Documented" entry
   - Row shows ✓ indicator
4. **Second Sync**: Run `python main.py --sync` again - verify:
   - Exception is NOT re-detected
   - Counts remain stable
5. **Fix Item**: Actually fix something in SQL Server
6. **Third Sync**: Verify "Fixed" appears in Actions sheet

---

## Implementation Order

| Phase | Est. Time | Dependencies |
|-------|-----------|--------------|
| 1. Domain types & state machine | 2 hours | None |
| 2. Diff module extraction | 3 hours | Phase 1 |
| 3. Actions module | 2 hours | Phase 1, 2 |
| 4. Exceptions module | 2 hours | Phase 1 |
| 5. Sync service rewrite | 3 hours | Phase 2, 3, 4 |
| 6. Test suite | 2 hours | Phase 5 |
| 7. Documentation | 1 hour | Phase 5 |

**Total Estimated: ~15 hours of implementation**

---

## Rollback Plan

If issues arise:
1. All changes are in new files initially (not modifying existing)
2. Old `sync_service.sync()` can be kept as `sync_legacy()` during transition
3. Git history preserves everything

---

*Document Version: 1.0 | Created: 2025-12-18*
