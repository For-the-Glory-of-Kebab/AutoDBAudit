"""
State Assertions - State transition verification.

Verifies the sync engine state machine logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TransitionType(Enum):
    """Expected transition types from state machine."""

    NO_CHANGE = "no_change"
    FIXED = "fixed"
    REGRESSION = "regression"
    NEW_ISSUE = "new_issue"
    EXCEPTION_ADDED = "exception_added"
    EXCEPTION_REMOVED = "exception_removed"


@dataclass
class StateTransition:
    """Represents a state transition test case."""

    old_result: str | None  # PASS/FAIL/WARN or None (new)
    new_result: str  # PASS/FAIL/WARN
    had_exception: bool
    has_exception: bool
    expected_type: TransitionType

    @property
    def description(self) -> str:
        """Human-readable description."""
        old = self.old_result or "(new)"
        exc_before = "+Exc" if self.had_exception else ""
        exc_after = "+Exc" if self.has_exception else ""
        return f"{old}{exc_before} → {self.new_result}{exc_after}"


# Complete state transition matrix
STATE_MATRIX: list[StateTransition] = [
    # FIXED: FAIL → PASS
    StateTransition("FAIL", "PASS", False, False, TransitionType.FIXED),
    StateTransition(
        "FAIL", "PASS", True, False, TransitionType.FIXED
    ),  # Exception cleared on fix
    StateTransition("WARN", "PASS", False, False, TransitionType.FIXED),
    # REGRESSION: PASS → FAIL/WARN
    StateTransition("PASS", "FAIL", False, False, TransitionType.REGRESSION),
    StateTransition("PASS", "WARN", False, False, TransitionType.REGRESSION),
    # NEW_ISSUE: None → FAIL/WARN
    StateTransition(None, "FAIL", False, False, TransitionType.NEW_ISSUE),
    StateTransition(None, "WARN", False, False, TransitionType.NEW_ISSUE),
    # EXCEPTION_ADDED: FAIL → FAIL+Exception
    StateTransition("FAIL", "FAIL", False, True, TransitionType.EXCEPTION_ADDED),
    StateTransition("WARN", "WARN", False, True, TransitionType.EXCEPTION_ADDED),
    # EXCEPTION_REMOVED: FAIL+Exception → FAIL (no exception)
    StateTransition("FAIL", "FAIL", True, False, TransitionType.EXCEPTION_REMOVED),
    # NO_CHANGE: Same state
    StateTransition("PASS", "PASS", False, False, TransitionType.NO_CHANGE),
    StateTransition("FAIL", "FAIL", False, False, TransitionType.NO_CHANGE),
    StateTransition(
        "FAIL", "FAIL", True, True, TransitionType.NO_CHANGE
    ),  # Exception stays
]


class StateAssertions:
    """
    State transition verification utilities.
    """

    @staticmethod
    def get_expected_transition(
        old_result: str | None,
        new_result: str,
        had_exception: bool,
        has_exception: bool,
    ) -> TransitionType:
        """
        Determine expected transition type.

        This is the single source of truth for state machine behavior.
        """
        # New finding
        if old_result is None:
            if new_result in ("FAIL", "WARN"):
                return TransitionType.NEW_ISSUE
            return TransitionType.NO_CHANGE

        # Fixed
        if old_result in ("FAIL", "WARN") and new_result == "PASS":
            return TransitionType.FIXED

        # Regression
        if old_result == "PASS" and new_result in ("FAIL", "WARN"):
            return TransitionType.REGRESSION

        # Exception changes (only if still failing)
        if new_result in ("FAIL", "WARN"):
            if not had_exception and has_exception:
                return TransitionType.EXCEPTION_ADDED
            if had_exception and not has_exception:
                return TransitionType.EXCEPTION_REMOVED

        return TransitionType.NO_CHANGE

    @staticmethod
    def assert_transition(
        old_result: str | None,
        new_result: str,
        had_exception: bool,
        has_exception: bool,
        expected: TransitionType,
    ) -> None:
        """Assert transition matches expected type."""
        actual = StateAssertions.get_expected_transition(
            old_result, new_result, had_exception, has_exception
        )
        assert actual == expected, (
            f"Transition {old_result}→{new_result} "
            f"(exc: {had_exception}→{has_exception}): "
            f"expected {expected.value}, got {actual.value}"
        )

    @staticmethod
    def get_all_transitions() -> list[StateTransition]:
        """Get the complete state matrix for parametrized tests."""
        return STATE_MATRIX.copy()
