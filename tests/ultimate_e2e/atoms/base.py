"""
Base classes for the Atom test infrastructure.

Provides:
- Atom: Abstract base for all atomic operations
- AtomResult: Result of executing an atom
- AssertionAtom: Atom that only asserts (no side effects)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..conftest import TestContext


@dataclass
class AtomResult:
    """Result of executing an atom."""

    atom_name: str
    success: bool
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"{status} {self.atom_name}: {self.message}"


class Atom(ABC):
    """
    Base class for atomic test operations.

    An atom represents a single, indivisible test operation that:
    1. Has a clear name for logging
    2. Executes one specific action
    3. Optionally verifies the result

    Atoms can be combined using AtomSequence or ScenarioBuilder.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for logging."""
        pass

    @abstractmethod
    def execute(self, ctx: "TestContext") -> AtomResult:
        """
        Execute the atomic operation.

        Args:
            ctx: Test context with DB, Excel paths, and helpers

        Returns:
            AtomResult with success status and any data
        """
        pass

    def verify(self, ctx: "TestContext", result: AtomResult) -> None:
        """
        Optional verification after execute.

        Override to add post-execute assertions.
        Raises AssertionError on failure.
        """
        pass


class AssertionAtom(Atom):
    """
    Atom that only asserts (no side effects).

    Override _assert() to implement verification logic.
    execute() automatically wraps _assert() in try/except.
    """

    def execute(self, ctx: "TestContext") -> AtomResult:
        try:
            self._assert(ctx)
            return AtomResult(self.name, True, "Assertion passed")
        except AssertionError as e:
            return AtomResult(self.name, False, str(e))

    @abstractmethod
    def _assert(self, ctx: "TestContext") -> None:
        """Override to implement assertion logic."""
        pass
