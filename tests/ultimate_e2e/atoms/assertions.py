"""
Assertion atoms.

Atoms that verify state without side effects.
All assertions use the AssertionAtom base class.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .base import AssertionAtom

if TYPE_CHECKING:
    from ..conftest import TestContext


@dataclass
class VerifyAnnotationValueAtom(AssertionAtom):
    """Assert an annotation in Excel has expected value."""

    sheet: str
    row: int
    column: str
    expected: str

    @property
    def name(self) -> str:
        return f"VerifyAnnotation({self.sheet}[{self.row}].{self.column})"

    def _assert(self, ctx: "TestContext") -> None:
        actual = ctx.read_annotation_from_excel(self.sheet, self.row, self.column)
        assert actual == self.expected, f"Expected '{self.expected}', got '{actual}'"


@dataclass
class VerifyExceptionCountAtom(AssertionAtom):
    """Assert the number of exception changes in last sync."""

    expected: int
    change_type: str | None = None  # "added", "removed", "updated"

    @property
    def name(self) -> str:
        return f"VerifyExceptionCount(expected={self.expected})"

    def _assert(self, ctx: "TestContext") -> None:
        assert (
            hasattr(ctx, "_last_sync_result") and ctx._last_sync_result
        ), "No sync has been run yet"
        changes = ctx._last_sync_result.get("exception_changes", [])

        if self.change_type:
            changes = [c for c in changes if c.get("change_type") == self.change_type]

        actual = len(changes)
        assert (
            actual == self.expected
        ), f"Expected {self.expected} exception changes, got {actual}"


@dataclass
class VerifyActionLogCountAtom(AssertionAtom):
    """Assert the number of action log entries."""

    expected: int

    @property
    def name(self) -> str:
        return f"VerifyActionLogCount(expected={self.expected})"

    def _assert(self, ctx: "TestContext") -> None:
        actual = ctx.count_action_log()
        assert (
            actual == self.expected
        ), f"Expected {self.expected} action log entries, got {actual}"


@dataclass
class VerifyChangeTypeAtom(AssertionAtom):
    """Assert that a specific change type was detected in last sync."""

    change_type: str  # "added", "removed", "updated", "fixed", "regression"
    min_count: int = 1

    @property
    def name(self) -> str:
        return f"VerifyChangeType({self.change_type}>={self.min_count})"

    def _assert(self, ctx: "TestContext") -> None:
        assert (
            hasattr(ctx, "_last_sync_result") and ctx._last_sync_result
        ), "No sync has been run yet"
        changes = ctx._last_sync_result.get("exception_changes", [])

        matching = [c for c in changes if c.get("change_type") == self.change_type]
        actual = len(matching)

        assert (
            actual >= self.min_count
        ), f"Expected >={self.min_count} {self.change_type}, got {actual}"


@dataclass
class VerifyNoNewActionsAtom(AssertionAtom):
    """Assert that no new actions were logged in last sync (stability test)."""

    @property
    def name(self) -> str:
        return "VerifyNoNewActions"

    def _assert(self, ctx: "TestContext") -> None:
        assert (
            hasattr(ctx, "_last_sync_result") and ctx._last_sync_result
        ), "No sync has been run yet"
        changes = ctx._last_sync_result.get("exception_changes", [])
        assert (
            len(changes) == 0
        ), f"Expected 0 changes for stability, got {len(changes)}"


@dataclass
class VerifyAnnotationNotEmptyAtom(AssertionAtom):
    """Assert an annotation is not empty."""

    sheet: str
    row: int
    column: str

    @property
    def name(self) -> str:
        return f"VerifyNotEmpty({self.sheet}[{self.row}].{self.column})"

    def _assert(self, ctx: "TestContext") -> None:
        actual = ctx.read_annotation_from_excel(self.sheet, self.row, self.column)
        assert (
            actual is not None and str(actual).strip() != ""
        ), f"Expected non-empty value, got '{actual}'"


@dataclass
class VerifyAnnotationEmptyAtom(AssertionAtom):
    """Assert an annotation is empty or None."""

    sheet: str
    row: int
    column: str

    @property
    def name(self) -> str:
        return f"VerifyEmpty({self.sheet}[{self.row}].{self.column})"

    def _assert(self, ctx: "TestContext") -> None:
        actual = ctx.read_annotation_from_excel(self.sheet, self.row, self.column)
        is_empty = actual is None or str(actual).strip() == ""
        assert is_empty, f"Expected empty value, got '{actual}'"
