"""
Backups Sheet Module.

Handles the Backups worksheet for database backup audit.
This sheet provides backup compliance status for all databases,
including age, location, and pass/fail assessment.

Sheet Purpose:
    - Verify backup compliance for all databases
    - Flag databases with old or missing backups
    - Track backup file locations for DR planning
    - Identify databases without recent backups

Compliance Rules:
    - PASS: Backup within last 24 hours
    - WARN: Backup 1-7 days old
    - FAIL: Backup older than 7 days or never backed up

Columns:
    - Server/Instance: SQL Server location
    - Database: Database name
    - Recovery Model: FULL/SIMPLE/BULK_LOGGED
    - Last Full Backup: Date of most recent full backup
    - Days Since: Days since last backup
    - Backup Path: Directory where backup file is stored
    - Size (MB): Backup file size
    - Status: Pass/Warn/Fail compliance status
    - Notes: Manual notes for exceptions

Visual Features:
    - Status column with color-coded Pass/Warn/Fail
    - Red highlighting for "NEVER" backups
    - Gray background for manual notes
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


__all__ = ["BackupSheetMixin", "BACKUP_CONFIG"]


BACKUP_COLUMNS = (
    ColumnDef("Server", 16, Alignments.LEFT),
    ColumnDef("Instance", 14, Alignments.LEFT),
    ColumnDef("Database", 22, Alignments.LEFT),
    ColumnDef("Recovery Model", 14, Alignments.CENTER),
    ColumnDef("Last Full Backup", 16, Alignments.CENTER),
    ColumnDef("Days Since", 10, Alignments.CENTER),
    ColumnDef("Backup Path", 40, Alignments.LEFT),  # NEW: Backup directory
    ColumnDef("Size (MB)", 12, Alignments.RIGHT),   # NEW: Backup size
    ColumnDef("Status", 10, Alignments.CENTER, is_status=True),
    ColumnDef("Notes", 35, Alignments.LEFT, is_manual=True),
)

BACKUP_CONFIG = SheetConfig(name="Backups", columns=BACKUP_COLUMNS)

# Backup age thresholds (configurable)
BACKUP_WARN_DAYS = 1   # Warn if older than 1 day
BACKUP_FAIL_DAYS = 7   # Fail if older than 7 days


class BackupSheetMixin(BaseSheetMixin):
    """
    Mixin for Backups sheet functionality.
    
    Provides the `add_backup_info` method to record backup status
    for each database. Automatically assesses compliance based
    on backup age thresholds.
    
    Compliance Logic:
        - days_since is None → FAIL (never backed up)
        - days_since > 7 → FAIL (outdated)
        - days_since > 1 → WARN (getting old)
        - days_since <= 1 → PASS (recent)
    
    Attributes:
        _backup_sheet: Reference to the Backups worksheet
        _backup_last_server: Tracks server for alternating colors
        _backup_alt: Toggles alternating background per server
    """
    
    _backup_sheet = None
    _backup_last_server: str = ""
    _backup_alt: bool = False
    
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
        """
        Add a backup status row with compliance assessment.
        
        Each database is automatically assessed against backup
        age thresholds. Databases that have never been backed up
        are flagged as FAIL.
        
        Args:
            server_name: Server hostname
            instance_name: SQL Server instance name
            database_name: Database name
            recovery_model: Recovery model:
                - "FULL" - Requires regular log backups
                - "SIMPLE" - No log backups needed
                - "BULK_LOGGED" - Minimal logging for bulk ops
            last_backup_date: Date of last full backup (None if never)
            days_since: Days since last backup (None if never)
            backup_path: Directory path of last backup file
            backup_size_mb: Size of last backup in MB
        
        Example:
            writer.add_backup_info(
                server_name="SQLPROD01",
                instance_name="",
                database_name="ApplicationDB",
                recovery_model="FULL",
                last_backup_date=datetime(2024, 12, 6),
                days_since=1,
                backup_path="D:\\Backups\\SQLPROD01\\",
                backup_size_mb=1024.5,
            )
        """
        # Lazy-initialize the worksheet
        if self._backup_sheet is None:
            self._backup_sheet = self._ensure_sheet(BACKUP_CONFIG)
            self._backup_last_server = ""
            self._backup_alt = False
        
        ws = self._backup_sheet
        
        # Toggle alternating color when server changes
        if server_name != self._backup_last_server:
            self._backup_alt = not self._backup_alt
            self._backup_last_server = server_name
        
        # Determine compliance status based on backup age
        if days_since is None or days_since > BACKUP_FAIL_DAYS:
            status = "fail"
            self._increment_issue()
        elif days_since > BACKUP_WARN_DAYS:
            status = "warn"
            self._increment_warn()
        else:
            status = "pass"
            self._increment_pass()
        
        # Format display values
        backup_date_str = format_date(last_backup_date) if last_backup_date else "NEVER"
        days_str = str(days_since) if days_since is not None else "N/A"
        size_str = format_size_mb(backup_size_mb) if backup_size_mb else ""
        
        # Prepare row data
        data = [
            server_name,
            instance_name or "(Default)",
            database_name,
            recovery_model,
            backup_date_str,
            days_str,
            backup_path or "",
            size_str,
            None,  # Status - styled separately
            "",    # Notes (manual)
        ]
        
        row = self._write_row(ws, BACKUP_CONFIG, data)
        
        # Apply alternating background for server grouping
        if self._backup_alt:
            for col in range(1, len(BACKUP_COLUMNS) + 1):
                cell = ws.cell(row=row, column=col)
                if not BACKUP_COLUMNS[col-1].is_manual and not BACKUP_COLUMNS[col-1].is_status:
                    cell.fill = Fills.SERVER_ALT
        
        # Apply status styling
        apply_status_styling(ws.cell(row=row, column=9), status)
        
        # Special styling for "NEVER" backups - make it stand out
        if backup_date_str == "NEVER":
            ws.cell(row=row, column=5).fill = Fills.FAIL
            ws.cell(row=row, column=5).font = Fonts.FAIL
