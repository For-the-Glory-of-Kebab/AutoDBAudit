"""
Excel operation atoms.

Atoms for reading/writing Excel files in tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .base import Atom, AtomResult

if TYPE_CHECKING:
    from ..conftest import TestContext


@dataclass
class AddAnnotationAtom(Atom):
    """Add an annotation to an Excel cell."""

    sheet: str
    row: int
    column: str
    value: str

    @property
    def name(self) -> str:
        return f"AddAnnotation({self.sheet}[{self.row}].{self.column})"

    def execute(self, ctx: "TestContext") -> AtomResult:
        success = ctx.add_annotation_to_excel(
            self.sheet, self.row, self.column, self.value
        )
        msg = (
            f"Set {self.column}='{self.value[:20]}...'"
            if success
            else "Failed to add annotation"
        )
        return AtomResult(self.name, success, msg)


@dataclass
class AddExceptionAtom(Atom):
    """Add exception justification (convenience wrapper)."""

    sheet: str
    row: int = 2
    value: str = "Test exception"

    @property
    def name(self) -> str:
        return f"AddException({self.sheet})"

    def execute(self, ctx: "TestContext") -> AtomResult:
        # Most sheets use "Justification", some use "Exception Reason"
        success = ctx.add_annotation_to_excel(
            self.sheet, self.row, "Justification", self.value
        )
        if not success:
            # Try alternate column name
            success = ctx.add_annotation_to_excel(
                self.sheet, self.row, "Exception Reason", self.value
            )
        msg = f"Added exception: '{self.value[:30]}...'" if success else "Failed"
        return AtomResult(self.name, success, msg)


@dataclass
class ReadAnnotationAtom(Atom):
    """Read an annotation from Excel."""

    sheet: str
    row: int
    column: str

    @property
    def name(self) -> str:
        return f"ReadAnnotation({self.sheet}[{self.row}].{self.column})"

    def execute(self, ctx: "TestContext") -> AtomResult:
        value = ctx.read_annotation_from_excel(self.sheet, self.row, self.column)
        return AtomResult(
            self.name,
            True,
            f"Read value: '{value}'",
            {"value": value},
        )


@dataclass
class MarkRowAsFailAtom(Atom):
    """Mark a row as FAIL status in Excel."""

    sheet: str
    row: int = 2

    @property
    def name(self) -> str:
        return f"MarkRowAsFail({self.sheet}[{self.row}])"

    def execute(self, ctx: "TestContext") -> AtomResult:
        success = ctx.mark_row_as_fail(self.sheet, self.row)
        return AtomResult(self.name, success, "Marked as FAIL" if success else "Failed")


@dataclass
class CreateExcelAtom(Atom):
    """Create Excel file with specified sheets."""

    sheet_names: list[str] | None = None

    @property
    def name(self) -> str:
        if self.sheet_names:
            return f"CreateExcel({len(self.sheet_names)} sheets)"
        return "CreateExcel(all sheets)"

    def execute(self, ctx: "TestContext") -> AtomResult:
        from ..sheet_specs import get_data_specs

        if self.sheet_names:
            specs = [s for s in get_data_specs() if s.sheet_name in self.sheet_names]
        else:
            specs = None

        ctx.create_excel_with_specs(specs)
        return AtomResult(self.name, True, f"Created Excel at {ctx.excel_path}")


@dataclass
class ClearAnnotationAtom(Atom):
    """Clear an annotation value (set to empty string)."""

    sheet: str
    row: int
    column: str

    @property
    def name(self) -> str:
        return f"ClearAnnotation({self.sheet}[{self.row}].{self.column})"

    def execute(self, ctx: "TestContext") -> AtomResult:
        success = ctx.add_annotation_to_excel(self.sheet, self.row, self.column, "")
        return AtomResult(self.name, success, "Cleared" if success else "Failed")
