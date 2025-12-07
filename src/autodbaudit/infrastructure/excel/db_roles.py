"""
Database Roles Sheet Module.

Handles the Database Roles worksheet for per-database role membership audit.
"""

from __future__ import annotations

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    Fills,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
)


__all__ = ["DBRoleSheetMixin", "DB_ROLE_CONFIG"]


DB_ROLE_COLUMNS = (
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Database", 20, Alignments.LEFT),
    ColumnDef("Role", 20, Alignments.LEFT),
    ColumnDef("Member", 25, Alignments.LEFT),
    ColumnDef("Member Type", 18, Alignments.LEFT),
    ColumnDef("Justification", 50, Alignments.LEFT, is_manual=True),
)

DB_ROLE_CONFIG = SheetConfig(name="Database Roles", columns=DB_ROLE_COLUMNS)

# Sensitive database roles that require review
SENSITIVE_DB_ROLES = frozenset({
    "db_owner",
    "db_securityadmin",
    "db_accessadmin",
    "db_backupoperator",
    "db_ddladmin",
})


class DBRoleSheetMixin(BaseSheetMixin):
    """Mixin for Database Roles sheet functionality."""
    
    _db_role_sheet = None
    
    def add_db_role_member(
        self,
        server_name: str,
        instance_name: str,
        database_name: str,
        role_name: str,
        member_name: str,
        member_type: str,
    ) -> None:
        """
        Add a database role membership row.
        
        Args:
            server_name: Server hostname
            instance_name: SQL Server instance name
            database_name: Database containing the role
            role_name: Database role name
            member_name: Name of the role member
            member_type: Type of member (User, Role, etc.)
        """
        if self._db_role_sheet is None:
            self._db_role_sheet = self._ensure_sheet(DB_ROLE_CONFIG)
        
        ws = self._db_role_sheet
        
        data = [
            server_name,
            instance_name or "(Default)",
            database_name,
            role_name,
            member_name,
            member_type,
            "",  # Justification
        ]
        
        row = self._write_row(ws, DB_ROLE_CONFIG, data)
        
        # Highlight sensitive roles
        if role_name.lower() in SENSITIVE_DB_ROLES:
            for col in range(1, 6):
                ws.cell(row=row, column=col).fill = Fills.WARN
