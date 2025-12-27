"""
Orphaned Users Sheet Module.

Handles the Orphaned Users worksheet for orphaned database user audit.
Uses ServerGroupMixin for server/instance grouping.

This sheet consolidates all non-system orphaned users for quick review.
Orphaned users are database users without matching server logins.


UUID Support (v3):
    - Column A: Hidden UUID for stable row identification
    - All other columns shifted +1 from original positions
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
    STATUS_COLUMN,
    LAST_REVIEWED_COLUMN,
    apply_action_needed_styling,
)
from autodbaudit.infrastructure.excel.server_group import ServerGroupMixin


__all__ = ["OrphanedUserSheetMixin", "ORPHANED_USER_CONFIG"]


ORPHANED_USER_COLUMNS = (
    ACTION_COLUMN,  # Column B: Action indicator (A=UUID hidden)
    ColumnDef("Server", 18, Alignments.LEFT),  # Column C
    ColumnDef("Instance", 15, Alignments.LEFT),  # Column D
    ColumnDef("Database", 20, Alignments.LEFT),  # Column E
    ColumnDef("User Name", 25, Alignments.LEFT),  # Column F
    ColumnDef("Type", 16, Alignments.CENTER),  # Column G
    ColumnDef("Status", 14, Alignments.CENTER),  # Column H
    STATUS_COLUMN,  # Review Status dropdown
    ColumnDef("Justification", 45, Alignments.LEFT, is_manual=True),
    LAST_REVIEWED_COLUMN,
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
            self._orphaned_user_sheet = self._ensure_sheet_with_uuid(
                ORPHANED_USER_CONFIG
            )
            self._init_grouping(self._orphaned_user_sheet, ORPHANED_USER_CONFIG)
            self._add_orphan_dropdowns()

        ws = self._orphaned_user_sheet

        # Track grouping and get row color
        row_color = self._track_group(
            server_name,
            instance_name,
            ORPHANED_USER_CONFIG.name,
            database_name=database_name,
        )

        # Format user type with icon
        type_lower = (user_type or "").lower()
        type_display = user_type
        if "windows" in type_lower:
            type_display = "🪟 Windows"
        elif "sql" in type_lower:
            type_display = "🔑 SQL"

        data = [
            None,  # Action indicator (column B) - all orphaned users need action
            server_name,  # Column C
            instance_name or "(Default)",
            database_name,
            user_name,
            type_display,
            None,  # Status - styled separately
            "",  # Justification
            "",  # Last Revised
        ]

        row, _ = self._write_row_with_uuid(ws, ORPHANED_USER_CONFIG, data)

        # All orphaned users need action - show ⏳
        apply_action_needed_styling(ws.cell(row=row, column=2), True)

        # Apply row color to data columns (A=UUID, B=Action, C=Server, D=Instance, E=Database, F=UserName, G=Type, H=Status)
        self._apply_row_color(row, row_color, data_cols=[3, 4, 5, 6, 7], ws=ws)

        # Style Status column (column H = 8)
        status_cell = ws.cell(row=row, column=8)
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
            self._orphaned_user_sheet = self._ensure_sheet_with_uuid(
                ORPHANED_USER_CONFIG
            )
            self._init_grouping(self._orphaned_user_sheet, ORPHANED_USER_CONFIG)
            self._add_orphan_dropdowns()

        ws = self._orphaned_user_sheet

        # Track grouping and get row color
        row_color = self._track_group(
            server_name, instance_name, ORPHANED_USER_CONFIG.name
        )

        data = [
            None,  # Action indicator (column B) - no action needed
            server_name,  # Column C
            instance_name or "(Default)",
            "(All Databases)",  # Database
            "— None Found —",  # User Name
            "",  # Type
            None,  # Status - styled separately
            "",  # Justification
            "",  # Last Revised
        ]

        row, _ = self._write_row_with_uuid(ws, ORPHANED_USER_CONFIG, data)

        # Apply row color to data columns
        self._apply_row_color(row, row_color, data_cols=[3, 4, 5, 6, 7], ws=ws)

        # Style Status column (column H = 8) as PASS (no orphans = good)
        status_cell = ws.cell(row=row, column=8)
        status_cell.value = "✅ None Found"
        status_cell.fill = Fills.PASS
        status_cell.font = Fonts.PASS

    def _finalize_orphaned_users(self) -> None:
        """Finalize orphaned users sheet - merge remaining groups."""
        if self._orphaned_user_sheet:
            self._finalize_grouping(ORPHANED_USER_CONFIG.name)
            self._finalize_sheet_with_uuid(self._orphaned_user_sheet)

    def _add_orphan_dropdowns(self) -> None:
        """Add dropdown validations for status columns."""
        from autodbaudit.infrastructure.excel.base import (
            add_dropdown_validation,
            add_review_status_conditional_formatting,
            STATUS_VALUES,
        )

        ws = self._orphaned_user_sheet
        # Type column (F) - column 6 (shifted +1 from E)
        add_dropdown_validation(ws, "G", ["🪟 Windows", "🔑 SQL"])
        # Status column (G) - column 7 (shifted +1 from F)
        add_dropdown_validation(ws, "H", ["⚠️ Orphaned", "✓ Fixed", "❌ Removed"])
        # Review Status column (H) - column 8
        add_dropdown_validation(ws, "I", STATUS_VALUES.all())
        add_review_status_conditional_formatting(ws, "I")
