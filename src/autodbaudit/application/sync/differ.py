"""
Differ - Detect changes between annotation states.

Compares old and new annotations to detect:
- New exceptions added
- Exceptions removed
- Documentation changes
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ExceptionChangeType(str, Enum):
    """Type of exception change."""

    ADDED = "added"
    REMOVED = "removed"
    UPDATED = "updated"


@dataclass(frozen=True, slots=True)
class ExceptionChange:
    """
    Represents a single exception change for action logging.

    Replaces the old dict-based approach with a proper dataclass.
    """

    full_key: str  # entity_type|entity_key
    entity_type: str
    entity_key: str
    justification: str
    change_type: ExceptionChangeType
    review_status: str = ""


@dataclass
class DiffResult:
    """Result of comparing two annotation states."""

    exceptions_added: int = 0
    exceptions_removed: int = 0
    exceptions_updated: int = 0
    docs_added: int = 0
    docs_updated: int = 0
    docs_removed: int = 0

    # Full exception change details for action logging
    exception_changes: list[ExceptionChange] = field(default_factory=list)

    # Legacy key lists (for backward compat if needed)
    added_keys: list[str] = field(default_factory=list)
    removed_keys: list[str] = field(default_factory=list)
    updated_keys: list[str] = field(default_factory=list)

    def __len__(self) -> int:
        """Total number of exception changes."""
        return len(self.exception_changes)

    def __iter__(self):
        """Iterate over exception changes."""
        return iter(self.exception_changes)


def has_justification(fields: dict[str, Any]) -> bool:
    """Check if annotation has a justification (exception)."""
    just = fields.get("justification", "")
    if just and str(just).strip():
        return True

    # Check review_status for "Exception"
    status = fields.get("review_status", "")
    if status and "exception" in str(status).lower():
        return True

    return False


def has_documentation(fields: dict[str, Any]) -> bool:
    """Check if annotation has non-exception documentation."""
    notes = fields.get("notes", "")
    if notes and str(notes).strip():
        return True

    # Check date fields
    for key in ["last_reviewed", "revised_date"]:
        val = fields.get(key, "")
        if val and str(val).strip():
            return True

    return False


def diff_annotations(
    old_annotations: dict[str, dict],
    new_annotations: dict[str, dict],
    discrepant_keys: set[str] | None = None,
) -> DiffResult:
    """
    Compare old and new annotations to detect changes.

    Args:
        old_annotations: Previous state {key: {field: value}}
        new_annotations: Current state {key: {field: value}}
        discrepant_keys: Optional set of keys that are FAIL/WARN

    Returns:
        DiffResult with change counts and full exception details
    """
    result = DiffResult()

    all_keys = set(old_annotations.keys()) | set(new_annotations.keys())

    for full_key in all_keys:
        old_fields = old_annotations.get(full_key, {})
        new_fields = new_annotations.get(full_key, {})

        # Parse entity_type|entity_key from full_key
        parts = full_key.split("|", 1)
        entity_type = parts[0] if len(parts) >= 1 else ""
        entity_key = parts[1] if len(parts) == 2 else ""

        # Check if this is a discrepant item
        is_discrepant = discrepant_keys is None or full_key.lower() in discrepant_keys

        old_has_just = has_justification(old_fields)
        new_has_just = has_justification(new_fields)

        old_has_docs = has_documentation(old_fields)
        new_has_docs = has_documentation(new_fields)

        # Exception changes (only for discrepant items)
        if is_discrepant:
            new_just = str(new_fields.get("justification", "")).strip()
            new_status = str(new_fields.get("review_status", "")).strip()

            if new_has_just and not old_has_just:
                result.exceptions_added += 1
                result.added_keys.append(full_key)
                result.exception_changes.append(
                    ExceptionChange(
                        full_key=full_key,
                        entity_type=entity_type,
                        entity_key=entity_key,
                        justification=new_just,
                        change_type=ExceptionChangeType.ADDED,
                        review_status=new_status,
                    )
                )
            elif old_has_just and not new_has_just:
                result.exceptions_removed += 1
                result.removed_keys.append(full_key)
                result.exception_changes.append(
                    ExceptionChange(
                        full_key=full_key,
                        entity_type=entity_type,
                        entity_key=entity_key,
                        justification="",  # Cleared
                        change_type=ExceptionChangeType.REMOVED,
                        review_status="",
                    )
                )
            elif old_has_just and new_has_just:
                # Check if justification changed
                old_just = str(old_fields.get("justification", "")).strip()
                if old_just != new_just:
                    result.exceptions_updated += 1
                    result.updated_keys.append(full_key)
                    result.exception_changes.append(
                        ExceptionChange(
                            full_key=full_key,
                            entity_type=entity_type,
                            entity_key=entity_key,
                            justification=new_just,
                            change_type=ExceptionChangeType.UPDATED,
                            review_status=new_status,
                        )
                    )

        # Documentation changes (count only, no ExceptionChange)
        if new_has_docs and not old_has_docs:
            result.docs_added += 1
        elif old_has_docs and not new_has_docs:
            result.docs_removed += 1
        elif old_has_docs and new_has_docs:
            if old_fields.get("notes") != new_fields.get("notes"):
                result.docs_updated += 1

    logger.info(
        "Diff: +%d/-%d exceptions, docs +%d/-%d",
        result.exceptions_added,
        result.exceptions_removed,
        result.docs_added,
        result.docs_removed,
    )

    return result
