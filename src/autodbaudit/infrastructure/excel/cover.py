"""
Cover Sheet Module.

Handles the Cover worksheet with audit summary and statistics.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from autodbaudit.infrastructure.excel_styles import (
    Fonts,
    Fills,
    Alignments,
    Icons,
)
from autodbaudit.infrastructure.excel.base import BaseSheetMixin

if TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet


__all__ = ["CoverSheetMixin"]


class CoverSheetMixin(BaseSheetMixin):
    """Mixin for Cover sheet functionality."""
    
    _cover_sheet: Worksheet | None = None
    audit_run_id: int | None = None
    organization: str = ""
    started_at: datetime | None = None
    ended_at: datetime | None = None
    
    def set_audit_info(
        self,
        run_id: int,
        organization: str,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
    ) -> None:
        """
        Set audit metadata for the cover sheet.
        
        Args:
            run_id: Audit run identifier
            organization: Organization name
            started_at: Audit start time
            ended_at: Audit end time
        """
        self.audit_run_id = run_id
        self.organization = organization
        self.started_at = started_at
        self.ended_at = ended_at
    
    def create_cover_sheet(self) -> None:
        """Create the cover sheet with audit summary."""
        if "Cover" in self.wb.sheetnames:
            return
        
        # Remove default "Sheet" if present
        if "Sheet" in self.wb.sheetnames:
            del self.wb["Sheet"]
        
        ws = self.wb.create_sheet("Cover", 0)
        self._cover_sheet = ws
        
        # Set column widths
        ws.column_dimensions["A"].width = 5
        ws.column_dimensions["B"].width = 25
        ws.column_dimensions["C"].width = 40
        
        # Title
        ws.merge_cells("B3:C3")
        title_cell = ws["B3"]
        title_cell.value = "SQL SERVER SECURITY AUDIT"
        title_cell.font = Fonts.TITLE
        title_cell.alignment = Alignments.CENTER
        
        # Subtitle (Organization)
        ws.merge_cells("B4:C4")
        subtitle_cell = ws["B4"]
        subtitle_cell.value = self.organization or "Audit Report"
        subtitle_cell.font = Fonts.SUBHEADER
        subtitle_cell.fill = Fills.HEADER
        subtitle_cell.alignment = Alignments.CENTER
        
        # Metadata section
        metadata = [
            ("Audit Run ID", str(self.audit_run_id or "N/A")),
            ("Organization", self.organization or "N/A"),
            ("Started", self.started_at.strftime("%Y-%m-%d %H:%M") if self.started_at else "N/A"),
            ("Ended", self.ended_at.strftime("%Y-%m-%d %H:%M") if self.ended_at else "N/A"),
        ]
        
        row = 6
        for label, value in metadata:
            ws.cell(row=row, column=2).value = label
            ws.cell(row=row, column=2).font = Fonts.DATA_BOLD
            ws.cell(row=row, column=3).value = value
            ws.cell(row=row, column=3).font = Fonts.DATA
            row += 1
        
        # Summary header
        row += 1
        ws.merge_cells(f"B{row}:C{row}")
        summary_cell = ws.cell(row=row, column=2)
        summary_cell.value = "AUDIT SUMMARY"
        summary_cell.font = Fonts.HEADER
        summary_cell.fill = Fills.SUBHEADER
        summary_cell.alignment = Alignments.CENTER
        row += 1
        
        # Summary stats
        summary_items = [
            (f"{Icons.PASS} Passed", self._pass_count, Fills.PASS),
            (f"{Icons.FAIL} Issues", self._issue_count, Fills.FAIL),
            (f"{Icons.WARN} Warnings", self._warn_count, Fills.WARN),
        ]
        
        for label, count, fill in summary_items:
            ws.cell(row=row, column=2).value = label
            ws.cell(row=row, column=2).font = Fonts.DATA
            
            value_cell = ws.cell(row=row, column=3)
            value_cell.value = count
            value_cell.font = Fonts.DATA_BOLD
            if count > 0:
                value_cell.fill = fill
            row += 1
