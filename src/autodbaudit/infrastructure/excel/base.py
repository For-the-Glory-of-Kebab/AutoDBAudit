"""
Excel Report Base Module.

Contains shared utilities, column definitions, and base classes
for all sheet modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from openpyxl.worksheet.worksheet import Worksheet

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    Fonts,
    Fills,
    Borders,
    Icons,
    apply_header_row,
    freeze_panes,
    add_autofilter,
)

if TYPE_CHECKING:
    from openpyxl import Workbook


__all__ = [
    "ColumnDef",
    "Alignments",
    "SheetConfig",
    "BaseSheetMixin",
    "format_date",
    "format_size_mb",
    "get_sql_year",
    "add_dropdown_validation",
    "LAST_REVISED_COLUMN",
    "ACTION_COLUMN",
    "apply_action_needed_styling",
]


# ============================================================================
# Standard Column Definitions
# ============================================================================

# Reusable "Last Revised" column for sheets with manual annotations
# This tracks when an auditor last reviewed/updated the row
LAST_REVISED_COLUMN = ColumnDef(
    name="Last Revised",
    width=12,
    alignment=Alignments.CENTER,
    is_manual=True,
)

# Reusable "Action" indicator column - shows ⏳ for rows needing attention
ACTION_COLUMN = ColumnDef(
    name="⏳",
    width=4,
    alignment=Alignments.CENTER,
)


def apply_action_needed_styling(cell, needs_action: bool) -> None:
    """
    Apply action-needed indicator to a cell.
    
    Shows ⏳ icon with orange background for rows needing user attention
    (i.e., FAIL/WARN status with no Notes/justification).
    """
    if needs_action:
        cell.value = Icons.PENDING
        cell.fill = Fills.ACTION
        cell.font = Fonts.WARN
        cell.alignment = Alignments.CENTER
    else:
        cell.value = ""


# ============================================================================
# Utility Functions
# ============================================================================

def format_date(value: Any) -> str:
    """Format a date value for display."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    s = str(value)
    return s[:10] if len(s) >= 10 else s


def format_size_mb(value: Any) -> str:
    """Format a size in MB for display."""
    if value is None:
        return ""
    try:
        return f"{float(value):,.1f}"
    except (ValueError, TypeError):
        return str(value)


def get_sql_year(version_major: int) -> str:
    """Convert major version number to SQL Server year."""
    mapping = {
        10: "2008",
        11: "2012",
        12: "2014",
        13: "2016",
        14: "2017",
        15: "2019",
        16: "2022",
        17: "2025",
    }
    return mapping.get(version_major, f"v{version_major}")


def add_dropdown_validation(
    ws: Worksheet,
    column_letter: str,
    options: list[str],
    start_row: int = 2,
    end_row: int = 1000,
) -> None:
    """Add dropdown data validation to a column.
    
    Args:
        ws: The worksheet to add validation to
        column_letter: Column letter (e.g., "E", "F")
        options: List of valid options for the dropdown
        start_row: Starting row (default 2 to skip header)
        end_row: Ending row (default 1000)
    """
    from openpyxl.worksheet.datavalidation import DataValidation
    
    # Create comma-separated list for formula
    formula = '"' + ','.join(options) + '"'
    
    dv = DataValidation(
        type="list",
        formula1=formula,
        showDropDown=False,  # False = show dropdown arrow (counterintuitive)
        allow_blank=True,
    )
    dv.error = f"Please select from: {', '.join(options)}"
    dv.errorTitle = "Invalid Value"
    ws.add_data_validation(dv)
    dv.add(f"{column_letter}{start_row}:{column_letter}{end_row}")


# ============================================================================
# Sheet Configuration
# ============================================================================

@dataclass(frozen=True)
class SheetConfig:
    """Configuration for a worksheet."""
    
    name: str
    columns: tuple[ColumnDef, ...]
    
    @property
    def column_count(self) -> int:
        return len(self.columns)


# ============================================================================
# Base Sheet Mixin
# ============================================================================

class BaseSheetMixin:
    """
    Base class for sheet mixins.
    
    Provides common functionality for sheet creation and data writing.
    Each sheet mixin inherits from this and implements sheet-specific
    add_* methods.
    """
    
    # Subclasses must define these
    wb: Workbook
    _row_counters: dict[str, int]
    _issue_count: int
    _pass_count: int
    _warn_count: int
    
    def _ensure_sheet(self, config: SheetConfig) -> Worksheet:
        """
        Get or create a worksheet with the given configuration.
        
        Creates the sheet if it doesn't exist, applies headers,
        freezes panes, and adds autofilter.
        """
        if config.name in self.wb.sheetnames:
            return self.wb[config.name]
        
        # Remove default "Sheet" if present
        if "Sheet" in self.wb.sheetnames and len(self.wb.sheetnames) == 1:
            del self.wb["Sheet"]
        
        ws = self.wb.create_sheet(config.name)
        apply_header_row(ws, list(config.columns), row=1)
        freeze_panes(ws, row=2, col=1)
        add_autofilter(ws, list(config.columns), header_row=1)
        
        return ws
    
    def _write_row(
        self,
        ws: Worksheet,
        config: SheetConfig,
        data: list[Any],
    ) -> int:
        """
        Write a row of data to a worksheet.
        
        Args:
            ws: Target worksheet
            config: Sheet configuration with column definitions
            data: List of values to write
            
        Returns:
            Row number that was written
        """
        row = self._row_counters[config.name]
        
        for col, (value, col_def) in enumerate(zip(data, config.columns), start=1):
            cell = ws.cell(row=row, column=col)
            cell.value = value
            cell.font = Fonts.DATA
            cell.border = Borders.THIN
            cell.alignment = col_def.alignment
            
            if col_def.is_manual:
                cell.fill = Fills.MANUAL
        
        self._row_counters[config.name] += 1
        return row
    
    def _increment_pass(self) -> None:
        """Increment pass count."""
        self._pass_count += 1
    
    def _increment_warn(self) -> None:
        """Increment warning count."""
        self._warn_count += 1
    
    def _increment_issue(self) -> None:
        """Increment issue count."""
        self._issue_count += 1
