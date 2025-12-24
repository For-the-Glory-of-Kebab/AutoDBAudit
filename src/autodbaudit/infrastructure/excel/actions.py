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
    ColumnDef("Category", 20, Alignments.LEFT),  # Wider category
    ColumnDef("Finding", 50, Alignments.LEFT_WRAP),  # Wider finding description
    ColumnDef("Risk Level", 12, Alignments.CENTER),
    ColumnDef("Change Description", 55, Alignments.LEFT_WRAP),  # Wider change desc
    ColumnDef(
        "Change Type", 15, Alignments.CENTER, is_status=True
    ),  # Fixed/Regressed/New
    ColumnDef(
        "Detected Date", 15, Alignments.CENTER
    ),  # When change detected (editable)
    ColumnDef("Notes", 60, Alignments.LEFT_WRAP, is_manual=True),  # Much wider notes
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
        found_date: datetime | None = None,
        notes: str | None = None,
        action_id: int | None = None,  # DB action ID for row matching
    ) -> None:
        """
        Add a changelog entry row with DB ID for row matching.

        Args:
            server_name: Server hostname
            instance_name: SQL Server instance name
            category: Finding category for grouping
            finding: Description of what changed
            risk_level: Severity (Low for fixes, High for regressions)
            recommendation: Change description (what happened)
            status: Change type (Closed for fixes, Open for issues)
            found_date: When change was detected
            notes: (Optional) User notes/commentary
            action_id: (Optional) Database action ID for Excel row matching
        """
        import logging

        logger = logging.getLogger(__name__)

        ws = self._ensure_sheet(ACTION_CONFIG)

        # Use DB ID if provided, otherwise auto-generate
        if action_id is not None:
            display_id = str(action_id)
        else:
            self._action_count += 1
            display_id = str(self._action_count)

        # Determine status icon
        status_icon = Icons.PENDING
        if status.lower() in ("closed", "fixed", "resolved"):
            status_icon = Icons.PASS  # ✅
        elif status.lower() in ("exception", "warn"):
            status_icon = Icons.PASS

        logger.info(
            "ActionWriter: Adding row ID=%s: %s | %s",
            display_id,
            category,
            finding,
        )

        if found_date is None:
            found_date = datetime.now()

        data = [
            display_id,
            server_name,
            instance_name or "(Default)",
            category,
            finding,
            risk_level.title(),
            recommendation,  # Change Description
            None,  # Change Type - styled separately
            format_date(found_date),  # Detected Date
            notes or "",  # Notes - empty string if None
        ]

        row = self._write_row(ws, ACTION_CONFIG, data)

        # Style Change Type cell (column 8) - handle all status types
        status_cell = ws.cell(row=row, column=8)
        status_lower = (
            status.lower().replace("✓", "").replace("⚠", "").replace("⏳", "").strip()
        )

        if status_lower == "fixed":
            status_cell.value = f"{Icons.PASS} Fixed"
            status_cell.fill = Fills.PASS
            status_cell.font = Fonts.PASS
        elif status_lower == "exception":
            status_cell.value = f"{Icons.PASS} Exception"
            status_cell.fill = Fills.PASS
            status_cell.font = Fonts.PASS
        elif status_lower == "regression":
            status_cell.value = f"{Icons.FAIL} Regression"
            status_cell.fill = Fills.FAIL
            status_cell.font = Fonts.FAIL
        elif status_lower == "closed":
            status_cell.value = f"{Icons.PASS} Closed"
            status_cell.fill = Fills.PASS
            status_cell.font = Fonts.PASS
        else:  # open, pending, or anything else
            status_cell.value = f"{Icons.PENDING} Open"
            status_cell.fill = Fills.WARN
            status_cell.font = Fonts.WARN

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
        add_dropdown_validation(
            ws,
            "D",
            [
                "SA Account",
                "Configuration",
                "Backup",
                "Login",
                "Permissions",
                "Service",
                "Database",
                "Other",
            ],
        )
        # Risk Level column (F) - column 6
        add_dropdown_validation(ws, "F", ["Low", "Medium", "High"])
        # Change Type column (H) - column 8
        add_dropdown_validation(
            ws, "H", ["⏳ Open", "✓ Fixed", "✓ Exception", "❌ Regression", "✓ Closed"]
        )

        # --- Add Conditional Formatting for dynamic styling ---
        self._add_action_conditional_formatting()

    def _add_action_conditional_formatting(self) -> None:
        """Add Conditional Formatting rules for Risk Level and Change Type columns."""
        from openpyxl.formatting.rule import FormulaRule
        from openpyxl.styles import PatternFill, Font

        ws = self._action_sheet
        if ws is None:
            return

        # Define fills and fonts for CF
        pass_fill = PatternFill(
            start_color="C8E6C9", end_color="C8E6C9", fill_type="solid"
        )  # Green
        pass_font = Font(color="1B5E20", bold=True)
        warn_fill = PatternFill(
            start_color="FFE082", end_color="FFE082", fill_type="solid"
        )  # Yellow/Orange
        warn_font = Font(color="E65100", bold=True)
        fail_fill = PatternFill(
            start_color="FFCDD2", end_color="FFCDD2", fill_type="solid"
        )  # Red
        fail_font = Font(color="B71C1C", bold=True)

        # Risk Level (Column F) - Dynamic based on value
        f_range = f"F2:F{ws.max_row + 500}"

        # Low = Green
        ws.conditional_formatting.add(
            f_range,
            FormulaRule(
                formula=['ISNUMBER(SEARCH("Low",F2))'],
                stopIfTrue=True,
                fill=pass_fill,
                font=pass_font,
            ),
        )
        # Medium = Orange/Yellow
        ws.conditional_formatting.add(
            f_range,
            FormulaRule(
                formula=['ISNUMBER(SEARCH("Medium",F2))'],
                stopIfTrue=True,
                fill=warn_fill,
                font=warn_font,
            ),
        )
        # High = Red
        ws.conditional_formatting.add(
            f_range,
            FormulaRule(
                formula=['ISNUMBER(SEARCH("High",F2))'],
                stopIfTrue=True,
                fill=fail_fill,
                font=fail_font,
            ),
        )
        # Critical = Dark Red (if ever used)
        ws.conditional_formatting.add(
            f_range,
            FormulaRule(
                formula=['ISNUMBER(SEARCH("Critical",F2))'],
                stopIfTrue=True,
                fill=fail_fill,
                font=fail_font,
            ),
        )

        # Change Type (Column H) - Dynamic based on value
        h_range = f"H2:H{ws.max_row + 500}"

        # Fixed/Closed/Exception = Green (Good news)
        ws.conditional_formatting.add(
            h_range,
            FormulaRule(
                formula=[
                    'OR(ISNUMBER(SEARCH("Fixed",H2)), ISNUMBER(SEARCH("Closed",H2)), ISNUMBER(SEARCH("Exception",H2)))'
                ],
                stopIfTrue=True,
                fill=pass_fill,
                font=pass_font,
            ),
        )
        # Regression = Red (Bad news)
        ws.conditional_formatting.add(
            h_range,
            FormulaRule(
                formula=['ISNUMBER(SEARCH("Regression",H2))'],
                stopIfTrue=True,
                fill=fail_fill,
                font=fail_font,
            ),
        )
        # Open/Pending = Orange (Needs attention)
        ws.conditional_formatting.add(
            h_range,
            FormulaRule(
                formula=[
                    'OR(ISNUMBER(SEARCH("Open",H2)), ISNUMBER(SEARCH("Pending",H2)))'
                ],
                stopIfTrue=True,
                fill=warn_fill,
                font=warn_font,
            ),
        )
