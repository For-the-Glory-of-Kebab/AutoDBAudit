"""
Server Roles Sheet Module.

Handles the Sensitive Roles worksheet for server role membership audit.
"""

from __future__ import annotations

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    Fills,
    apply_boolean_styling,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
)


__all__ = ["RoleSheetMixin", "ROLE_CONFIG"]


ROLE_COLUMNS = (
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Role", 20, Alignments.LEFT),
    ColumnDef("Member", 30, Alignments.LEFT),
    ColumnDef("Member Type", 20, Alignments.LEFT),
    ColumnDef("Disabled", 10, Alignments.CENTER),
    ColumnDef("Justification", 50, Alignments.LEFT, is_manual=True),
)

ROLE_CONFIG = SheetConfig(name="Sensitive Roles", columns=ROLE_COLUMNS)

# Sensitive server roles that require justification
SENSITIVE_ROLES = frozenset({
    "sysadmin",
    "securityadmin",
    "serveradmin",
    "setupadmin",
    "processadmin",
    "diskadmin",
    "dbcreator",
    "bulkadmin",
})


class RoleSheetMixin(BaseSheetMixin):
    """Mixin for Sensitive Roles sheet functionality."""
    
    _role_sheet = None
    
    def add_role_member(
        self,
        server_name: str,
        instance_name: str,
        role_name: str,
        member_name: str,
        member_type: str,
        is_disabled: bool,
    ) -> None:
        """
        Add a server role membership row.
        
        Args:
            server_name: Server hostname
            instance_name: SQL Server instance name
            role_name: Name of the server role
            member_name: Name of the role member
            member_type: Type of member (SQL Login, Windows Login, etc.)
            is_disabled: Whether the member login is disabled
        """
        if self._role_sheet is None:
            self._role_sheet = self._ensure_sheet(ROLE_CONFIG)
        
        ws = self._role_sheet
        
        data = [
            server_name,
            instance_name or "(Default)",
            role_name,
            member_name,
            member_type,
            None,  # Disabled - styled separately
            "",    # Justification
        ]
        
        row = self._write_row(ws, ROLE_CONFIG, data)
        
        apply_boolean_styling(ws.cell(row=row, column=6), is_disabled)
        
        # Highlight sysadmin members with warning color
        if role_name.lower() == "sysadmin":
            for col in range(1, 6):
                ws.cell(row=row, column=col).fill = Fills.WARN
