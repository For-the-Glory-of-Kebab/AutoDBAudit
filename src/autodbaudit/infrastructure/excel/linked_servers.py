"""
Linked Servers Sheet Module.

Handles the Linked Servers worksheet for linked server security audit.
"""

from __future__ import annotations

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    apply_boolean_styling,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
)


__all__ = ["LinkedServerSheetMixin", "LINKED_SERVER_CONFIG"]


LINKED_SERVER_COLUMNS = (
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Linked Server", 25, Alignments.LEFT),
    ColumnDef("Product", 15, Alignments.LEFT),
    ColumnDef("Provider", 18, Alignments.LEFT),
    ColumnDef("Data Source", 35, Alignments.LEFT),
    ColumnDef("RPC Out", 10, Alignments.CENTER),
    ColumnDef("Purpose", 40, Alignments.LEFT, is_manual=True),
)

LINKED_SERVER_CONFIG = SheetConfig(name="Linked Servers", columns=LINKED_SERVER_COLUMNS)


class LinkedServerSheetMixin(BaseSheetMixin):
    """Mixin for Linked Servers sheet functionality."""
    
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
    ) -> None:
        """
        Add a linked server row.
        
        Linked servers can pose security risks - RPC Out should be reviewed.
        
        Args:
            server_name: Server hostname
            instance_name: SQL Server instance name
            linked_server_name: Name of the linked server
            product: Product type (SQL Server, Oracle, etc.)
            provider: OLE DB provider name
            data_source: Connection data source
            rpc_out: Whether RPC Out is enabled (security consideration)
        """
        if self._linked_server_sheet is None:
            self._linked_server_sheet = self._ensure_sheet(LINKED_SERVER_CONFIG)
        
        ws = self._linked_server_sheet
        
        data = [
            server_name,
            instance_name or "(Default)",
            linked_server_name,
            product or "",
            provider or "",
            data_source or "",
            None,  # RPC Out - styled separately
            "",    # Purpose
        ]
        
        row = self._write_row(ws, LINKED_SERVER_CONFIG, data)
        
        apply_boolean_styling(ws.cell(row=row, column=7), rpc_out)
