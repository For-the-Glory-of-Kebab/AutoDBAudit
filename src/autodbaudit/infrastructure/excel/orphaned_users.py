"""
Orphaned Users Sheet Module.

Handles the Orphaned Users worksheet for orphaned database user audit.
"""

from __future__ import annotations

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    apply_status_styling,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
)


__all__ = ["OrphanedUserSheetMixin", "ORPHANED_USER_CONFIG"]


ORPHANED_USER_COLUMNS = (
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Database", 20, Alignments.LEFT),
    ColumnDef("User Name", 25, Alignments.LEFT),
    ColumnDef("Type", 18, Alignments.LEFT),
    ColumnDef("Status", 12, Alignments.CENTER, is_status=True),
    ColumnDef("Remediation", 45, Alignments.LEFT, is_manual=True),
)

ORPHANED_USER_CONFIG = SheetConfig(name="Orphaned Users", columns=ORPHANED_USER_COLUMNS)


class OrphanedUserSheetMixin(BaseSheetMixin):
    """Mixin for Orphaned Users sheet functionality."""
    
    _orphaned_user_sheet = None
    
    def add_orphaned_user(
        self,
        server_name: str,
        instance_name: str,
        database_name: str,
        user_name: str,
        user_type: str,
    ) -> None:
        """
        Add an orphaned user row.
        
        Orphaned users are database users without a corresponding server login.
        They represent a security risk and should be remediated.
        
        Args:
            server_name: Server hostname
            instance_name: SQL Server instance name
            database_name: Database containing the orphaned user
            user_name: Orphaned user name
            user_type: Type of user (SQL User, Windows User, etc.)
        """
        if self._orphaned_user_sheet is None:
            self._orphaned_user_sheet = self._ensure_sheet(ORPHANED_USER_CONFIG)
        
        ws = self._orphaned_user_sheet
        
        # All orphaned users are issues
        self._increment_issue()
        
        data = [
            server_name,
            instance_name or "(Default)",
            database_name,
            user_name,
            user_type,
            None,  # Status - styled separately
            "",    # Remediation
        ]
        
        row = self._write_row(ws, ORPHANED_USER_CONFIG, data)
        
        apply_status_styling(ws.cell(row=row, column=6), "fail")
