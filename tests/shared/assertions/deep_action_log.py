"""
Deep Action Log Assertions - Content-based verification.

This module provides comprehensive action log assertions that verify:
- Specific entry existence
- Entry content (description, entity key)
- Timestamp validity
- Cross-reference with Excel Actions sheet
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence


@dataclass
class ActionLogEntry:
    """Complete action log entry data."""

    id: int
    audit_id: int
    entity_key: str
    action_type: str
    description: str | None
    sheet_name: str | None
    timestamp: datetime | None

    @property
    def is_fix(self) -> bool:
        return "fixed" in self.action_type.lower()

    @property
    def is_regression(self) -> bool:
        return "regression" in self.action_type.lower()

    @property
    def is_exception(self) -> bool:
        return "exception" in self.action_type.lower()

    @property
    def is_new(self) -> bool:
        return "new" in self.action_type.lower()


class DeepActionLogAssertions:
    """
    Deep, content-based action log assertions.

    These verify actual entry content, not just counts.
    """

    @staticmethod
    def get_entries_from_db(
        conn,
        audit_id: int,
        action_type: str | None = None,
    ) -> list[ActionLogEntry]:
        """
        Get all action log entries for an audit.

        Args:
            conn: Database connection
            audit_id: Audit run ID
            action_type: Filter by action type (optional)

        Returns:
            List of ActionLogEntry objects
        """
        query = """
            SELECT 
                id, sync_run_id, entity_key, action_type, 
                description, sheet_name, action_date
            FROM action_log 
            WHERE sync_run_id = ?
        """
        params = [audit_id]

        if action_type:
            query += " AND action_type LIKE ?"
            params.append(f"%{action_type}%")

        cursor = conn.execute(query, params)

        entries = []
        for row in cursor.fetchall():
            entries.append(
                ActionLogEntry(
                    id=row[0],
                    audit_id=row[1],
                    entity_key=row[2] or "",
                    action_type=row[3] or "",
                    description=row[4],
                    sheet_name=row[5],
                    timestamp=row[6] if isinstance(row[6], datetime) else None,
                )
            )

        return entries

    @staticmethod
    def find_entry_by_entity(
        entries: Sequence[ActionLogEntry],
        entity_pattern: str,
        action_type: str | None = None,
    ) -> ActionLogEntry | None:
        """
        Find entry matching entity pattern.

        Args:
            entries: List of entries to search
            entity_pattern: Regex pattern for entity key
            action_type: Required action type (optional)

        Returns:
            First matching entry or None
        """
        for entry in entries:
            if re.search(entity_pattern, entry.entity_key, re.IGNORECASE):
                if action_type is None:
                    return entry
                if action_type.lower() in entry.action_type.lower():
                    return entry

        return None

    @staticmethod
    def assert_entry_exists(
        entries: Sequence[ActionLogEntry],
        entity_pattern: str,
        action_type: str,
    ) -> ActionLogEntry:
        """
        Assert action log entry exists and return it.

        Raises AssertionError with details if not found.
        """
        entry = DeepActionLogAssertions.find_entry_by_entity(
            entries, entity_pattern, action_type
        )

        if entry is None:
            existing = [f"{e.entity_key}:{e.action_type}" for e in entries[:10]]
            raise AssertionError(
                f"No action log entry for entity '{entity_pattern}' "
                f"with action '{action_type}'.\n"
                f"Existing entries: {existing}"
            )

        return entry

    @staticmethod
    def assert_entry_content(
        entry: ActionLogEntry,
        description_contains: str | None = None,
        sheet_name: str | None = None,
        has_timestamp: bool = True,
    ) -> None:
        """
        Assert entry has expected content.

        Args:
            entry: Entry to verify
            description_contains: Required substring in description
            sheet_name: Required sheet name
            has_timestamp: Whether timestamp must exist
        """
        errors = []

        if description_contains:
            desc = entry.description or ""
            if description_contains.lower() not in desc.lower():
                errors.append(
                    f"Description should contain '{description_contains}', "
                    f"got '{desc}'"
                )

        if sheet_name:
            if entry.sheet_name != sheet_name:
                errors.append(
                    f"Sheet should be '{sheet_name}', got '{entry.sheet_name}'"
                )

        if has_timestamp and entry.timestamp is None:
            errors.append("Missing timestamp")

        if errors:
            raise AssertionError(
                f"Entry {entry.id} validation failed:\n" + "\n".join(errors)
            )

    @staticmethod
    def assert_no_duplicate_entries(
        entries: Sequence[ActionLogEntry],
        entity_pattern: str,
        action_type: str,
    ) -> None:
        """Assert only one entry exists for entity/action combination."""
        matches = [
            e
            for e in entries
            if re.search(entity_pattern, e.entity_key, re.IGNORECASE)
            and action_type.lower() in e.action_type.lower()
        ]

        if len(matches) > 1:
            raise AssertionError(
                f"Duplicate entries for '{entity_pattern}' / '{action_type}': "
                f"found {len(matches)} entries"
            )

    @staticmethod
    def assert_fix_entry_complete(
        conn,
        audit_id: int,
        entity_pattern: str,
        expected_description: str | None = None,
    ) -> ActionLogEntry:
        """
        Assert complete FIXED entry with all required fields.

        This is a comprehensive check for a FIXED action log entry.
        """
        entries = DeepActionLogAssertions.get_entries_from_db(conn, audit_id)

        entry = DeepActionLogAssertions.assert_entry_exists(
            entries, entity_pattern, "Fixed"
        )

        DeepActionLogAssertions.assert_entry_content(
            entry,
            description_contains=expected_description,
            has_timestamp=True,
        )

        DeepActionLogAssertions.assert_no_duplicate_entries(
            entries, entity_pattern, "Fixed"
        )

        return entry

    @staticmethod
    def assert_regression_entry_complete(
        conn,
        audit_id: int,
        entity_pattern: str,
    ) -> ActionLogEntry:
        """Assert complete REGRESSION entry."""
        entries = DeepActionLogAssertions.get_entries_from_db(conn, audit_id)

        entry = DeepActionLogAssertions.assert_entry_exists(
            entries, entity_pattern, "Regression"
        )

        DeepActionLogAssertions.assert_entry_content(entry, has_timestamp=True)

        return entry

    @staticmethod
    def assert_exception_entry_complete(
        conn,
        audit_id: int,
        entity_pattern: str,
        justification_contains: str | None = None,
    ) -> ActionLogEntry:
        """Assert complete Exception Documented entry."""
        entries = DeepActionLogAssertions.get_entries_from_db(conn, audit_id)

        entry = DeepActionLogAssertions.assert_entry_exists(
            entries, entity_pattern, "Exception"
        )

        DeepActionLogAssertions.assert_entry_content(
            entry,
            description_contains=justification_contains,
            has_timestamp=True,
        )

        return entry
