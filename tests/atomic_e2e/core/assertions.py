"""
Custom Assertions for Atomic E2E Tests.

Provides rich assertion functions that give detailed error messages
for debugging test failures.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AssertionResult:
    """Result of an assertion check."""
    passed: bool
    message: str
    expected: Any = None
    actual: Any = None
    context: dict = None


def assert_annotation_value(
    actual: str | None,
    expected: str | None,
    context: str = "",
) -> AssertionResult:
    """
    Assert annotation value matches expected.
    
    Handles None and whitespace normalization.
    """
    # Normalize values
    actual_norm = str(actual).strip() if actual else ""
    expected_norm = str(expected).strip() if expected else ""
    
    if actual_norm == expected_norm:
        return AssertionResult(
            passed=True,
            message=f"Value matches: '{expected_norm}'",
            expected=expected_norm,
            actual=actual_norm,
        )
    else:
        return AssertionResult(
            passed=False,
            message=f"{context}: expected '{expected_norm}', got '{actual_norm}'",
            expected=expected_norm,
            actual=actual_norm,
        )


def assert_exception_count(
    actual: int,
    expected: int,
    context: str = "",
) -> AssertionResult:
    """Assert exception count matches."""
    if actual == expected:
        return AssertionResult(
            passed=True,
            message=f"Exception count correct: {expected}",
            expected=expected,
            actual=actual,
        )
    else:
        return AssertionResult(
            passed=False,
            message=f"{context}: expected {expected} exceptions, got {actual}",
            expected=expected,
            actual=actual,
        )


def assert_action_logged(
    actions: list[dict],
    entity_key: str,
    action_type: str,
    context: str = "",
) -> AssertionResult:
    """
    Assert action was logged with correct type.
    
    Args:
        actions: List of action dicts from action log
        entity_key: Expected entity key (partial match)
        action_type: Expected action type (e.g., 'EXCEPTION_ADDED')
    """
    matching = [
        a for a in actions
        if entity_key.lower() in a.get("entity_key", "").lower()
        and a.get("action_type", "").upper() == action_type.upper()
    ]
    
    if matching:
        return AssertionResult(
            passed=True,
            message=f"Action '{action_type}' found for '{entity_key}'",
            expected=action_type,
            actual=matching[0],
        )
    else:
        available = [(a.get("entity_key"), a.get("action_type")) for a in actions]
        return AssertionResult(
            passed=False,
            message=(
                f"{context}: action '{action_type}' not found for '{entity_key}'. "
                f"Available: {available[:5]}"
            ),
            expected=(entity_key, action_type),
            actual=available,
        )


def assert_no_action_logged(
    actions: list[dict],
    entity_key: str,
    action_type: str,
    context: str = "",
) -> AssertionResult:
    """Assert action was NOT logged."""
    matching = [
        a for a in actions
        if entity_key.lower() in a.get("entity_key", "").lower()
        and a.get("action_type", "").upper() == action_type.upper()
    ]
    
    if not matching:
        return AssertionResult(
            passed=True,
            message=f"No '{action_type}' action for '{entity_key}' (correct)",
        )
    else:
        return AssertionResult(
            passed=False,
            message=(
                f"{context}: unexpected action '{action_type}' found for '{entity_key}'"
            ),
            expected=None,
            actual=matching[0],
        )


def assert_key_format(
    actual_key: str,
    expected_parts: list[str],
    entity_type: str,
    context: str = "",
) -> AssertionResult:
    """
    Assert entity key has correct format.
    
    Args:
        actual_key: The key from Excel/DB
        expected_parts: List of expected key parts
        entity_type: Expected entity type prefix
    """
    expected_key = f"{entity_type}|{'|'.join(expected_parts)}".lower()
    actual_norm = actual_key.lower()
    
    if actual_norm == expected_key:
        return AssertionResult(
            passed=True,
            message=f"Key format correct: {expected_key}",
            expected=expected_key,
            actual=actual_norm,
        )
    else:
        return AssertionResult(
            passed=False,
            message=(
                f"{context}: key format mismatch. "
                f"Expected '{expected_key}', got '{actual_norm}'"
            ),
            expected=expected_key,
            actual=actual_norm,
        )


def assert_no_duplicates(
    items: list[Any],
    key_func=None,
    context: str = "",
) -> AssertionResult:
    """
    Assert no duplicate items.
    
    Args:
        items: List to check
        key_func: Optional function to extract key from item
    """
    if key_func:
        keys = [key_func(item) for item in items]
    else:
        keys = items
        
    unique = set(keys)
    if len(unique) == len(keys):
        return AssertionResult(
            passed=True,
            message=f"No duplicates found ({len(keys)} items)",
        )
    else:
        from collections import Counter
        counts = Counter(keys)
        dups = {k: v for k, v in counts.items() if v > 1}
        return AssertionResult(
            passed=False,
            message=f"{context}: found duplicates: {dups}",
            expected="no duplicates",
            actual=dups,
        )


def assert_stats_match(
    stats,
    expected: dict[str, int],
    context: str = "",
) -> AssertionResult:
    """
    Assert CLI stats match expected values.
    
    Args:
        stats: SyncStats object
        expected: Dict of stat_name -> expected_value
    """
    mismatches = []
    for stat_name, expected_val in expected.items():
        actual_val = getattr(stats, stat_name, None)
        if actual_val != expected_val:
            mismatches.append(
                f"{stat_name}: expected {expected_val}, got {actual_val}"
            )
            
    if not mismatches:
        return AssertionResult(
            passed=True,
            message=f"Stats match: {expected}",
            expected=expected,
        )
    else:
        return AssertionResult(
            passed=False,
            message=f"{context}: stats mismatch: {'; '.join(mismatches)}",
            expected=expected,
            actual={k: getattr(stats, k, None) for k in expected.keys()},
        )


def assert_value_preserved(
    before: str | None,
    after: str | None,
    context: str = "",
) -> AssertionResult:
    """Assert value was preserved (not cleared or changed)."""
    before_norm = str(before).strip() if before else ""
    after_norm = str(after).strip() if after else ""
    
    if before_norm == after_norm:
        return AssertionResult(
            passed=True,
            message=f"Value preserved: '{before_norm}'",
        )
    else:
        return AssertionResult(
            passed=False,
            message=f"{context}: value changed from '{before_norm}' to '{after_norm}'",
            expected=before_norm,
            actual=after_norm,
        )


def assert_no_scrambling(
    expected_positions: dict[tuple[int, str], str],
    read_func,
    context: str = "",
) -> AssertionResult:
    """
    Assert no data scrambling occurred.
    
    Args:
        expected_positions: Dict of (row, col) -> expected_value
        read_func: Function(row, col) -> actual_value
    """
    mismatches = []
    for (row, col), expected in expected_positions.items():
        actual = read_func(row, col)
        actual_norm = str(actual).strip() if actual else ""
        expected_norm = str(expected).strip() if expected else ""
        
        if actual_norm != expected_norm:
            mismatches.append(f"({row},{col}): expected '{expected_norm}', got '{actual_norm}'")
            
    if not mismatches:
        return AssertionResult(
            passed=True,
            message=f"No scrambling: {len(expected_positions)} positions verified",
        )
    else:
        return AssertionResult(
            passed=False,
            message=f"{context}: data scrambling detected: {mismatches[:5]}",
            expected=expected_positions,
            actual=mismatches,
        )


# Convenience wrapper that raises on failure
def require(result: AssertionResult):
    """Raise AssertionError if result failed."""
    if not result.passed:
        raise AssertionError(result.message)
    return result
