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
)


__all__ = ["SAAccountSheetMixin", "SA_ACCOUNT_CONFIG"]


SA_ACCOUNT_COLUMNS = (
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Status", 12, Alignments.CENTER, is_status=True),
    ColumnDef("Is Disabled", 12, Alignments.CENTER),
    ColumnDef("Is Renamed", 12, Alignments.CENTER),
    ColumnDef("Current Name", 20, Alignments.LEFT),
    ColumnDef("Default DB", 15, Alignments.LEFT),
    ColumnDef("Remediation Notes", 45, Alignments.LEFT, is_manual=True),
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
        
        data = [
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
        
        # Apply light color to Server, Instance, Current Name, Default DB
        fill = PatternFill(start_color=color_light, end_color=color_light, fill_type="solid")
        for col in [1, 2, 6, 7]:
            ws.cell(row=row, column=col).fill = fill
        
        # Apply status styling
        apply_status_styling(ws.cell(row=row, column=3), status)
        apply_boolean_styling(ws.cell(row=row, column=4), is_disabled)
        apply_boolean_styling(ws.cell(row=row, column=5), is_renamed)
    
    def _merge_sa_server(self, ws) -> None:
        """Merge Server cells for current server group."""
        current_row = self._row_counters[SA_ACCOUNT_CONFIG.name]
        if current_row > self._sa_server_start_row:
            color_main, _ = SERVER_GROUP_COLORS[
                self._sa_server_idx % len(SERVER_GROUP_COLORS)
            ]
            merge_server_cells(
                ws,
                server_col=1,
                start_row=self._sa_server_start_row,
                end_row=current_row - 1,
                server_name=self._sa_last_server,
                is_alt=True,
            )
            merged = ws.cell(row=self._sa_server_start_row, column=1)
            merged.fill = PatternFill(
                start_color=color_main, end_color=color_main, fill_type="solid"
            )
    
    def _finalize_sa_accounts(self) -> None:
        """Finalize SA Account sheet - merge remaining server group."""
        if self._sa_account_sheet and self._sa_last_server:
            self._merge_sa_server(self._sa_account_sheet)
