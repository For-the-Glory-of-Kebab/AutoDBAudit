"""
Linked Servers Sheet Module.

Handles the Linked Servers worksheet for linked server security audit.
Uses ServerGroupMixin for server/instance grouping.
"""

from __future__ import annotations

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    Fills,
    Fonts,
    apply_boolean_styling,
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
    ColumnDef("Product", 14, Alignments.LEFT),
    ColumnDef("Provider", 16, Alignments.LEFT),
    ColumnDef("Data Source", 30, Alignments.LEFT),
    ColumnDef("RPC Out", 9, Alignments.CENTER),
    ColumnDef("Local Login", 20, Alignments.LEFT),
    ColumnDef("Remote Login", 18, Alignments.LEFT),
    ColumnDef("Risk", 10, Alignments.CENTER),
    ColumnDef("Purpose", 35, Alignments.LEFT, is_manual=True),
    LAST_REVISED_COLUMN,
)

LINKED_SERVER_CONFIG = SheetConfig(name="Linked Servers", columns=LINKED_SERVER_COLUMNS)


class LinkedServerSheetMixin(ServerGroupMixin, BaseSheetMixin):
    """Mixin for Linked Servers sheet with server/instance grouping."""
    
    _linked_server_sheet = None
    
    def add_linked_server(
        self,
        server_name: str,
        instance_name: str,
        linked_server_name: str,
        product: str,
        provider: str,
        data_source: str,
        rpc_out: bool,
        local_login: str = "",
        remote_login: str = "",
        risk_level: str = "",
    ) -> None:
        """Add a linked server row with optional login mapping."""
        if self._linked_server_sheet is None:
            self._linked_server_sheet = self._ensure_sheet(LINKED_SERVER_CONFIG)
            self._init_grouping(self._linked_server_sheet, LINKED_SERVER_CONFIG)
        
        ws = self._linked_server_sheet
        
        # Track grouping and get row color
        row_color = self._track_group(server_name, instance_name, LINKED_SERVER_CONFIG.name)
        
        data = [
            server_name,
            instance_name or "(Default)",
            linked_server_name,
            product or "",
            provider or "",
            data_source or "",
            None,  # RPC Out
            local_login or "",
            remote_login or "",
            risk_level or "",
            "",    # Purpose
            "",    # Last Revised
        ]
        
        row = self._write_row(ws, LINKED_SERVER_CONFIG, data)
        
        self._apply_row_color(row, row_color, data_cols=[1, 2, 3, 4, 5, 6, 8, 9], ws=ws)
        apply_boolean_styling(ws.cell(row=row, column=7), rpc_out)
        
        if risk_level == "HIGH_PRIVILEGE":
            risk_cell = ws.cell(row=row, column=10)
            risk_cell.fill = Fills.FAIL
            risk_cell.font = Fonts.FAIL
            risk_cell.value = "HIGH"
        elif risk_level == "NORMAL":
            ws.cell(row=row, column=10).value = "Normal"
    
    def _finalize_linked_servers(self) -> None:
        """Finalize linked servers sheet - merge remaining groups."""
        if self._linked_server_sheet:
            self._finalize_grouping(LINKED_SERVER_CONFIG.name)
