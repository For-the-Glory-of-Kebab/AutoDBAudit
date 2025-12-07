"""
Actions Sheet Module.

Handles the Actions worksheet for remediation tracking.
This sheet provides a centralized list of all findings that
require action, with tracking for assignment and resolution.

Sheet Purpose:
    - Track all security findings requiring remediation
    - Assign findings to responsible parties
    - Track resolution status and dates
    - Document exceptions with justification

Columns:
    - ID: Unique action item number
    - Server/Instance: Location of finding
    - Category: Type (SA Account, Configuration, Backup, etc.)
    - Finding: Description of the issue
    - Risk Level: Critical/High/Medium/Low
    - Recommendation: Suggested remediation
    - Status: Open/Closed/Exception
    - Found Date: When the finding was discovered (auto)
    - Assigned To: Person responsible (manual)
    - Due Date: Target resolution date (manual)
    - Resolution Date: When actually resolved (manual)
    - Resolution Notes: How it was resolved (manual)

Visual Features:
    - Risk level color coding (Critical=dark red, High=red)
    - Status icons (Open=pending, Closed=checkmark)
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


ACTION_COLUMNS = (
    ColumnDef("ID", 6, Alignments.CENTER),
    ColumnDef("Server", 16, Alignments.LEFT),
    ColumnDef("Instance", 14, Alignments.LEFT),
    ColumnDef("Category", 16, Alignments.LEFT),
    ColumnDef("Finding", 40, Alignments.LEFT),
    ColumnDef("Risk Level", 10, Alignments.CENTER),
    ColumnDef("Recommendation", 45, Alignments.LEFT),
    ColumnDef("Status", 12, Alignments.CENTER, is_status=True),
    ColumnDef("Found Date", 12, Alignments.CENTER),  # Auto-populated
    ColumnDef("Assigned To", 18, Alignments.LEFT, is_manual=True),
    ColumnDef("Due Date", 12, Alignments.CENTER, is_manual=True),
    ColumnDef("Resolution Date", 14, Alignments.CENTER, is_manual=True),
    ColumnDef("Resolution Notes", 45, Alignments.LEFT, is_manual=True),
)

ACTION_CONFIG = SheetConfig(name="Actions", columns=ACTION_COLUMNS)


class ActionSheetMixin(BaseSheetMixin):
    """
    Mixin for Actions sheet functionality.
    
    Provides the `add_action` method to record remediation items.
    Each action is automatically numbered and timestamped with
    the date it was discovered.
    
    Action Lifecycle:
        1. Finding discovered during audit → "Open" status
        2. Assigned to responsible party
        3. Due date set for remediation
        4. Issue resolved → "Closed" status + Resolution Date
        
    OR:
        3. Exception granted → "Exception" status + justification
    
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
        recommendation: str,
        status: str = "Open",
        found_date: datetime | None = None,
    ) -> None:
        """
        Add an action item row with automatic ID and date.
        
        Each action is auto-assigned an incremental ID and
        the found date defaults to the current date.
        
        Args:
            server_name: Server hostname
            instance_name: SQL Server instance name
            category: Finding category for grouping:
                - "SA Account" - SA security issues
                - "Configuration" - sp_configure issues
                - "Backup" - Backup compliance issues
                - "Login" - Login security issues
                - "Permissions" - Permission issues
            finding: Clear description of the issue found
            risk_level: Severity of the finding:
                - "Critical" - Immediate action required
                - "High" - Address within 7 days
                - "Medium" - Address within 30 days
                - "Low" - Address when possible
            recommendation: Specific steps to remediate
            status: Current status:
                - "Open" - Not yet addressed
                - "Closed" - Remediated
                - "Exception" - Risk accepted
            found_date: When finding was discovered (defaults to now)
        
        Example:
            writer.add_action(
                server_name="SQLPROD01",
                instance_name="",
                category="SA Account",
                finding="SA account is enabled and not renamed",
                risk_level="Critical",
                recommendation="Disable SA and rename to '$@'",
            )
        """
        # Lazy-initialize the worksheet
        if self._action_sheet is None:
            self._action_sheet = self._ensure_sheet(ACTION_CONFIG)
        
        ws = self._action_sheet
        
        # Auto-assign ID and date
        self._action_count += 1
        if found_date is None:
            found_date = datetime.now()
        
        # Prepare row data
        data = [
            str(self._action_count),
            server_name,
            instance_name or "(Default)",
            category,
            finding,
            risk_level.title(),
            recommendation,
            None,  # Status - styled separately
            format_date(found_date),  # Found Date (auto)
            "",    # Assigned To (manual)
            "",    # Due Date (manual)
            "",    # Resolution Date (manual)
            "",    # Resolution Notes (manual)
        ]
        
        row = self._write_row(ws, ACTION_CONFIG, data)
        
        # Style status cell with icon
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
        elif status_lower == "exception":
            status_cell.value = f"{Icons.EXCEPTION} Exception"
            status_cell.fill = Fills.EXCEPTION
            status_cell.font = Fonts.WARN
        
        # Style risk level cell with severity colors
        risk_cell = ws.cell(row=row, column=6)
        risk_lower = risk_level.lower()
        if risk_lower == "critical":
            risk_cell.fill = Fills.CRITICAL
            risk_cell.font = Fonts.CRITICAL
        elif risk_lower == "high":
            risk_cell.fill = Fills.FAIL
            risk_cell.font = Fonts.FAIL
        elif risk_lower == "medium":
            risk_cell.fill = Fills.WARN
            risk_cell.font = Fonts.WARN
