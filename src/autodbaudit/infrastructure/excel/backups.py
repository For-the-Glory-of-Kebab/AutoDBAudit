"""
Backups Sheet Module.

Handles the Backups worksheet for database backup audit.
"""

from __future__ import annotations

from typing import Any

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    apply_status_styling,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
    format_date,
)


__all__ = ["BackupSheetMixin", "BACKUP_CONFIG"]


BACKUP_COLUMNS = (
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Database", 25, Alignments.LEFT),
    ColumnDef("Recovery Model", 15, Alignments.CENTER),
    ColumnDef("Last Full Backup", 18, Alignments.CENTER),
    ColumnDef("Days Since", 12, Alignments.CENTER),
    ColumnDef("Status", 12, Alignments.CENTER, is_status=True),
    ColumnDef("Notes", 40, Alignments.LEFT, is_manual=True),
)

BACKUP_CONFIG = SheetConfig(name="Backups", columns=BACKUP_COLUMNS)

# Backup age thresholds
BACKUP_WARN_DAYS = 1   # Warn if older than 1 day
BACKUP_FAIL_DAYS = 7   # Fail if older than 7 days


class BackupSheetMixin(BaseSheetMixin):
    """Mixin for Backups sheet functionality."""
    
    _backup_sheet = None
    
    def add_backup_info(
        self,
        server_name: str,
        instance_name: str,
        database_name: str,
        recovery_model: str,
        last_backup_date: Any,
        days_since: int | None,
    ) -> None:
        """
        Add a backup info row.
        
        Args:
            server_name: Server hostname
            instance_name: SQL Server instance name
            database_name: Database name
            recovery_model: Recovery model (FULL, SIMPLE, BULK_LOGGED)
            last_backup_date: Date of last full backup (None if never)
            days_since: Days since last backup (None if never)
        """
        if self._backup_sheet is None:
            self._backup_sheet = self._ensure_sheet(BACKUP_CONFIG)
        
        ws = self._backup_sheet
        
        # Determine status based on backup age
        if days_since is None or days_since > BACKUP_FAIL_DAYS:
            status = "fail"
            self._increment_issue()
        elif days_since > BACKUP_WARN_DAYS:
            status = "warn"
            self._increment_warn()
        else:
            status = "pass"
            self._increment_pass()
        
        data = [
            server_name,
            instance_name or "(Default)",
            database_name,
            recovery_model,
            format_date(last_backup_date) if last_backup_date else "NEVER",
            str(days_since) if days_since is not None else "N/A",
            None,  # Status - styled separately
            "",    # Notes
        ]
        
        row = self._write_row(ws, BACKUP_CONFIG, data)
        
        apply_status_styling(ws.cell(row=row, column=7), status)
