"""
Atoms Package - Modular Test Infrastructure.

This package provides atomic test operations organized by responsibility:
- base: Core Atom class and AtomResult
- excel: Excel read/write operations
- db: Database operations
- sync: Sync cycle operations
- assertions: Verification atoms
- scenarios: AtomSequence and ScenarioBuilder
- generators: Random scenario generation

Usage:
    from tests.ultimate_e2e.atoms import (
        AddExceptionAtom,
        SyncCycleAtom,
        VerifyExceptionCountAtom,
        AtomSequence,
        ScenarioBuilder,
    )
"""

from .base import Atom, AtomResult, AssertionAtom
from .excel import (
    AddAnnotationAtom,
    AddExceptionAtom,
    ReadAnnotationAtom,
    MarkRowAsFailAtom,
    CreateExcelAtom,
    ClearAnnotationAtom,
)
from .db import (
    VerifyDbAnnotationAtom,
    VerifyDbFindingAtom,
    InsertFindingAtom,
    CountActionLogAtom,
    GetActionLogEntriesAtom,
)
from .sync import (
    SyncCycleAtom,
    SyncWithoutMockFindingsAtom,
    MultipleSyncCyclesAtom,
)
from .assertions import (
    VerifyAnnotationValueAtom,
    VerifyExceptionCountAtom,
    VerifyActionLogCountAtom,
    VerifyChangeTypeAtom,
    VerifyNoNewActionsAtom,
    VerifyAnnotationNotEmptyAtom,
    VerifyAnnotationEmptyAtom,
)
from .scenarios import AtomSequence, ScenarioBuilder
from .generators import (
    generate_random_scenario,
    generate_all_sheets_scenario,
    generate_state_matrix_scenario,
    generate_multi_sheet_cross_correlation_scenario,
)

__all__ = [
    # Base
    "Atom",
    "AtomResult",
    "AssertionAtom",
    # Excel
    "AddAnnotationAtom",
    "AddExceptionAtom",
    "ReadAnnotationAtom",
    "MarkRowAsFailAtom",
    "CreateExcelAtom",
    "ClearAnnotationAtom",
    # DB
    "VerifyDbAnnotationAtom",
    "VerifyDbFindingAtom",
    "InsertFindingAtom",
    "CountActionLogAtom",
    "GetActionLogEntriesAtom",
    # Sync
    "SyncCycleAtom",
    "SyncWithoutMockFindingsAtom",
    "MultipleSyncCyclesAtom",
    # Assertions
    "VerifyAnnotationValueAtom",
    "VerifyExceptionCountAtom",
    "VerifyActionLogCountAtom",
    "VerifyChangeTypeAtom",
    "VerifyNoNewActionsAtom",
    "VerifyAnnotationNotEmptyAtom",
    "VerifyAnnotationEmptyAtom",
    # Scenarios
    "AtomSequence",
    "ScenarioBuilder",
    # Generators
    "generate_random_scenario",
    "generate_all_sheets_scenario",
    "generate_state_matrix_scenario",
    "generate_multi_sheet_cross_correlation_scenario",
]
