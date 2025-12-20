"""
Base SheetSpec class definition.

This is the contract for all sheet specifications.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class SheetSpec:
    """
    Specification for a single Excel sheet.

    Attributes:
        sheet_name: Excel worksheet name (must match exactly).
        entity_type: Internal entity type identifier.
        writer_method: Name of the method on EnhancedReportWriter to add data.
        sample_kwargs: Dict of kwargs to pass to writer_method.
        editable_cols: Mapping of Excel header names to DB field names.
        expected_key_pattern: Pattern for entity key (lowercase).
        supports_exceptions: Whether this sheet supports exception tracking.
        has_notes: Whether this sheet has a Notes column.
        has_justification: Whether this sheet has Justification column.
        has_status: Whether this sheet shows compliance status.
        data_row: Row number where data starts (default 2, after headers).
        is_log_sheet: Whether this is a log/action sheet (not auditable).
        is_summary_sheet: Whether this is a summary sheet (Cover).
    """

    sheet_name: str
    entity_type: str
    writer_method: str | None = None
    sample_kwargs: dict[str, Any] = field(default_factory=dict)
    editable_cols: dict[str, str] = field(default_factory=dict)
    expected_key_pattern: str = ""
    supports_exceptions: bool = True
    has_notes: bool = False
    has_justification: bool = True
    has_status: bool = True
    data_row: int = 2
    is_log_sheet: bool = False
    is_summary_sheet: bool = False

    @property
    def has_editable_fields(self) -> bool:
        """Whether this sheet has any user-editable fields."""
        return len(self.editable_cols) > 0

    @property
    def justification_col(self) -> str | None:
        """Get the justification column name if exists."""
        for col_name, field_name in self.editable_cols.items():
            if field_name == "justification" or "justification" in col_name.lower():
                return col_name
        # Check for Exception Reason (Configuration sheet style)
        for col_name in self.editable_cols.keys():
            if "reason" in col_name.lower() or "exception" in col_name.lower():
                return col_name
        return None

    @property
    def notes_col(self) -> str | None:
        """Get the notes column name if exists."""
        for col_name, field_name in self.editable_cols.items():
            if field_name == "notes" or "notes" in col_name.lower():
                return col_name
        return None

    @property
    def review_status_col(self) -> str | None:
        """Get the review status column name if exists."""
        for col_name, field_name in self.editable_cols.items():
            if field_name == "review_status" or "review" in col_name.lower():
                return col_name
        return None

    @property
    def date_col(self) -> str | None:
        """Get the date column name if exists."""
        for col_name, field_name in self.editable_cols.items():
            if "last" in col_name.lower() or "date" in col_name.lower():
                return col_name
        return None


def spec_summary(spec: SheetSpec) -> str:
    """Generate a summary string for a spec."""
    flags = []
    if spec.supports_exceptions:
        flags.append("EXC")
    if spec.has_notes:
        flags.append("NOTES")
    if spec.is_summary_sheet:
        flags.append("SUMMARY")
    if spec.is_log_sheet:
        flags.append("LOG")
    return f"{spec.sheet_name} [{', '.join(flags) or 'DATA'}]"
