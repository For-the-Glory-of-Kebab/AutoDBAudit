"""
Sync cycle atoms.

Atoms for running synchronization operations in tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .base import Atom, AtomResult

if TYPE_CHECKING:
    from ..conftest import TestContext


@dataclass
class SyncCycleAtom(Atom):
    """Run a complete sync cycle."""

    generate_mock_findings: bool = True

    @property
    def name(self) -> str:
        return "SyncCycle"

    def execute(self, ctx: "TestContext") -> AtomResult:
        result = ctx.run_sync_cycle(generate_mock_findings=self.generate_mock_findings)

        # Store result in context for subsequent verification atoms
        ctx._last_sync_result = result

        exception_count = len(result.get("exception_changes", []))
        return AtomResult(
            self.name,
            True,
            f"Cycle {result['cycle']}: {exception_count} exception changes",
            result,
        )


@dataclass
class SyncWithoutMockFindingsAtom(Atom):
    """Run sync cycle without generating mock findings (for pure annotation tests)."""

    @property
    def name(self) -> str:
        return "SyncWithoutMockFindings"

    def execute(self, ctx: "TestContext") -> AtomResult:
        result = ctx.run_sync_cycle(generate_mock_findings=False)
        ctx._last_sync_result = result
        return AtomResult(
            self.name,
            True,
            f"Cycle {result['cycle']}: pure annotation sync",
            result,
        )


@dataclass
class MultipleSyncCyclesAtom(Atom):
    """Run multiple sync cycles in sequence."""

    count: int = 3
    generate_mock_findings: bool = True

    @property
    def name(self) -> str:
        return f"MultipleSyncCycles({self.count})"

    def execute(self, ctx: "TestContext") -> AtomResult:
        results = []
        for i in range(self.count):
            result = ctx.run_sync_cycle(
                generate_mock_findings=self.generate_mock_findings
            )
            results.append(result)
            ctx._last_sync_result = result

        return AtomResult(
            self.name,
            True,
            f"Completed {self.count} sync cycles",
            {"sync_results": results, "final_cycle": ctx.cycle_count},
        )
