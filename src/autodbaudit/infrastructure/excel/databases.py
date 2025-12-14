"""
Databases Sheet Module.

Handles the Databases worksheet for database properties audit.
Uses ServerGroupMixin for server/instance grouping.
Enhanced with visual icons for State and Recovery Model.
"""

from __future__ import annotations

from typing import Any

from openpyxl.styles import PatternFill

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
    format_size_mb,
    ACTION_COLUMN,
    apply_action_needed_styling,
)
from autodbaudit.infrastructure.excel.server_group import ServerGroupMixin


__all__ = ["DatabaseSheetMixin", "DATABASE_CONFIG"]


DATABASE_COLUMNS = (
    ACTION_COLUMN,  # Column A: Action indicator (⏳ needs attention)
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Database", 25, Alignments.LEFT),
    ColumnDef("Owner", 20, Alignments.LEFT),
    ColumnDef("Recovery", 14, Alignments.CENTER),
    ColumnDef("State", 14, Alignments.CENTER),
    ColumnDef("Data (MB)", 12, Alignments.RIGHT),
    ColumnDef("Log (MB)", 12, Alignments.RIGHT),
    ColumnDef("Trustworthy", 12, Alignments.CENTER),
    ColumnDef("Justification", 35, Alignments.LEFT, is_manual=True),
    ColumnDef("Notes", 30, Alignments.LEFT, is_manual=True),
)

DATABASE_CONFIG = SheetConfig(name="Databases", columns=DATABASE_COLUMNS)


class DatabaseSheetMixin(ServerGroupMixin, BaseSheetMixin):
    """Mixin for Databases sheet with server/instance grouping."""
    
    _database_sheet = None
    
    def add_database(
        self,
        server_name: str,
        instance_name: str,
        database_name: str,
        owner: str,
        recovery_model: str,
        state: str,
        data_size_mb: Any,
        log_size_mb: Any,
        is_trustworthy: bool,
    ) -> None:
        """Add a database row."""
        if self._database_sheet is None:
            self._database_sheet = self._ensure_sheet(DATABASE_CONFIG)
            self._init_grouping(self._database_sheet, DATABASE_CONFIG)
            self._add_database_dropdowns()
        
        ws = self._database_sheet
        
        # Track grouping and get row color
        row_color = self._track_group(server_name, instance_name, DATABASE_CONFIG.name)
        
        # Determine if action needed (TRUSTWORTHY ON for user DBs)
        system_dbs = {"master", "msdb", "model", "tempdb"}
        is_system_db = database_name.lower() in system_dbs
        needs_action = is_trustworthy and not is_system_db
        
        data = [
            None,  # Action indicator (column A)
            server_name,
            instance_name or "(Default)",
            database_name,
            owner or "",
            None,  # Recovery - styled separately
            None,  # State - styled separately
            format_size_mb(data_size_mb),
            format_size_mb(log_size_mb),
            None,  # Trustworthy
            "",    # Justification
            "",    # Notes
        ]
        
        row = self._write_row(ws, DATABASE_CONFIG, data)
        
        # Apply action indicator (column 1)
        apply_action_needed_styling(ws.cell(row=row, column=1), needs_action)
        
        # Apply row color to data columns (shifted +1 for action column)
        self._apply_row_color(row, row_color, data_cols=[2, 3, 4, 5, 8, 9], ws=ws)
        
        # Style Recovery Model column (column 6, shifted +1)
        recovery_cell = ws.cell(row=row, column=6)
        recovery_lower = (recovery_model or "").lower()
        if "full" in recovery_lower:
            recovery_cell.value = "🛡️ Full"
            recovery_cell.fill = Fills.PASS
        elif "bulk" in recovery_lower:
            recovery_cell.value = "📦 Bulk-Logged"
            recovery_cell.fill = PatternFill(start_color="FFF3E0", end_color="FFF3E0", fill_type="solid")
        elif "simple" in recovery_lower:
            recovery_cell.value = "⚡ Simple"
            recovery_cell.fill = Fills.WARN
        else:
            recovery_cell.value = recovery_model or ""
        
        # Style State column (column 7, shifted +1)
        state_cell = ws.cell(row=row, column=7)
        state_lower = (state or "").lower()
        if "online" in state_lower:
            state_cell.value = "✓ Online"
            state_cell.fill = Fills.PASS
            state_cell.font = Fonts.PASS
        elif "offline" in state_lower:
            state_cell.value = "⛔ Offline"
            state_cell.fill = Fills.WARN
            state_cell.font = Fonts.WARN
        elif "restoring" in state_lower:
            state_cell.value = "🔄 Restoring"
            state_cell.fill = PatternFill(start_color="E3F2FD", end_color="E3F2FD", fill_type="solid")
        elif "recovering" in state_lower:
            state_cell.value = "⏳ Recovering"
            state_cell.fill = PatternFill(start_color="FFF3E0", end_color="FFF3E0", fill_type="solid")
        elif "suspect" in state_lower:
            state_cell.value = "⚠️ Suspect"
            state_cell.fill = Fills.FAIL
            state_cell.font = Fonts.FAIL
        elif "emergency" in state_lower:
            state_cell.value = "🚨 Emergency"
            state_cell.fill = Fills.FAIL
            state_cell.font = Fonts.FAIL
        else:
            state_cell.value = state or ""
        
        # Trustworthy column (column 10, shifted +1)
        # is_system_db already calculated above for needs_action
        trustworthy_cell = ws.cell(row=row, column=10)
        if is_system_db:
            # System DB - show value but don't mark as pass/fail
            trustworthy_cell.value = "✓ ON" if is_trustworthy else "✗ OFF"
            trustworthy_cell.fill = PatternFill(start_color="E8EAF6", end_color="E8EAF6", fill_type="solid")
        else:
            # User DB - TRUSTWORTHY ON is a security concern
            apply_boolean_styling(trustworthy_cell, is_trustworthy, invert=True)
    
    def _finalize_databases(self) -> None:
        """Finalize databases sheet - merge remaining groups."""
        if self._database_sheet:
            self._finalize_grouping(DATABASE_CONFIG.name)
    
    def _add_database_dropdowns(self) -> None:
        """Add dropdown validations for status columns."""
        from autodbaudit.infrastructure.excel.base import add_dropdown_validation
        
        ws = self._database_sheet
        # Recovery Model column (E) - column 5
        add_dropdown_validation(ws, "E", ["🛡️ Full", "📦 Bulk-Logged", "⚡ Simple"])
        # State column (F) - column 6
        add_dropdown_validation(ws, "F", ["✓ Online", "⛔ Offline", "🔄 Restoring", "⏳ Recovering", "⚠️ Suspect", "🚨 Emergency"])
        # Trustworthy column (I) - column 9
        add_dropdown_validation(ws, "I", ["✓ ON", "✗ OFF", "✓", "✗"])
