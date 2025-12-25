"""
Scenario builders for composing atoms.

Provides:
- AtomSequence: Execute atoms in order
- ScenarioBuilder: Build multi-sync scenarios with phases
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Atom, AtomResult
from .sync import SyncCycleAtom

if TYPE_CHECKING:
    from ..conftest import TestContext


class AtomSequence:
    """
    A sequence of atoms to execute in order.

    Example:
        seq = AtomSequence([
            CreateExcelAtom(),
            AddExceptionAtom("SA Account"),
            SyncCycleAtom(),
            VerifyExceptionCountAtom(expected=1),
        ])
        results = seq.run(ctx)
    """

    def __init__(self, atoms: list[Atom] | None = None):
        self.atoms = atoms or []

    def add(self, atom: Atom) -> "AtomSequence":
        """Add an atom to the sequence (fluent API)."""
        self.atoms.append(atom)
        return self

    def run(self, ctx: "TestContext", stop_on_failure: bool = True) -> list[AtomResult]:
        """
        Execute all atoms in sequence.

        Args:
            ctx: Test context
            stop_on_failure: If True, stop on first failure

        Returns:
            List of AtomResults
        """
        results = []
        for atom in self.atoms:
            result = atom.execute(ctx)
            results.append(result)

            # Run optional verification
            try:
                atom.verify(ctx, result)
            except AssertionError as e:
                result.success = False
                result.message += f" (verify failed: {e})"

            if stop_on_failure and not result.success:
                break

        return results

    def __len__(self) -> int:
        return len(self.atoms)


class ScenarioBuilder:
    """
    Build multi-sync scenarios with atoms distributed across phases.

    Example:
        scenario = ScenarioBuilder()
        scenario.before_sync(1, [CreateExcelAtom(), AddExceptionAtom("SA Account")])
        scenario.after_sync(1, [VerifyExceptionCountAtom(expected=1)])
        scenario.before_sync(2, [AddExceptionAtom("Server Logins")])
        scenario.after_sync(2, [VerifyExceptionCountAtom(expected=1)])  # Only new
        results = scenario.run(ctx, num_syncs=3)
    """

    def __init__(self):
        self._phases: dict[str, list[Atom]] = {}
        self._labels: dict[int, str] = {}  # Optional sync labels

    def before_sync(self, sync_num: int, atoms: list[Atom]) -> "ScenarioBuilder":
        """Add atoms to execute before sync N."""
        key = f"before_sync{sync_num}"
        self._phases.setdefault(key, []).extend(atoms)
        return self

    def after_sync(self, sync_num: int, atoms: list[Atom]) -> "ScenarioBuilder":
        """Add atoms to execute after sync N."""
        key = f"after_sync{sync_num}"
        self._phases.setdefault(key, []).extend(atoms)
        return self

    def label_sync(self, sync_num: int, label: str) -> "ScenarioBuilder":
        """Add a descriptive label for documentation."""
        self._labels[sync_num] = label
        return self

    def run(
        self,
        ctx: "TestContext",
        num_syncs: int = 3,
        stop_on_failure: bool = True,
    ) -> dict[str, list[AtomResult]]:
        """
        Execute the scenario.

        Args:
            ctx: Test context
            num_syncs: Number of sync cycles to run
            stop_on_failure: If True, stop on first failure

        Returns:
            Dict mapping phase names to their results
        """
        all_results: dict[str, list[AtomResult]] = {}
        failed = False

        for sync_num in range(1, num_syncs + 1):
            if failed and stop_on_failure:
                break

            # Before sync
            before_key = f"before_sync{sync_num}"
            if before_key in self._phases:
                seq = AtomSequence(self._phases[before_key])
                results = seq.run(ctx, stop_on_failure)
                all_results[before_key] = results
                if any(not r.success for r in results):
                    failed = True
                    if stop_on_failure:
                        continue

            # Run sync
            sync_atom = SyncCycleAtom()
            sync_result = sync_atom.execute(ctx)
            all_results[f"sync{sync_num}"] = [sync_result]
            if not sync_result.success:
                failed = True
                if stop_on_failure:
                    continue

            # After sync
            after_key = f"after_sync{sync_num}"
            if after_key in self._phases:
                seq = AtomSequence(self._phases[after_key])
                results = seq.run(ctx, stop_on_failure)
                all_results[after_key] = results
                if any(not r.success for r in results):
                    failed = True

        return all_results

    def summarize(self) -> str:
        """Generate a human-readable summary of the scenario."""
        lines = ["Scenario:"]
        sync_nums = set()
        for key in self._phases:
            if key.startswith("before_sync") or key.startswith("after_sync"):
                num = int(key.split("sync")[1])
                sync_nums.add(num)

        for num in sorted(sync_nums):
            label = self._labels.get(num, "")
            lines.append(f"  Sync {num}{f' ({label})' if label else ''}:")
            before = self._phases.get(f"before_sync{num}", [])
            after = self._phases.get(f"after_sync{num}", [])
            if before:
                lines.append(f"    Before: {', '.join(a.name for a in before)}")
            if after:
                lines.append(f"    After: {', '.join(a.name for a in after)}")

        return "\n".join(lines)
