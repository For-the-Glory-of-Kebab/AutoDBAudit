"""
Database Users Sheet Module.

Handles the Database Users worksheet for per-database user security matrix.
This sheet provides a comprehensive view of database-level users across
all databases, with security status assessment.

Sheet Purpose:
    - Inventory all database users per database
    - Identify orphaned users (no matching server login)
    - Track user types and login mappings
    - Support security matrix auditing (Requirement 27)

Security Checks:
    - Orphaned users are flagged as FAIL (security risk)
    - Guest accounts enabled are flagged
    - Users without login mappings are reviewed

Visual Features:
    - Alternating row colors per database for readability
    - Status column with Pass/Fail icons
    - Orphaned column with boolean icons
    - Gray background for manual notes column

Related Sheets:
    - Orphaned Users: Dedicated sheet for orphaned user remediation
    - Database Roles: Shows role memberships for these users
"""

from __future__ import annotations

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    Fills,
    apply_boolean_styling,
    apply_status_styling,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
)


__all__ = ["DBUserSheetMixin", "DB_USER_CONFIG"]


DB_USER_COLUMNS = (
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 14, Alignments.LEFT),
    ColumnDef("Database", 18, Alignments.LEFT),
    ColumnDef("User Name", 22, Alignments.LEFT),
    ColumnDef("Type", 16, Alignments.LEFT),
    ColumnDef("Mapped Login", 22, Alignments.LEFT),
    ColumnDef("Orphaned", 10, Alignments.CENTER),
    ColumnDef("Status", 10, Alignments.CENTER, is_status=True),
    ColumnDef("Notes", 35, Alignments.LEFT, is_manual=True),
)

DB_USER_CONFIG = SheetConfig(name="Database Users", columns=DB_USER_COLUMNS)


class DBUserSheetMixin(BaseSheetMixin):
    """
    Mixin for Database Users sheet functionality.
    
    Provides the `add_db_user` method to record database-level users
    with orphan detection. This is part of the security matrix audit
    that spans multiple sheets.
    
    Orphaned User Detection:
        An orphaned user is a database user whose corresponding
        server login has been deleted. These users can't log in
        normally but may still have permissions - a security risk.
    
    Attributes:
        _db_user_sheet: Reference to the Database Users worksheet
        _db_user_last_db: Tracks database name for alternating colors
        _db_user_alt: Toggles alternating background per database
    """
    
    _db_user_sheet = None
    _db_user_last_db: str = ""
    _db_user_alt: bool = False
    
    def add_db_user(
        self,
        server_name: str,
        instance_name: str,
        database_name: str,
        user_name: str,
        user_type: str,
        mapped_login: str | None,
        is_orphaned: bool,
    ) -> None:
        """
        Add a database user row with orphan status assessment.
        
        Each user is automatically assessed:
        - Orphaned users (no matching login) = FAIL status
        - Normal users with valid login mapping = PASS status
        
        Args:
            server_name: Server hostname
            instance_name: SQL Server instance name
            database_name: Database containing the user
            user_name: Database user name
            user_type: Type of database user:
                - "SQL_USER" - Mapped to SQL login
                - "WINDOWS_USER" - Mapped to Windows login
                - "WINDOWS_GROUP" - Mapped to Windows group
                - "DATABASE_ROLE" - Database role
                - "EXTERNAL_USER" - Azure AD user
            mapped_login: Server login this user maps to (None if orphaned)
            is_orphaned: True if user has no corresponding login
        
        Example:
            writer.add_db_user(
                server_name="SQLPROD01",
                instance_name="",
                database_name="ApplicationDB",
                user_name="app_user",
                user_type="SQL_USER",
                mapped_login="app_service",
                is_orphaned=False,
            )
        """
        # Lazy-initialize the worksheet
        if self._db_user_sheet is None:
            self._db_user_sheet = self._ensure_sheet(DB_USER_CONFIG)
            self._db_user_last_db = ""
            self._db_user_alt = False
        
        ws = self._db_user_sheet
        
        # Toggle alternating color when database changes
        # This groups users by database visually
        db_key = f"{server_name}:{instance_name}:{database_name}"
        if db_key != self._db_user_last_db:
            self._db_user_alt = not self._db_user_alt
            self._db_user_last_db = db_key
        
        # Determine security status - orphaned users are issues
        status = "fail" if is_orphaned else "pass"
        if status == "fail":
            self._increment_issue()
        else:
            self._increment_pass()
        
        # Prepare row data
        data = [
            server_name,
            instance_name or "(Default)",
            database_name,
            user_name,
            user_type,
            mapped_login or "",
            None,  # Orphaned - styled separately
            None,  # Status - styled separately
            "",    # Notes (manual)
        ]
        
        row = self._write_row(ws, DB_USER_CONFIG, data)
        
        # Apply alternating background for database grouping
        if self._db_user_alt:
            for col in range(1, len(DB_USER_COLUMNS) + 1):
                cell = ws.cell(row=row, column=col)
                if not DB_USER_COLUMNS[col-1].is_manual and not DB_USER_COLUMNS[col-1].is_status:
                    cell.fill = Fills.SERVER_ALT
        
        # Apply boolean styling - orphaned=True is bad (invert=True)
        apply_boolean_styling(ws.cell(row=row, column=7), is_orphaned, invert=True)
        apply_status_styling(ws.cell(row=row, column=8), status)
