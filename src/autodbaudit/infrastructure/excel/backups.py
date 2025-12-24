"""
Backups Sheet Module.

Handles the Backups worksheet for database backup audit.
Uses ServerGroupMixin for server/instance grouping.


UUID Support (v3):
    - Column A: Hidden UUID for stable row identification
    - All other columns shifted +1 from original positions
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
    ACTION_COLUMN,
    STATUS_COLUMN,
    LAST_REVIEWED_COLUMN,
    apply_action_needed_styling,
)
from autodbaudit.infrastructure.excel.server_group import ServerGroupMixin


__all__ = ["BackupSheetMixin", "BACKUP_CONFIG"]


BACKUP_COLUMNS = (
    ACTION_COLUMN,  # Column B: Action indicator (A=UUID hidden)
    ColumnDef("Server", 16, Alignments.LEFT),  # Column C
    ColumnDef("Instance", 14, Alignments.LEFT),  # Column D
    ColumnDef("Database", 22, Alignments.LEFT),  # Column E
    ColumnDef("Recovery Model", 14, Alignments.CENTER),  # Column F
    ColumnDef("Last Full Backup", 16, Alignments.CENTER),  # Column G
    ColumnDef("Days Since", 10, Alignments.CENTER),  # Column H
    ColumnDef("Backup Path", 40, Alignments.LEFT),  # Column I
    ColumnDef("Size (MB)", 12, Alignments.RIGHT),  # Column J
    ColumnDef("Status", 10, Alignments.CENTER, is_status=True),  # Column K
    STATUS_COLUMN,  # Review Status dropdown
    ColumnDef("Justification", 35, Alignments.LEFT, is_manual=True),
    LAST_REVIEWED_COLUMN,
    ColumnDef("Notes", 25, Alignments.LEFT_WRAP, is_manual=True),
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
            self._backup_sheet = self._ensure_sheet_with_uuid(BACKUP_CONFIG)
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
            None,  # Action indicator (column B)
            server_name,  # Column C
            instance_name or "(Default)",
            database_name,
            recovery_model,
            backup_date_str,
            days_str,
            backup_path or "",
            size_str,
            None,  # Status
            "",  # Notes
        ]

        row, row_uuid = self._write_row_with_uuid(ws, BACKUP_CONFIG, data)

        # Apply action indicator - show ⏳ for FAIL/WARN backup status
        needs_action = status != "pass"
        apply_action_needed_styling(ws.cell(row=row, column=2), needs_action)

        # Apply row color (A=UUID, B=Action, C=Server, D=Instance, E=Database, F=Recovery, G=LastBackup, H=Days, I=Path, J=Size)
        self._apply_row_color(
            row, row_color, data_cols=[3, 4, 5, 6, 7, 8, 9, 10], ws=ws
        )

        # Apply status styling (Status is column K = 11)
        apply_status_styling(ws.cell(row=row, column=11), status)

        if backup_date_str == "NEVER":
            ws.cell(row=row, column=7).fill = (
                Fills.FAIL
            )  # Last Full Backup column G = 7
            ws.cell(row=row, column=7).font = Fonts.FAIL

    def _finalize_backups(self) -> None:
        """Finalize backups sheet - merge remaining groups."""
        if self._backup_sheet:
            self._finalize_grouping(BACKUP_CONFIG.name)
            self._finalize_sheet_with_uuid(self._backup_sheet)

    def _add_backup_dropdowns(self) -> None:
        """Add dropdown validations for status columns."""
        from autodbaudit.infrastructure.excel.base import (
            add_dropdown_validation,
            add_review_status_conditional_formatting,
            STATUS_VALUES,
        )

        ws = self._backup_sheet
        # Status column (K) - column 11 (A=UUID, B=Action, ..., K=Status)
        add_dropdown_validation(ws, "K", ["PASS", "WARN", "FAIL"])
        # Review Status column (L) - column 12
        add_dropdown_validation(ws, "L", STATUS_VALUES.all())
        add_review_status_conditional_formatting(ws, "L")
