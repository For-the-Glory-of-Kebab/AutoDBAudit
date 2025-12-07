"""
Actions Sheet Module.

Handles the Actions worksheet for remediation tracking.
"""

from __future__ import annotations

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    Fills,
    Icons,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
)


__all__ = ["ActionSheetMixin", "ACTION_CONFIG"]


ACTION_COLUMNS = (
    ColumnDef("ID", 8, Alignments.CENTER),
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Category", 18, Alignments.LEFT),
    ColumnDef("Finding", 45, Alignments.LEFT),
    ColumnDef("Risk Level", 12, Alignments.CENTER),
    ColumnDef("Recommendation", 50, Alignments.LEFT),
    ColumnDef("Status", 15, Alignments.CENTER, is_status=True),
    ColumnDef("Assigned To", 20, Alignments.LEFT, is_manual=True),
    ColumnDef("Due Date", 12, Alignments.CENTER, is_manual=True),
    ColumnDef("Resolution Notes", 50, Alignments.LEFT, is_manual=True),
)

ACTION_CONFIG = SheetConfig(name="Actions", columns=ACTION_COLUMNS)


class ActionSheetMixin(BaseSheetMixin):
    """Mixin for Actions sheet functionality."""
    
    _action_sheet = None
    _action_count: int = 0
    
    def add_action(
        self,
        server_name: str,
        instance_name: str,
        category: str,
        finding: str,
        risk_level: str,
        recommendation: str,
        status: str = "Open",
    ) -> None:
        """
        Add an action item row.
        
        Args:
            server_name: Server hostname
            instance_name: SQL Server instance name
            category: Category of the finding (SA Account, Configuration, etc.)
            finding: Description of the finding
            risk_level: Risk level (Critical, High, Medium, Low)
            recommendation: Recommended remediation steps
            status: Current status (Open, Closed)
        """
        if self._action_sheet is None:
            self._action_sheet = self._ensure_sheet(ACTION_CONFIG)
        
        ws = self._action_sheet
        
        self._action_count += 1
        
        data = [
            str(self._action_count),
            server_name,
            instance_name or "(Default)",
            category,
            finding,
            risk_level.title(),
            recommendation,
            None,  # Status - styled separately
            "",    # Assigned To
            "",    # Due Date
            "",    # Resolution Notes
        ]
        
        row = self._write_row(ws, ACTION_CONFIG, data)
        
        # Style status cell
        status_cell = ws.cell(row=row, column=8)
        if status.lower() == "open":
            status_cell.value = f"{Icons.PENDING} Open"
            status_cell.fill = Fills.WARN
        else:
            status_cell.value = f"{Icons.PASS} Closed"
            status_cell.fill = Fills.PASS
        
        # Style risk level cell
        risk_cell = ws.cell(row=row, column=6)
        if risk_level.lower() == "critical":
            risk_cell.fill = Fills.CRITICAL
        elif risk_level.lower() == "high":
            risk_cell.fill = Fills.FAIL
        elif risk_level.lower() == "medium":
            risk_cell.fill = Fills.WARN
