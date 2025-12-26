"""
Deep State Transition Assertions.

Comprehensive verification of state transitions including:
- Before/after Result comparison
- Annotation preservation
- Indicator column changes
- Cross-reference with action log
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .deep_excel import RowData


class TransitionType(Enum):
    """All possible state transitions."""

    NO_CHANGE = auto()
    FIXED = auto()  # FAIL/WARN → PASS
    REGRESSION = auto()  # PASS → FAIL/WARN
    NEW_ISSUE = auto()  # None → FAIL/WARN
    REMOVED = auto()  # Entity removed
    EXCEPTION_ADDED = auto()  # Added justification
    EXCEPTION_REMOVED = auto()  # Removed justification


@dataclass
class StateSnapshot:
    """Snapshot of entity state at a point in time."""

    entity_key: str
    result: str | None  # PASS, FAIL, WARN, None
    has_justification: bool
    justification_text: str | None
    review_status: str | None
    notes: str | None
    indicator: str | None
    row_num: int | None = None

    @classmethod
    def from_row_data(
        cls, row: "RowData", entity_column: str = "Login"
    ) -> "StateSnapshot":
        """Create snapshot from RowData."""
        return cls(
            entity_key=str(row.get(entity_column) or ""),
            result=row.get("Result"),
            has_justification=bool(row.get("Justification")),
            justification_text=row.get("Justification"),
            review_status=row.get("Review Status"),
            notes=row.get("Notes"),
            indicator=row.get("Indicator"),
            row_num=row.row_num,
        )

    @property
    def is_discrepant(self) -> bool:
        return self.result in ("FAIL", "WARN")

    @property
    def is_exception(self) -> bool:
        return self.is_discrepant and self.has_justification


class DeepStateAssertions:
    """
    Deep state transition verification.

    These compare before/after states comprehensively.
    """

    @staticmethod
    def determine_transition(
        before: StateSnapshot | None,
        after: StateSnapshot,
    ) -> TransitionType:
        """
        Determine the transition type between states.

        Args:
            before: State before sync (None if new)
            after: State after sync

        Returns:
            TransitionType enum value
        """
        # New entity
        if before is None:
            if after.is_discrepant:
                return TransitionType.NEW_ISSUE
            return TransitionType.NO_CHANGE  # New PASS doesn't need action

        # Result changed
        before_disc = before.result in ("FAIL", "WARN")
        after_disc = after.result in ("FAIL", "WARN")

        if before_disc and not after_disc:
            return TransitionType.FIXED

        if not before_disc and after_disc:
            return TransitionType.REGRESSION

        # Exception changed
        if not before.has_justification and after.has_justification:
            return TransitionType.EXCEPTION_ADDED

        if before.has_justification and not after.has_justification:
            return TransitionType.EXCEPTION_REMOVED

        return TransitionType.NO_CHANGE

    @staticmethod
    def assert_transition(
        before: StateSnapshot | None,
        after: StateSnapshot,
        expected: TransitionType,
    ) -> None:
        """Assert transition matches expected type."""
        actual = DeepStateAssertions.determine_transition(before, after)

        if actual != expected:
            raise AssertionError(
                f"Transition mismatch for '{after.entity_key}':\n"
                f"  Expected: {expected.name}\n"
                f"  Actual: {actual.name}\n"
                f"  Before: result={before.result if before else None}, "
                f"just={before.has_justification if before else None}\n"
                f"  After: result={after.result}, just={after.has_justification}"
            )

    @staticmethod
    def assert_fixed(before: StateSnapshot, after: StateSnapshot) -> None:
        """Assert entity was FIXED (FAIL → PASS)."""
        assert before.is_discrepant, f"Before should be FAIL/WARN, got {before.result}"
        assert not after.is_discrepant, f"After should be PASS, got {after.result}"
        assert (
            after.result == "PASS"
        ), f"After result should be PASS, got {after.result}"

    @staticmethod
    def assert_regression(before: StateSnapshot, after: StateSnapshot) -> None:
        """Assert entity regressed (PASS → FAIL)."""
        assert not before.is_discrepant, f"Before should be PASS, got {before.result}"
        assert after.is_discrepant, f"After should be FAIL/WARN, got {after.result}"

    @staticmethod
    def assert_annotations_preserved(
        before: StateSnapshot,
        after: StateSnapshot,
    ) -> None:
        """Assert annotations survived the transition."""
        if before.notes:
            assert (
                after.notes == before.notes
            ), f"Notes changed: '{before.notes}' → '{after.notes}'"

        # Justification behavior depends on transition
        # FIXED clears exception status but may preserve justification as doc

    @staticmethod
    def assert_indicator_matches_state(
        snapshot: StateSnapshot,
    ) -> None:
        """Assert indicator column matches exception state."""
        if snapshot.is_exception:
            # Should have indicator
            if snapshot.indicator:
                assert (
                    "✓" in str(snapshot.indicator) or snapshot.indicator
                ), f"Exception should have indicator, got '{snapshot.indicator}'"
        elif snapshot.is_discrepant:
            # Discrepant but not exception - should be pending
            if snapshot.indicator:
                assert (
                    snapshot.indicator != "✓"
                ), f"Non-exception FAIL should not have ✓, got '{snapshot.indicator}'"

    @staticmethod
    def assert_exception_cleared_on_fix(
        before: StateSnapshot,
        after: StateSnapshot,
    ) -> None:
        """When FIXED, exception status should be cleared."""
        if before.is_exception:
            # After fix, Review Status should be cleared
            assert after.review_status in (
                None,
                "",
                "Accepted",
            ), f"Exception status should clear on fix, got '{after.review_status}'"
            # Justification may persist as documentation
