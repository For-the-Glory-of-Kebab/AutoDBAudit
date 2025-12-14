"""
SA Account Sheet Module.

Handles the SA Account worksheet for SA account security audit.
Merges Server column when multiple instances on same server.
"""

from __future__ import annotations

from openpyxl.styles import PatternFill

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    apply_boolean_styling,
    apply_status_styling,
    merge_server_cells,
    SERVER_GROUP_COLORS,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
    ACTION_COLUMN,
    apply_action_needed_styling,
)


__all__ = ["SAAccountSheetMixin", "SA_ACCOUNT_CONFIG"]


SA_ACCOUNT_COLUMNS = (
    ACTION_COLUMN,  # Column A: Action indicator
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Status", 12, Alignments.CENTER, is_status=True),
    ColumnDef("Is Disabled", 12, Alignments.CENTER),
    ColumnDef("Is Renamed", 12, Alignments.CENTER),
    ColumnDef("Current Name", 20, Alignments.LEFT),
    ColumnDef("Default DB", 15, Alignments.LEFT),
    ColumnDef("Justification", 40, Alignments.LEFT, is_manual=True),  # FAIL + justification = exception
    ColumnDef("Notes", 35, Alignments.LEFT, is_manual=True),
)

SA_ACCOUNT_CONFIG = SheetConfig(name="SA Account", columns=SA_ACCOUNT_COLUMNS)


class SAAccountSheetMixin(BaseSheetMixin):
    """Mixin for SA Account sheet with server grouping."""
    
    _sa_account_sheet = None
    _sa_last_server: str = ""
    _sa_server_start_row: int = 2
    _sa_server_idx: int = 0
    
    def add_sa_account(
        self,
        server_name: str,
        instance_name: str,
        is_disabled: bool,
        is_renamed: bool,
        current_name: str,
        default_db: str,
    ) -> None:
        """Add SA account audit row."""
        if self._sa_account_sheet is None:
            self._sa_account_sheet = self._ensure_sheet(SA_ACCOUNT_CONFIG)
            self._sa_last_server = ""
            self._sa_server_start_row = 2
            self._sa_server_idx = 0
            self._add_sa_dropdowns()
        
        ws = self._sa_account_sheet
        current_row = self._row_counters[SA_ACCOUNT_CONFIG.name]
        
        # Check if server changed
        if server_name != self._sa_last_server:
            if self._sa_last_server:
                self._merge_sa_server(ws)
                self._sa_server_idx += 1
            
            self._sa_server_start_row = current_row
            self._sa_last_server = server_name
        
        # Get color
        color_main, color_light = SERVER_GROUP_COLORS[
            self._sa_server_idx % len(SERVER_GROUP_COLORS)
        ]
        
        # Determine compliance status
        if is_disabled and is_renamed:
            status = "pass"
            self._increment_pass()
        elif is_disabled or is_renamed:
            status = "warn"
            self._increment_warn()
        else:
            status = "fail"
            self._increment_issue()
        
        # Action indicator will be set after write
        data = [
            None,  # Action indicator (column A)
            server_name,
            instance_name or "(Default)",
            None,  # Status
            None,  # Is Disabled
            None,  # Is Renamed
            current_name,
            default_db or "",
            "",    # Remediation Notes
        ]
        
        row = self._write_row(ws, SA_ACCOUNT_CONFIG, data)
        
        # Apply action indicator (column A) - show ⏳ for non-pass items
        needs_action = status != "pass"
        apply_action_needed_styling(ws.cell(row=row, column=1), needs_action)
        
        # Apply light color to Server, Instance, Current Name, Default DB (shifted +1)
        fill = PatternFill(start_color=color_light, end_color=color_light, fill_type="solid")
        for col in [2, 3, 7, 8]:  # Server=2, Instance=3, CurrentName=7, DefaultDB=8
            ws.cell(row=row, column=col).fill = fill
        
        # Apply status styling (shifted +1)
        apply_status_styling(ws.cell(row=row, column=4), status)  # Status is now col 4
        apply_boolean_styling(ws.cell(row=row, column=5), is_disabled)  # Is Disabled is now col 5
        apply_boolean_styling(ws.cell(row=row, column=6), is_renamed)  # Is Renamed is now col 6
    
    def _merge_sa_server(self, ws) -> None:
        """Merge Server cells for current server group."""
        current_row = self._row_counters[SA_ACCOUNT_CONFIG.name]
        if current_row > self._sa_server_start_row:
            color_main, _ = SERVER_GROUP_COLORS[
                self._sa_server_idx % len(SERVER_GROUP_COLORS)
            ]
            merge_server_cells(
                ws,
                server_col=2,  # Server is now column B (shifted +1)
                start_row=self._sa_server_start_row,
                end_row=current_row - 1,
                server_name=self._sa_last_server,
                is_alt=True,
            )
            merged = ws.cell(row=self._sa_server_start_row, column=2)  # Column B
            merged.fill = PatternFill(
                start_color=color_main, end_color=color_main, fill_type="solid"
            )
    
    def _finalize_sa_accounts(self) -> None:
        """Finalize SA Account sheet - merge remaining server group."""
        if self._sa_account_sheet and self._sa_last_server:
            self._merge_sa_server(self._sa_account_sheet)
    
    def _add_sa_dropdowns(self) -> None:
        """Add dropdown validations for status columns."""
        from autodbaudit.infrastructure.excel.base import add_dropdown_validation
        
        ws = self._sa_account_sheet
        # Status column (D) - column 4 (shifted +1 from C)
        add_dropdown_validation(ws, "D", ["PASS", "FAIL", "WARN"])
        # Is Disabled column (E) - column 5 (shifted +1 from D)
        add_dropdown_validation(ws, "E", ["✓", "✗"])
        # Is Renamed column (F) - column 6 (shifted +1 from E)
        add_dropdown_validation(ws, "F", ["✓", "✗"])
