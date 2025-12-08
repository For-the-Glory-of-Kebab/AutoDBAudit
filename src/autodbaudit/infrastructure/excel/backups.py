"""
Backups Sheet Module.

Handles the Backups worksheet for database backup audit.
Uses ServerGroupMixin for server/instance grouping.
"""

from __future__ import annotations

from typing import Any

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    Fills,
    Fonts,
    apply_status_styling,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
    format_date,
    format_size_mb,
)
from autodbaudit.infrastructure.excel.server_group import ServerGroupMixin


__all__ = ["BackupSheetMixin", "BACKUP_CONFIG"]


BACKUP_COLUMNS = (
    ColumnDef("Server", 16, Alignments.LEFT),
    ColumnDef("Instance", 14, Alignments.LEFT),
    ColumnDef("Database", 22, Alignments.LEFT),
    ColumnDef("Recovery Model", 14, Alignments.CENTER),
    ColumnDef("Last Full Backup", 16, Alignments.CENTER),
    ColumnDef("Days Since", 10, Alignments.CENTER),
    ColumnDef("Backup Path", 40, Alignments.LEFT),
    ColumnDef("Size (MB)", 12, Alignments.RIGHT),
    ColumnDef("Status", 10, Alignments.CENTER, is_status=True),
    ColumnDef("Notes", 35, Alignments.LEFT, is_manual=True),
)

BACKUP_CONFIG = SheetConfig(name="Backups", columns=BACKUP_COLUMNS)

BACKUP_WARN_DAYS = 1
BACKUP_FAIL_DAYS = 7


class BackupSheetMixin(ServerGroupMixin, BaseSheetMixin):
    """Mixin for Backups sheet with server/instance grouping."""
    
    _backup_sheet = None
    
    def add_backup_info(
        self,
        server_name: str,
        instance_name: str,
        database_name: str,
        recovery_model: str,
        last_backup_date: Any,
        days_since: int | None,
        backup_path: str = "",
        backup_size_mb: Any = None,
    ) -> None:
        """Add a backup status row with compliance assessment."""
        if self._backup_sheet is None:
            self._backup_sheet = self._ensure_sheet(BACKUP_CONFIG)
            self._init_grouping(self._backup_sheet, BACKUP_CONFIG)
            self._add_backup_dropdowns()
        
        ws = self._backup_sheet
        
        # Track grouping and get row color
        row_color = self._track_group(server_name, instance_name, BACKUP_CONFIG.name)
        
        # Determine compliance status
        if days_since is None or days_since > BACKUP_FAIL_DAYS:
            status = "fail"
            self._increment_issue()
        elif days_since > BACKUP_WARN_DAYS:
            status = "warn"
            self._increment_warn()
        else:
            status = "pass"
            self._increment_pass()
        
        backup_date_str = format_date(last_backup_date) if last_backup_date else "NEVER"
        days_str = str(days_since) if days_since is not None else "N/A"
        size_str = format_size_mb(backup_size_mb) if backup_size_mb else ""
        
        data = [
            server_name,
            instance_name or "(Default)",
            database_name,
            recovery_model,
            backup_date_str,
            days_str,
            backup_path or "",
            size_str,
            None,  # Status
            "",    # Notes
        ]
        
        row = self._write_row(ws, BACKUP_CONFIG, data)
        
        self._apply_row_color(row, row_color, data_cols=[1, 2, 3, 4, 5, 6, 7, 8], ws=ws)
        apply_status_styling(ws.cell(row=row, column=9), status)
        
        if backup_date_str == "NEVER":
            ws.cell(row=row, column=5).fill = Fills.FAIL
            ws.cell(row=row, column=5).font = Fonts.FAIL
    
    def _finalize_backups(self) -> None:
        """Finalize backups sheet - merge remaining groups."""
        if self._backup_sheet:
            self._finalize_grouping(BACKUP_CONFIG.name)
    
    def _add_backup_dropdowns(self) -> None:
        """Add dropdown validations for status columns."""
        from autodbaudit.infrastructure.excel.base import add_dropdown_validation
        
        ws = self._backup_sheet
        # Status column (I) - column 9
        add_dropdown_validation(ws, "I", ["PASS", "WARN", "FAIL"])
