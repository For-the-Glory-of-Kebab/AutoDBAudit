"""
Actions Sheet Module.

Handles the Actions worksheet for audit changelog tracking.
This sheet provides a dated log of all detected CHANGES during
sync operations - what was fixed, what regressed, what's new.

Sheet Purpose:
    - Track all state transitions detected during --sync
    - Record when changes were first detected
    - Allow user notes to document context
    - NOT a TODO list - it's an audit trail of changes

Columns:
    - ID: Unique action item number
    - Server/Instance: Location of finding
    - Category: Type (SA Account, Configuration, Backup, etc.)
    - Finding: Description of the change
    - Risk Level: Severity (Low for fixes, High for regressions)
    - Change Description: What happened (Fixed/Regressed/New)
    - Change Type: Type icon (Closed for fixes, Open for issues)
    - Detected Date: When the change was first discovered (editable)
    - Notes: User commentary (synced each run)

Visual Features:
    - Risk level color coding (Low=green, High=red)
    - Change type icons (Closed=checkmark, Open=pending)
    - Gray background for manual input columns
"""

from __future__ import annotations

from datetime import datetime

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    Fills,
    Icons,
    Fonts,
    Borders,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
    format_date,
)


__all__ = ["ActionSheetMixin", "ACTION_CONFIG"]


# Changelog columns - simplified for audit trail purpose
ACTION_COLUMNS = (
    ColumnDef("ID", 6, Alignments.CENTER),
    ColumnDef("Server", 16, Alignments.LEFT),
    ColumnDef("Instance", 14, Alignments.LEFT),
    ColumnDef("Category", 16, Alignments.LEFT),
    ColumnDef("Finding", 40, Alignments.LEFT),
    ColumnDef("Risk Level", 10, Alignments.CENTER),
    ColumnDef("Change Description", 45, Alignments.LEFT),  # What changed
    ColumnDef("Change Type", 12, Alignments.CENTER, is_status=True),  # Fixed/Regressed/New
    ColumnDef("Detected Date", 12, Alignments.CENTER),  # When change detected (editable)
    ColumnDef("Notes", 45, Alignments.LEFT, is_manual=True),  # User commentary
)

ACTION_CONFIG = SheetConfig(name="Actions", columns=ACTION_COLUMNS)


class ActionSheetMixin(BaseSheetMixin):
    """
    Mixin for Actions sheet functionality.
    
    Provides the `add_action` method to record changelog entries.
    Each change is automatically numbered and timestamped with
    the date it was detected.
    
    Change Types:
        - Fixed: Issue was resolved (FAIL → PASS)
        - Regressed: Issue came back (PASS → FAIL)
        - New: Issue newly detected
    
    Attributes:
        _action_sheet: Reference to the Actions worksheet
        _action_count: Counter for action ID assignment
    """
    
    _action_sheet = None
    _action_count: int = 0
    
    def add_action(
        self,
        server_name: str,
        instance_name: str,
        category: str,
        finding: str,
        risk_level: str,
        recommendation: str,  # Now used as "Change Description"
        status: str = "Open",  # Now used as "Change Type"
        found_date: datetime | None = None,  # Now "Detected Date"
        resolution_notes: str = "",  # Now just "Notes"
    ) -> None:
        """
        Add a changelog entry row with automatic ID and date.
        
        Each entry is auto-assigned an incremental ID and
        the detected date defaults to the current date.
        
        Args:
            server_name: Server hostname
            instance_name: SQL Server instance name
            category: Finding category for grouping
            finding: Description of what changed
            risk_level: Severity (Low=good news, High=bad news)
            recommendation: Change description (what happened)
            status: Change type (Closed for fixes, Open for issues)
            found_date: When change was detected (editable, defaults to now)
            resolution_notes: (Optional) User notes/commentary
        """
        if self._action_sheet is None:
            self._action_sheet = self._ensure_sheet(ACTION_CONFIG)
            self._add_action_dropdowns()
        
        ws = self._action_sheet
        
        # Auto-assign ID and date
        self._action_count += 1
        if found_date is None:
            found_date = datetime.now()
        
        # Prepare row data (10 columns now)
        data = [
            str(self._action_count),
            server_name,
            instance_name or "(Default)",
            category,
            finding,
            risk_level.title(),
            recommendation,       # Change Description
            None,                 # Change Type - styled separately
            format_date(found_date),  # Detected Date
            resolution_notes,     # Notes (user commentary)
        ]
        
        row = self._write_row(ws, ACTION_CONFIG, data)
        
        # Style Change Type cell (column 8)
        status_cell = ws.cell(row=row, column=8)
        status_lower = status.lower()
        if status_lower == "open":
            status_cell.value = f"{Icons.PENDING} Open"
            status_cell.fill = Fills.WARN
            status_cell.font = Fonts.WARN
        elif status_lower == "closed":
            status_cell.value = f"{Icons.PASS} Closed"
            status_cell.fill = Fills.PASS
            status_cell.font = Fonts.PASS
        
        # Style risk level cell with severity colors
        risk_cell = ws.cell(row=row, column=6)
        risk_lower = risk_level.lower()
        if risk_lower == "low":
            # Low risk = good news (usually fixed items)
            risk_cell.fill = Fills.PASS
            risk_cell.font = Fonts.PASS
        elif risk_lower == "high":
            risk_cell.fill = Fills.FAIL
            risk_cell.font = Fonts.FAIL
        elif risk_lower == "medium":
            risk_cell.fill = Fills.WARN
            risk_cell.font = Fonts.WARN
    
    def _add_action_dropdowns(self) -> None:
        """Add dropdown validations for action columns."""
        from autodbaudit.infrastructure.excel.base import add_dropdown_validation
        
        ws = self._action_sheet
        # Category column (D) - column 4
        add_dropdown_validation(ws, "D", ["SA Account", "Configuration", "Backup", "Login", "Permissions", "Service", "Database", "Other"])
        # Risk Level column (F) - column 6
        add_dropdown_validation(ws, "F", ["Low", "Medium", "High"])
        # Change Type column (H) - column 8
        add_dropdown_validation(ws, "H", ["⏳ Open", "✓ Closed"])
