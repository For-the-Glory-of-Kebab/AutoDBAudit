# AutoDBAudit Test Architecture - Comprehensive Design Document

## Document Status
- **Created**: 2025-12-25
- **Version**: 2.0
- **Status**: ACTIVE

---

## Executive Summary

This document defines the comprehensive test architecture for AutoDBAudit. The goal is to achieve **exhaustive coverage** of all possible state combinations, field persistence, sync behaviors, and error conditions through a **layered, modular approach**.

**Current Test Count**: 209+ tests passing (198 ultimate_e2e + 11 build)

---

## Vision & Philosophy

### Core Principles

1. **TDD-First**: Write tests before implementing features. Tests are the specification.

2. **Layered Coverage**: Build from atomic operations → composed behaviors → full scenarios.

3. **Exhaustive Combinations**: Use pairwise combinatorial testing to cover all meaningful combinations without O(n!) explosion.

4. **Reproducible Randomness**: Use seeded random scenarios for stress testing with reproducibility.

5. **No Prompts**: All tests run autonomously via wrapper scripts (per `no-prompts.md`).

6. **Fail Fast, Narrow Down**: Test failures should point to exactly one root cause.

### Industry Alignment

This architecture aligns with proven testing methodologies:

| Our Approach | Industry Standard |
|--------------|-------------------|
| Module-by-module field tests | **Unit Testing / Micro-tests** |
| All state transitions | **State Transition Testing** (black-box technique) |
| Random combos with controlled coverage | **Pairwise/Combinatorial Testing** (NIST research) |
| Layered build-up to E2E | **Test Pyramid** (Mike Cohn, 2009) |
| Composable atoms | **Page Object Pattern / Test DSL** |
| Seeded randomness | **Property-Based Testing** (QuickCheck, 1999) |

### Why These Libraries?

| Library | Purpose | Methodology |
|---------|---------|-------------|
| `hypothesis` | Generates edge cases automatically | Property-Based Testing |
| `allpairspy` | Mathematically optimal coverage | Pairwise Combinatorial |
| `pytest-cov` | Identifies untested code | Coverage Analysis |
| `faker` | Realistic test data | Data-Driven Testing |

---

## Test Directory Structure

```
tests/
├── conftest.py              # Root pytest config, markers, sys.path setup
├── archive/                 # Deprecated tests (do not run)
│
├── ultimate_e2e/           # Primary E2E test suite ★ CANONICAL ★
│   ├── conftest.py          # TestContext fixture
│   ├── sheet_specs/         # Per-sheet specifications
│   │   ├── __init__.py
│   │   └── all_specs.py     # SheetSpec definitions for all 20 sheets
│   │
│   ├── atoms/               # Modular atomic operations ★ NEW ★
│   │   ├── __init__.py      # Public API exports
│   │   ├── base.py          # Atom, AtomResult, AssertionAtom
│   │   ├── excel.py         # Excel operations (6 atoms)
│   │   ├── db.py            # Database operations (5 atoms)
│   │   ├── sync.py          # Sync cycle operations (3 atoms)
│   │   ├── assertions.py    # Verification atoms (8 atoms)
│   │   ├── scenarios.py     # AtomSequence, ScenarioBuilder
│   │   └── generators.py    # Random/combinatorial generators
│   │
│   ├── test_atoms.py        # Tests using atom infrastructure
│   ├── test_annotation_flow.py
│   ├── test_multi_sheet.py
│   ├── test_notes_persistence.py
│   ├── test_remediation.py
│   ├── test_report_generation.py
│   ├── test_state_transitions.py
│   ├── test_stats.py
│   ├── test_sync_integrity.py
│   └── test_sync_stability.py
│
├── layers/                  # 6-Layer test architecture ★ NEW ★
│   ├── conftest.py          # LayerTestContext fixture
│   ├── L1_field/            # Field-level persistence
│   ├── L2_state/            # State transition tests
│   ├── L3_sync/             # Sync cycle tests
│   ├── L4_sheet/            # Combinatorial per-sheet
│   ├── L5_cross/            # Cross-sheet orchestration
│   └── L6_e2e/              # Full E2E scenarios
│
├── build/                   # Build verification tests ★ NEW ★
│   └── test_build.py        # Package structure, imports, CLI
│
└── test_state_machine.py    # Core state machine unit tests
```

---

## 6-Layer Test Architecture

### Layer 1: Field Persistence (tests/layers/L1_field/)

**Purpose**: Verify each annotation field persists correctly in isolation.

**Fields Tested**:
- `notes` - Free-text notes column
- `justification` - Exception justification text
- `review_status` - Dropdown (Exception, Reviewed, etc.)
- `last_reviewed` - Date field
- `indicator` - ⏳/✓ action indicator

**Test Categories**:
1. Excel write → read back → verify match
2. DB write → read back → verify match
3. Excel → DB round-trip
4. DB → Excel round-trip
5. Invalid data (unicode, nulls, long text)
6. Property-based with hypothesis

**Files**:
- `test_notes_persistence.py`
- `test_justification_persistence.py`
- `test_review_status_persistence.py`

---

### Layer 2: State Transitions (tests/layers/L2_state/)

**Purpose**: Verify state machine correctly classifies all transitions.

**Transitions Covered**:
| Old Status | New Status | Expected Type |
|------------|------------|---------------|
| FAIL | PASS | FIXED |
| PASS | FAIL | REGRESSION |
| None | FAIL | NEW_ISSUE |
| FAIL | FAIL+Exception | EXCEPTION_ADDED |
| FAIL+Exception | FAIL | EXCEPTION_REMOVED |
| FAIL+Exception | PASS | FIXED (exception cleared) |
| * | * (same) | NO_CHANGE |

**Critical Bug Fix Verified**:
When FAIL+Exception → PASS (FIXED):
- Keep `justification` as documentation ✓
- Clear `review_status` to "" ✓
- Action log shows FIXED (not EXCEPTION_REMOVED) ✓

**Files**:
- `test_exception_fixed.py`

---

### Layer 3: Sync Cycle (tests/layers/L3_sync/)

**Purpose**: Verify complete sync cycles with action log and stats.

**Test Categories**:
1. Single sync creates proper action log entries
2. Multi-sync stability (3+ syncs with no changes = 0 new actions)
3. Action log records correct change types
4. Stats are accurate after sync

**Files**:
- `test_action_log.py`

---

### Layer 4: Combinatorial (tests/layers/L4_sheet/)

**Purpose**: Use pairwise testing for exhaustive field/value combinations.

**Technique**: allpairspy for pairwise generation

```python
from allpairspy import AllPairs

parameters = [
    ["notes", "justification", "review_status"],
    ["", "short", "long text", "unicode"],
    ["sa_account", "login", "config"],
]

for field, value, entity_type in AllPairs(parameters):
    # Test this combination
```

**Files**:
- `test_combinatorial.py`

---

### Layer 5: Cross-Sheet (tests/layers/L5_cross/)

**Purpose**: Verify operations across multiple sheets are independent.

**Test Scenarios**:
1. Exception on Sheet A doesn't affect Sheet B
2. FIXED on Sheet A doesn't clear Sheet B's exception
3. Simultaneous changes to multiple sheets all persist

**Files**:
- `test_cross_sheet.py`

---

### Layer 6: Full E2E (tests/layers/L6_e2e/)

**Purpose**: Complete end-to-end scenarios.

**Scenarios**:
1. Full audit lifecycle (baseline → syncs → finalize)
2. Finalize/Definalize flow
3. Remediation script generation
4. Error recovery (crash mid-sync)

---

## Atoms Infrastructure (tests/ultimate_e2e/atoms/)

### Purpose

Provide reusable, composable atomic test operations.

### Module Design (SRP)

| Module | Purpose | Exports |
|--------|---------|---------|
| `base.py` | Core classes | Atom, AtomResult, AssertionAtom |
| `excel.py` | Excel operations | AddAnnotationAtom, ReadAnnotationAtom, etc. |
| `db.py` | Database operations | VerifyDbAnnotationAtom, InsertFindingAtom, etc. |
| `sync.py` | Sync cycles | SyncCycleAtom, MultipleSyncCyclesAtom |
| `assertions.py` | Verification | VerifyExceptionCountAtom, VerifyNoNewActionsAtom |
| `scenarios.py` | Composition | AtomSequence, ScenarioBuilder |
| `generators.py` | Random scenarios | generate_random_scenario, generate_state_matrix_scenario |

### Usage Example

```python
from tests.ultimate_e2e.atoms import (
    CreateExcelAtom,
    AddExceptionAtom,
    SyncCycleAtom,
    VerifyExceptionCountAtom,
    AtomSequence,
)

seq = AtomSequence([
    CreateExcelAtom(),
    AddExceptionAtom("SA Account", value="Approved by CISO"),
    SyncCycleAtom(),
    VerifyExceptionCountAtom(expected=1),
])
results = seq.run(ctx)
```

---

## Testing Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| pytest | ≥7.0 | Test framework |
| hypothesis | 6.148+ | Property-based testing |
| allpairspy | 2.5+ | Pairwise combinatorial |
| pytest-cov | ≥4.0 | Coverage reporting |
| faker | 33.0+ | Random test data |
| openpyxl | ≥3.1 | Excel file handling |

---

## Test Markers

Defined in `tests/conftest.py`:

```python
@pytest.mark.unit          # Fast atomic tests (<5s)
@pytest.mark.component     # Single service tests (<30s)
@pytest.mark.integration   # Multi-service tests (<60s)
@pytest.mark.e2e           # Per-sheet E2E (<120s)
@pytest.mark.scenario      # Complex multi-sync scenarios
@pytest.mark.slow          # Tests taking >30s
@pytest.mark.sheet         # Per-sheet parametrized
@pytest.mark.finalize      # Finalize/Definalize tests
@pytest.mark.remediation   # Remediation script tests
```

---

## Running Tests

### All Tests (excluding archive)
```powershell
.\scripts\run_all_tests.ps1
```

### Ultimate E2E Only
```powershell
.\scripts\run_ultimate_e2e.ps1
```

### Atom Tests
```powershell
.\scripts\run_atom_tests.ps1
```

### Layer Tests
```powershell
.\scripts\run_layer_tests.ps1
```

### By Marker
```powershell
pytest -m "unit"           # Only unit tests
pytest -m "not slow"       # Skip slow tests
pytest -m "scenario"       # Only scenario tests
```

---

## Critical Bug Fixes Implemented

### Exception Cleared on FIXED

**Location**: `sync_service.py` PHASE 5b

**Behavior**: When item transitions FAIL+Exception → PASS:
1. Keep `justification` (documentation preserved)
2. Clear `review_status` to "" (exception state cleared)
3. Clear indicator from ✓ to blank
4. Log as FIXED (not EXCEPTION_REMOVED)

**Test Coverage**: `tests/layers/L2_state/test_exception_fixed.py`

---

## Deprecated Documents

The following documents are superseded by this one:

- `docs/TEST_ARCHITECTURE_WALKTHROUGH.md` → Superseded
- `docs/TEST_ARCHITECTURE_TASKS.md` → Superseded
- `docs/PHASE2_WALKTHROUGH.md` → Superseded

---

## Next Steps

1. **Fix Layer Tests**: Resolve hypothesis/fixture compatibility issue
2. **Complete L6 E2E**: Add finalize/definalize tests
3. **SyncService Injection**: Refactor for test isolation (Option A)
4. **Coverage Report**: Generate pytest-cov coverage report
5. **CI Integration**: Add GitHub Actions workflow for tests
