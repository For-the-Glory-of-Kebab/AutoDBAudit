"""
Scenario generators for stress testing and comprehensive coverage.

Provides:
- generate_random_scenario: Random but reproducible scenarios
- generate_all_sheets_scenario: Cover all sheet types
- generate_state_matrix_scenario: Cover all state transitions
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from .excel import (
    AddExceptionAtom,
    CreateExcelAtom,
    MarkRowAsFailAtom,
    ClearAnnotationAtom,
)
from .assertions import VerifyExceptionCountAtom, VerifyNoNewActionsAtom
from .scenarios import ScenarioBuilder

if TYPE_CHECKING:
    pass


def generate_random_scenario(
    seed: int | None = None,
    num_syncs: int = 3,
    annotations_per_sync: int = 2,
) -> ScenarioBuilder:
    """
    Generate a random but reproducible scenario.

    Args:
        seed: Random seed for reproducibility
        num_syncs: Number of sync cycles
        annotations_per_sync: Max annotations to add per sync

    Returns:
        ScenarioBuilder configured with random atoms
    """
    from ..sheet_specs import get_specs_with_exceptions

    if seed is not None:
        random.seed(seed)

    builder = ScenarioBuilder()
    available_sheets = list(get_specs_with_exceptions())

    for sync_num in range(1, num_syncs + 1):
        atoms = []

        # Add random annotations
        num_annotations = random.randint(0, annotations_per_sync)
        for _ in range(num_annotations):
            spec = random.choice(available_sheets)
            value = f"Random test {random.randint(1000, 9999)}"
            atoms.append(AddExceptionAtom(sheet=spec.sheet_name, value=value))

        if atoms:
            builder.before_sync(sync_num, atoms)
            builder.label_sync(sync_num, f"Random: {len(atoms)} annotations")

    return builder


def generate_all_sheets_scenario() -> ScenarioBuilder:
    """
    Generate a scenario that covers all sheet types with exceptions.

    Adds one exception to each sheet that supports exceptions.
    """
    from ..sheet_specs import get_specs_with_exceptions

    builder = ScenarioBuilder()
    specs = list(get_specs_with_exceptions())

    # First sync: Create Excel with all sheets
    builder.before_sync(1, [CreateExcelAtom()])

    # Add exceptions to all sheets (spread across syncs for variety)
    batch_size = 4
    sync_num = 1
    for i, spec in enumerate(specs):
        if i > 0 and i % batch_size == 0:
            sync_num += 1

        builder.before_sync(
            sync_num,
            [
                MarkRowAsFailAtom(spec.sheet_name, 2),
                AddExceptionAtom(
                    spec.sheet_name, value=f"Test exception for {spec.sheet_name}"
                ),
            ],
        )
        builder.label_sync(
            sync_num,
            f"Batch {sync_num}: sheets {i}-{min(i+batch_size-1, len(specs)-1)}",
        )

    # Final sync: Verify stability
    builder.after_sync(sync_num + 1, [VerifyNoNewActionsAtom()])

    return builder


def generate_state_matrix_scenario() -> ScenarioBuilder:
    """
    Generate a scenario covering all state transitions from E2E_STATE_MATRIX.md:

    1. FAIL → PASS = FIXED
    2. PASS → FAIL = REGRESSION
    3. (None) → FAIL = NEW_ISSUE
    4. FAIL + justification = EXCEPTION_ADDED
    5. FAIL+Exception → cleared = EXCEPTION_REMOVED
    6. FAIL+Exception → PASS = FIXED (exception cleared)
    7. 3 syncs no change = 0 new actions (STABILITY)
    """
    builder = ScenarioBuilder()

    # ----- SYNC 1: Setup initial state -----
    builder.before_sync(1, [CreateExcelAtom()])
    builder.label_sync(1, "Initial setup - add exceptions")

    # Scenario 4: FAIL + justification = EXCEPTION_ADDED
    builder.before_sync(
        1,
        [
            MarkRowAsFailAtom("SA Account", 2),
            AddExceptionAtom("SA Account", value="Exception for scenario 4"),
        ],
    )

    # Scenario 5: Setup for removal (will clear in sync 2)
    builder.before_sync(
        1,
        [
            MarkRowAsFailAtom("Server Logins", 2),
            AddExceptionAtom("Server Logins", value="Will be removed in sync 2"),
        ],
    )

    # ----- SYNC 2: State changes -----
    builder.label_sync(2, "State changes - removals")

    # Scenario 5: FAIL+Exception → cleared = EXCEPTION_REMOVED
    builder.before_sync(
        2,
        [
            ClearAnnotationAtom("Server Logins", 2, "Justification"),
        ],
    )

    # ----- SYNC 3: Stability check -----
    builder.label_sync(3, "Stability - no changes expected")
    builder.after_sync(3, [VerifyNoNewActionsAtom()])

    return builder


def generate_multi_sheet_cross_correlation_scenario() -> ScenarioBuilder:
    """
    Generate a scenario with changes across multiple sheets simultaneously
    to test cross-sheet correlation and isolation.
    """
    builder = ScenarioBuilder()

    builder.before_sync(1, [CreateExcelAtom()])
    builder.label_sync(1, "Multi-sheet simultaneous changes")

    # Add exceptions to multiple sheets in same sync
    sheets_to_test = ["SA Account", "Server Logins", "Databases", "Linked Servers"]

    for i, sheet in enumerate(sheets_to_test):
        builder.before_sync(
            1,
            [
                MarkRowAsFailAtom(sheet, 2),
                AddExceptionAtom(sheet, value=f"Cross-sheet test {i+1}"),
            ],
        )

    # Verify all were detected
    builder.after_sync(
        1,
        [
            VerifyExceptionCountAtom(expected=len(sheets_to_test), change_type="added"),
        ],
    )

    # Second sync: Stability
    builder.after_sync(2, [VerifyNoNewActionsAtom()])

    return builder
