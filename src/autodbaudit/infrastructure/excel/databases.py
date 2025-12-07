"""
Databases Sheet Module.

Handles the Databases worksheet for database properties audit.
"""

from __future__ import annotations

from typing import Any

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    apply_boolean_styling,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
    format_size_mb,
)


__all__ = ["DatabaseSheetMixin", "DATABASE_CONFIG"]


DATABASE_COLUMNS = (
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Database", 25, Alignments.LEFT),
    ColumnDef("Owner", 20, Alignments.LEFT),
    ColumnDef("Recovery", 12, Alignments.CENTER),
    ColumnDef("State", 12, Alignments.CENTER),
    ColumnDef("Size (MB)", 12, Alignments.RIGHT),
    ColumnDef("Trustworthy", 12, Alignments.CENTER),
    ColumnDef("Notes", 40, Alignments.LEFT, is_manual=True),
)

DATABASE_CONFIG = SheetConfig(name="Databases", columns=DATABASE_COLUMNS)


class DatabaseSheetMixin(BaseSheetMixin):
    """Mixin for Databases sheet functionality."""
    
    _database_sheet = None
    
    def add_database(
        self,
        server_name: str,
        instance_name: str,
        database_name: str,
        owner: str,
        recovery_model: str,
        state: str,
        size_mb: Any,
        is_trustworthy: bool,
    ) -> None:
        """
        Add a database row.
        
        Args:
            server_name: Server hostname
            instance_name: SQL Server instance name
            database_name: Name of the database
            owner: Database owner
            recovery_model: Recovery model (FULL, SIMPLE, BULK_LOGGED)
            state: Database state (ONLINE, OFFLINE, etc.)
            size_mb: Total database size in MB
            is_trustworthy: Whether TRUSTWORTHY is enabled (security risk)
        """
        if self._database_sheet is None:
            self._database_sheet = self._ensure_sheet(DATABASE_CONFIG)
        
        ws = self._database_sheet
        
        data = [
            server_name,
            instance_name or "(Default)",
            database_name,
            owner or "",
            recovery_model,
            state,
            format_size_mb(size_mb),
            None,  # Trustworthy - styled separately
            "",    # Notes
        ]
        
        row = self._write_row(ws, DATABASE_CONFIG, data)
        
        # Trustworthy ON is a security concern (invert=True)
        apply_boolean_styling(ws.cell(row=row, column=8), is_trustworthy, invert=True)
