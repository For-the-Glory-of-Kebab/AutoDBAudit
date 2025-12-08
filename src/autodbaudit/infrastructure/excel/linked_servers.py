"""
Linked Servers Sheet Module.

Handles the Linked Servers worksheet for linked server security audit.
Uses ServerGroupMixin for server/instance grouping.
Includes login mapping info, impersonate settings, and data validation dropdowns.
"""

from __future__ import annotations

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    Fills,
    Fonts,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
    LAST_REVISED_COLUMN,
)
from autodbaudit.infrastructure.excel.server_group import ServerGroupMixin


__all__ = ["LinkedServerSheetMixin", "LINKED_SERVER_CONFIG"]


LINKED_SERVER_COLUMNS = (
    ColumnDef("Server", 16, Alignments.LEFT),
    ColumnDef("Instance", 14, Alignments.LEFT),
    ColumnDef("Linked Server", 22, Alignments.LEFT),
    ColumnDef("Provider", 16, Alignments.LEFT),
    ColumnDef("Data Source", 28, Alignments.LEFT),
    ColumnDef("RPC Out", 10, Alignments.CENTER),
    ColumnDef("Local Login", 16, Alignments.LEFT),
    ColumnDef("Remote Login", 16, Alignments.LEFT),
    ColumnDef("Impersonate", 12, Alignments.CENTER),
    ColumnDef("Risk", 12, Alignments.CENTER),
    ColumnDef("Purpose", 30, Alignments.LEFT, is_manual=True),
    LAST_REVISED_COLUMN,
)

LINKED_SERVER_CONFIG = SheetConfig(name="Linked Servers", columns=LINKED_SERVER_COLUMNS)


class LinkedServerSheetMixin(ServerGroupMixin, BaseSheetMixin):
    """Mixin for Linked Servers sheet with server/instance grouping."""
    
    _linked_server_sheet = None
    _ls_validations_added = False
    
    def add_linked_server(
        self,
        server_name: str,
        instance_name: str,
        linked_server_name: str,
        product: str,  # Kept for API compatibility, not used
        provider: str,
        data_source: str,
        rpc_out: bool,
        local_login: str = "",
        remote_login: str = "",
        impersonate: bool = False,
        risk_level: str = "",
    ) -> None:
        """Add a linked server row with login mapping and security info."""
        if self._linked_server_sheet is None:
            self._linked_server_sheet = self._ensure_sheet(LINKED_SERVER_CONFIG)
            self._init_grouping(self._linked_server_sheet, LINKED_SERVER_CONFIG)
            self._add_linked_server_validations()
        
        ws = self._linked_server_sheet
        
        # Track grouping and get row color
        row_color = self._track_group(server_name, instance_name, LINKED_SERVER_CONFIG.name)
        
        data = [
            server_name,
            instance_name or "(Default)",
            linked_server_name,
            provider or "",
            data_source or "",
            None,       # RPC Out - styled
            local_login or "",
            remote_login or "",
            None,       # Impersonate - styled
            None,       # Risk - styled
            "",         # Purpose
            "",         # Last Revised
        ]
        
        row = self._write_row(ws, LINKED_SERVER_CONFIG, data)
        
        self._apply_row_color(row, row_color, data_cols=[1, 2, 3, 4, 5, 7, 8], ws=ws)
        
        # RPC Out column (6) with dropdown value
        rpc_cell = ws.cell(row=row, column=6)
        if rpc_out:
            rpc_cell.value = "✓ Yes"
            rpc_cell.fill = Fills.PASS
            rpc_cell.font = Fonts.PASS
        else:
            rpc_cell.value = "✗ No"
            rpc_cell.fill = Fills.WARN
        
        # Impersonate column (9) with dropdown value
        impersonate_cell = ws.cell(row=row, column=9)
        if impersonate:
            impersonate_cell.value = "✓ Yes"
            impersonate_cell.fill = Fills.WARN  # Worth noting
        else:
            impersonate_cell.value = "✗ No"
            impersonate_cell.fill = Fills.PASS
        
        # Risk column (10) with dropdown value
        risk_cell = ws.cell(row=row, column=10)
        if risk_level == "HIGH_PRIVILEGE":
            risk_cell.value = "🔴 High"
            risk_cell.fill = Fills.FAIL
            risk_cell.font = Fonts.FAIL
            self._increment_warn()
        else:
            risk_cell.value = "🟢 Normal"
            risk_cell.fill = Fills.PASS
    
    def _add_linked_server_validations(self) -> None:
        """Add dropdown data validation to choice columns."""
        if self._ls_validations_added:
            return
        
        from autodbaudit.infrastructure.excel.base import add_dropdown_validation
        
        ws = self._linked_server_sheet
        # RPC Out dropdown (column 6)
        add_dropdown_validation(ws, "F", ["✓ Yes", "✗ No"])
        # Impersonate dropdown (column 9)
        add_dropdown_validation(ws, "I", ["✓ Yes", "✗ No"])
        # Risk dropdown (column 10)
        add_dropdown_validation(ws, "J", ["🟢 Normal", "🔴 HIGH"])
        
        self._ls_validations_added = True
    
    def _finalize_linked_servers(self) -> None:
        """Finalize linked servers sheet - merge remaining groups."""
        if self._linked_server_sheet:
            self._finalize_grouping(LINKED_SERVER_CONFIG.name)
