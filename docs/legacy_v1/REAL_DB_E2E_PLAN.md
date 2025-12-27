# Real-DB E2E Testing - FINAL ARCHITECTURE PLAN v3.0

## Document Status
- **Version**: 3.0 FINAL
- **Date**: 2025-12-26
- **Status**: ✅ IMPLEMENTATION COMPLETE

---

## Critical Issues Addressed

### 1. Pre-existing Discrepancies (King Login, etc.)

**Problem**: Test instances have existing discrepancies that will pollute our test assertions.

**Solution: Baseline Snapshot Strategy**

```
┌─────────────────────────────────────────────────────────────┐
│  PHASE 0: CAPTURE BASELINE                                  │
│                                                             │
│  1. Run audit on clean instances (existing discrepancies)   │
│  2. Save as "baseline_snapshot.json"                        │
│  3. Record: {sheet: [entities], counts}                     │
│                                                             │
│  This becomes our "known state" - we only assert DELTAS     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1: APPLY TEST DISCREPANCIES                          │
│                                                             │
│  1. Run atomic fixture (e.g., sa_enable.sql)                │
│  2. Record what we added to "test_additions.json"           │
│                                                             │
│  We now know exactly what we added vs baseline              │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 2: AUDIT + VERIFY DELTAS                             │
│                                                             │
│  1. Run audit                                               │
│  2. Compare to baseline                                     │
│  3. Assert: NEW findings == test_additions                  │
│                                                             │
│  This ignores King login and other pre-existing stuff       │
└─────────────────────────────────────────────────────────────┘
```

**Implementation**:

```python
# tests/real_db/contexts/baseline_manager.py

class BaselineManager:
    """Captures and diffs against pre-existing discrepancies."""
    
    def __init__(self, snapshot_path: Path):
        self.snapshot_path = snapshot_path
        self.baseline: dict = {}
        self.test_additions: list[str] = []
    
    def capture_baseline(self, excel_path: Path) -> None:
        """Run once at start: capture all existing findings."""
        wb = load_workbook(excel_path)
        for sheet in wb.sheetnames:
            if sheet in ["Cover", "Actions", "Action Log"]:
                continue
            ws = wb[sheet]
            self.baseline[sheet] = self._extract_entity_keys(ws)
        self._save()
    
    def record_test_addition(self, sheet: str, entity: str) -> None:
        """Record what we're adding via fixtures."""
        self.test_additions.append(f"{sheet}::{entity}")
    
    def get_delta(self, excel_path: Path) -> dict:
        """Compare current findings to baseline, return only NEW ones."""
        current = self._extract_all(excel_path)
        delta = {}
        for sheet, entities in current.items():
            baseline_entities = self.baseline.get(sheet, [])
            new_entities = [e for e in entities if e not in baseline_entities]
            if new_entities:
                delta[sheet] = new_entities
        return delta
    
    def assert_additions_found(self, excel_path: Path) -> bool:
        """Verify our test additions appear in delta."""
        delta = self.get_delta(excel_path)
        for addition in self.test_additions:
            sheet, entity = addition.split("::")
            if sheet not in delta or entity not in delta[sheet]:
                return False
        return True
```

**Protected Entities** (never touch):
- `King` login (sysadmin, used for test connection)
- System databases (master, msdb, tempdb, model)
- Any pre-existing linked servers

### 2. Randomized Sync Testing (Hypothesis Stateful)

**Problem**: Fixed test sequences miss edge cases in sync logic.

**Solution: Hypothesis RuleBasedStateMachine**

```python
# tests/real_db/L8_stateful/test_random_sync_sequences.py

from hypothesis import settings
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant

class AuditSyncStateMachine(RuleBasedStateMachine):
    """
    Generates random sequences of audit operations.
    Hypothesis explores action orderings we'd never think of.
    """
    
    def __init__(self):
        super().__init__()
        self.ctx = RealDBTestContext()
        self.expected_state = {}
        self.sync_count = 0
    
    @rule()
    def apply_random_discrepancy(self):
        """Apply a random fixture."""
        fixture = random.choice(ATOMIC_FIXTURES)
        self.ctx.apply_fixture(fixture)
        self.expected_state[fixture.entity] = "FAIL"
    
    @rule()
    def fix_random_discrepancy(self):
        """Revert a random active discrepancy."""
        if not self.expected_state:
            return
        entity = random.choice(list(self.expected_state.keys()))
        self.ctx.revert_fixture(entity)
        self.expected_state[entity] = "FIXED"
    
    @rule()
    def add_exception_to_random(self):
        """Add exception to random FAIL entity."""
        fails = [k for k, v in self.expected_state.items() if v == "FAIL"]
        if not fails:
            return
        entity = random.choice(fails)
        self.ctx.write_exception(entity, "Test justification")
        self.expected_state[entity] = "EXCEPTION"
    
    @rule()
    def run_sync(self):
        """Run sync and verify consistency."""
        self.ctx.run_sync()
        self.sync_count += 1
    
    @invariant()
    def stats_match_state(self):
        """After any action, stats must match expected state."""
        if self.sync_count == 0:
            return  # Haven't synced yet
        
        actual_stats = self.ctx.get_stats()
        expected_fails = sum(1 for v in self.expected_state.values() if v == "FAIL")
        expected_exceptions = sum(1 for v in self.expected_state.values() if v == "EXCEPTION")
        
        assert actual_stats["active_issues"] == expected_fails
        assert actual_stats["exceptions"] == expected_exceptions


# Run the state machine
TestAuditSync = AuditSyncStateMachine.TestCase
```

---

## Engineering Standards Reminder

| Rule | Application |
|------|-------------|
| Max 400 lines/file | Split test files by concern |
| Intuitive names | `test_state_fixed.py` not `test_1.py` |
| No prompts | Use `./scripts/run_pytest.ps1` |
| Well-defined interfaces | Clear API in `assertions/` |
| Docs in sync | Update TEST_ARCHITECTURE.md |

---

## FINAL Folder Structure

```
tests/
├── conftest.py                    # Root config
│
├── shared/                        # Cross-suite utilities
│   ├── __init__.py
│   ├── assertions/
│   │   ├── __init__.py
│   │   ├── excel.py               # Column alignment, dropdowns
│   │   ├── state.py               # State transitions
│   │   ├── stats.py               # Stats consistency
│   │   ├── action_log.py          # Log entries
│   │   ├── persian.py             # i18n/RTL
│   │   └── errors.py              # Error conditions
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── sheets.py              # Expected columns
│   │   ├── dropdowns.py           # Valid values
│   │   └── transitions.py         # State machine
│   └── helpers/
│       ├── __init__.py
│       ├── excel_io.py
│       ├── cli.py                 # CLIRunner class
│       └── wait.py
│
├── ultimate_e2e/                  # Mock tests (UNCHANGED)
├── layers/                        # L1-L6 (UNCHANGED)
│
└── real_db/                       # Real SQL Server tests
    ├── __init__.py
    ├── conftest.py                # RealDBTestContext, fixtures
    │
    ├── contexts/                  # Test infrastructure
    │   ├── __init__.py
    │   ├── real_db_context.py
    │   ├── sql_executor.py
    │   └── baseline_manager.py    # ★ Snapshot/diff strategy
    │
    ├── fixtures/
    │   ├── __init__.py
    │   ├── README.md
    │   ├── base/                  # Full sets
    │   │   ├── apply_2008.sql
    │   │   ├── apply_2019.sql
    │   │   ├── revert_2008.sql
    │   │   └── revert_2019.sql
    │   └── atomic/                # Single-purpose
    │       ├── sa_enable.sql
    │       ├── sa_disable.sql
    │       ├── login_weak_create.sql
    │       ├── login_weak_drop.sql
    │       ├── config_xpcmd_enable.sql
    │       ├── config_xpcmd_disable.sql
    │       └── ...
    │
    ├── L1_foundation/             # Basic checks
    ├── L2_annotation/             # Field persistence
    ├── L3_state/                  # State transitions
    ├── L4_action_log/             # Log entries
    ├── L5_cross_sheet/            # Multi-sheet
    ├── L6_cli/                    # Commands
    ├── L7_error/                  # Error conditions
    │
    └── L8_stateful/               # ★ Hypothesis randomized
        ├── __init__.py
        └── test_random_sync_sequences.py
```

---

## Instance Configuration

From user:
- **SQL 2022 "InTheEnd"**: port 13727
- **SQL 2008 "BigBad2008"**: port 10525  
- **Docker 2025**: port 1444 (default instance)

Connection login: `King` (sysadmin) - PROTECTED, never modify

---

## Complete Test Categories

### L1: Foundation (5 tests)
```
test_audit_creates_excel.py      # audit → Excel exists
test_all_sheets_present.py       # 20 sheets exist
test_column_alignment.py         # Headers match schema
test_finding_in_delta.py         # Test additions appear
test_cli_exit_codes.py           # Commands return 0
```

### L2: Annotation (5 tests)
```
test_notes_persist.py
test_justification_persist.py
test_review_status_persist.py
test_purpose_persist.py
test_unicode_values.py
```

### L3: State Transitions (6 tests)
```
test_state_fixed.py              # FAIL → PASS
test_state_regression.py         # PASS → FAIL
test_state_new_issue.py          # (new) → FAIL
test_state_exception_add.py      # FAIL → FAIL+Exception
test_state_exception_remove.py   # FAIL+Exc → FAIL
test_state_exception_fixed.py    # FAIL+Exc → PASS
```

### L4: Action Log (4 tests)
```
test_log_entry_fixed.py
test_log_entry_regression.py
test_log_entry_exception.py
test_action_log_sheet.py
```

### L5: Cross-Sheet (3 tests)
```
test_multi_sheet_sync.py
test_sheet_isolation.py
test_stats_consistency.py
```

### L6: CLI Commands (6 tests)
```
test_cmd_audit.py
test_cmd_sync.py
test_cmd_finalize.py
test_cmd_definalize.py
test_cmd_status.py
test_cmd_persian.py
```

### L7: Error Handling (4 tests)
```
test_err_locked_file.py
test_err_invalid_audit_id.py
test_err_finalized_blocked.py
test_err_bad_config.py
```

### L8: Stateful/Random (1 test file, many sequences)
```
test_random_sync_sequences.py    # Hypothesis explores orderings
```

---

## Dependencies

```txt
# Add to requirements.txt
allpairspy>=2.5.1
pytest-ordering>=0.6
pytest-timeout>=2.3.1
```

---

## Implementation Phases (Revised)

| Phase | Task | Time | Key Deliverable |
|-------|------|------|-----------------|
| 0 | Add dependencies | 5 min | requirements.txt |
| 1 | Create tests/shared/ | 40 min | assertions/, helpers/ |
| 2 | Create tests/real_db/contexts/ | 40 min | RealDBTestContext, BaselineManager |
| 3 | Create atomic fixtures | 50 min | 10+ deterministic SQL scripts |
| 4 | L1 Foundation tests | 25 min | 5 test files |
| 5 | L2 Annotation tests | 25 min | 5 test files |
| 6 | L3 State transition tests | 35 min | 6 test files |
| 7 | L4 Action log tests | 20 min | 4 test files |
| 8 | L5 Cross-sheet tests | 20 min | 3 test files |
| 9 | L6 CLI command tests | 20 min | 6 test files |
| 10 | L7 Error handling tests | 20 min | 4 test files |
| 11 | L8 Stateful/Hypothesis | 30 min | Random sync machine |
| 12 | Update docs | 30 min | TEST_ARCHITECTURE.md |

**Total: ~6 hours**

---

## Recommended Priority Order

If time is constrained:

1. **Phase 0-2**: Infrastructure (must have)
2. **Phase 3**: Atomic fixtures (must have)
3. **Phase 4 (L1)**: Foundation (must have)
4. **Phase 6 (L3)**: State transitions (critical logic)
5. **Phase 9 (L6)**: CLI commands (user-facing)
6. **Phase 11 (L8)**: Randomized (catches edge cases)

**Minimum viable: Phases 0-4, 6, 9 = ~3.5 hours**

---

## Pre-Execution Checklist

Before starting:
- [ ] Capture baseline snapshot of 3 instances
- [ ] Confirm King login works on all 3
- [ ] Create `tests/shared/` folder
- [ ] Create `tests/real_db/` folder
- [ ] Add dependencies to requirements.txt

---

## Questions Resolved

1. ✅ Randomized testing: Hypothesis stateful machine
2. ✅ Pre-existing discrepancies: Baseline snapshot + delta assertions
3. ✅ Instance config: 2022:13727, 2008:10525, Docker:1444
4. ✅ Protected entities: King login, system DBs
5. ✅ simulate-discrepancies: Keep for now

---

## Remaining Questions

1. **Baseline capture**: Should I run this once at start or before each test session?
   - Recommend: Once per test session (fixture scope="session")

2. **Failure strategy**: If L1 fails, should we skip higher layers?
   - Recommend: Yes, use pytest-ordering dependencies

3. **Parallel execution**: Can tests run in parallel across instances?
   - Recommend: No for now, sequential is safer
