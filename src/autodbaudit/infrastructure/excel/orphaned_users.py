"""
Orphaned Users Sheet Module.

Handles the Orphaned Users worksheet for orphaned database user audit.
Uses ServerGroupMixin for server/instance grouping.

This sheet consolidates all non-system orphaned users for quick review.
Orphaned users are database users without matching server logins.
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
    ACTION_COLUMN,
    apply_action_needed_styling,
)
from autodbaudit.infrastructure.excel.server_group import ServerGroupMixin


__all__ = ["OrphanedUserSheetMixin", "ORPHANED_USER_CONFIG"]


ORPHANED_USER_COLUMNS = (
    ACTION_COLUMN,  # Column A: Action indicator
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Database", 20, Alignments.LEFT),
    ColumnDef("User Name", 25, Alignments.LEFT),
    ColumnDef("Type", 16, Alignments.CENTER),
    ColumnDef("Status", 14, Alignments.CENTER),
    ColumnDef("Remediation", 50, Alignments.LEFT, is_manual=True),
)

ORPHANED_USER_CONFIG = SheetConfig(name="Orphaned Users", columns=ORPHANED_USER_COLUMNS)


class OrphanedUserSheetMixin(ServerGroupMixin, BaseSheetMixin):
    """Mixin for Orphaned Users sheet with server/instance grouping."""
    
    _orphaned_user_sheet = None
    
    def add_orphaned_user(
        self,
        server_name: str,
        instance_name: str,
        database_name: str,
        user_name: str,
        user_type: str,
    ) -> None:
        """Add an orphaned user row.
        
        Only non-system orphaned users should be added here.
        System users (dbo, guest, INFORMATION_SCHEMA, sys) are filtered
        at the collection layer.
        """
        if self._orphaned_user_sheet is None:
            self._orphaned_user_sheet = self._ensure_sheet(ORPHANED_USER_CONFIG)
            self._init_grouping(self._orphaned_user_sheet, ORPHANED_USER_CONFIG)
            self._add_orphan_dropdowns()
        
        ws = self._orphaned_user_sheet
        
        # Track grouping and get row color
        row_color = self._track_group(server_name, instance_name, ORPHANED_USER_CONFIG.name)
        
        # Format user type with icon
        type_lower = (user_type or "").lower()
        type_display = user_type
        if "windows" in type_lower:
            type_display = "🪟 Windows"
        elif "sql" in type_lower:
            type_display = "🔑 SQL"
        
        data = [
            None,  # Action indicator (column A) - all orphaned users need action
            server_name,
            instance_name or "(Default)",
            database_name,
            user_name,
            type_display,
            None,  # Status - styled separately  
            "",    # Remediation
        ]
        
        row = self._write_row(ws, ORPHANED_USER_CONFIG, data)
        
        # All orphaned users need action - show ⏳
        apply_action_needed_styling(ws.cell(row=row, column=1), True)
        
        # Apply row color to data columns (shifted +1: Server=2, Instance=3, etc.)
        self._apply_row_color(row, row_color, data_cols=[2, 3, 4, 5, 6], ws=ws)
        
        # Style Status column (column 7, shifted +1 from 6) - orphaned is a warning
        status_cell = ws.cell(row=row, column=7)
        status_cell.value = "⚠️ Orphaned"
        status_cell.fill = Fills.WARN
        status_cell.font = Fonts.WARN
        
        self._increment_warn()
    
    def add_orphaned_user_not_found(
        self,
        server_name: str,
        instance_name: str,
    ) -> None:
        """Add a 'Not Found' row for instances with no orphaned users.
        
        This provides assurance that the instance was scanned.
        """
        if self._orphaned_user_sheet is None:
            self._orphaned_user_sheet = self._ensure_sheet(ORPHANED_USER_CONFIG)
            self._init_grouping(self._orphaned_user_sheet, ORPHANED_USER_CONFIG)
            self._add_orphan_dropdowns()
        
        ws = self._orphaned_user_sheet
        
        # Track grouping and get row color
        row_color = self._track_group(server_name, instance_name, ORPHANED_USER_CONFIG.name)
        
        data = [
            None,  # Action indicator (column A) - no action needed
            server_name,
            instance_name or "(Default)",
            "(All Databases)",  # Database
            "— None Found —",   # User Name
            "",                 # Type
            None,               # Status - styled separately  
            "",                 # Remediation
        ]
        
        row = self._write_row(ws, ORPHANED_USER_CONFIG, data)
        
        # Apply row color to data columns
        self._apply_row_color(row, row_color, data_cols=[2, 3, 4, 5, 6], ws=ws)
        
        # Style Status column as PASS (no orphans = good)
        status_cell = ws.cell(row=row, column=7)
        status_cell.value = "✅ None Found"
        status_cell.fill = Fills.PASS
        status_cell.font = Fonts.PASS
    
    def _finalize_orphaned_users(self) -> None:
        """Finalize orphaned users sheet - merge remaining groups."""
        if self._orphaned_user_sheet:
            self._finalize_grouping(ORPHANED_USER_CONFIG.name)
    
    def _add_orphan_dropdowns(self) -> None:
        """Add dropdown validations for status columns."""
        from autodbaudit.infrastructure.excel.base import add_dropdown_validation
        
        ws = self._orphaned_user_sheet
        # Type column (F) - column 6 (shifted +1 from E)
        add_dropdown_validation(ws, "F", ["🪟 Windows", "🔑 SQL"])
        # Status column (G) - column 7 (shifted +1 from F)
        add_dropdown_validation(ws, "G", ["⚠️ Orphaned", "✓ Fixed", "❌ Removed"])

