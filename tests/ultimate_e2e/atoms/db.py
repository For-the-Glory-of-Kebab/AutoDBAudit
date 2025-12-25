"""
Database operation atoms.

Atoms for database read/write/verify operations in tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .base import Atom, AtomResult, AssertionAtom

if TYPE_CHECKING:
    from ..conftest import TestContext


@dataclass
class VerifyDbAnnotationAtom(AssertionAtom):
    """Verify an annotation exists in the database."""

    entity_type: str
    entity_key: str
    field: str
    expected_value: str | None = None

    @property
    def name(self) -> str:
        return f"VerifyDbAnnotation({self.entity_type}/{self.entity_key})"

    def _assert(self, ctx: "TestContext") -> None:
        cursor = ctx.conn.execute(
            """
            SELECT justification, notes, review_status, last_reviewed
            FROM row_annotations
            WHERE entity_type = ? AND entity_key LIKE ?
            """,
            (self.entity_type, f"%{self.entity_key}%"),
        )
        row = cursor.fetchone()

        assert (
            row is not None
        ), f"No annotation found for {self.entity_type}/{self.entity_key}"

        if self.expected_value is not None:
            field_map = {
                "justification": row[0],
                "notes": row[1],
                "review_status": row[2],
                "last_reviewed": row[3],
            }
            actual = field_map.get(self.field)
            assert (
                actual == self.expected_value
            ), f"Expected {self.field}='{self.expected_value}', got '{actual}'"


@dataclass
class VerifyDbFindingAtom(AssertionAtom):
    """Verify a finding exists in the database with expected status."""

    entity_key: str
    expected_status: str | None = None

    @property
    def name(self) -> str:
        return f"VerifyDbFinding({self.entity_key})"

    def _assert(self, ctx: "TestContext") -> None:
        cursor = ctx.conn.execute(
            "SELECT status FROM findings WHERE entity_key LIKE ?",
            (f"%{self.entity_key}%",),
        )
        row = cursor.fetchone()

        assert row is not None, f"No finding found for {self.entity_key}"

        if self.expected_status:
            assert (
                row[0] == self.expected_status
            ), f"Expected status={self.expected_status}, got {row[0]}"


@dataclass
class InsertFindingAtom(Atom):
    """Insert a mock finding into the database."""

    entity_key: str
    finding_type: str
    status: str = "FAIL"
    description: str = "Test finding"

    @property
    def name(self) -> str:
        return f"InsertFinding({self.entity_key})"

    def execute(self, ctx: "TestContext") -> AtomResult:
        from autodbaudit.infrastructure.sqlite.schema import save_finding

        try:
            save_finding(
                connection=ctx.conn,
                audit_run_id=ctx.run_id,
                instance_id=ctx.instance_id,
                entity_key=self.entity_key,
                finding_type=self.finding_type,
                entity_name=self.entity_key.split("|")[-1],
                status=self.status,
                finding_description=self.description,
            )
            ctx.conn.commit()
            return AtomResult(self.name, True, f"Inserted {self.status} finding")
        except Exception as e:
            return AtomResult(self.name, False, str(e))


@dataclass
class CountActionLogAtom(Atom):
    """Count action log entries."""

    @property
    def name(self) -> str:
        return "CountActionLog"

    def execute(self, ctx: "TestContext") -> AtomResult:
        count = ctx.count_action_log()
        return AtomResult(self.name, True, f"{count} entries", {"count": count})


@dataclass
class GetActionLogEntriesAtom(Atom):
    """Get all action log entries for inspection."""

    @property
    def name(self) -> str:
        return "GetActionLogEntries"

    def execute(self, ctx: "TestContext") -> AtomResult:
        entries = ctx.get_action_log_entries()
        return AtomResult(
            self.name,
            True,
            f"{len(entries)} entries",
            {"entries": entries},
        )
