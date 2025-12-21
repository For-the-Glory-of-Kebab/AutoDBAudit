"""
Encryption Sheet Module.

Handles the Encryption worksheet for encryption key status audit.
Covers SMK (instance-level), DMK (database-level), and TDE status.
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
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
    add_dropdown_validation,
)
from autodbaudit.infrastructure.excel.server_group import ServerGroupMixin


__all__ = ["EncryptionSheetMixin", "ENCRYPTION_CONFIG"]


ENCRYPTION_COLUMNS = (
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Database", 20, Alignments.LEFT),
    ColumnDef("Key Type", 16, Alignments.CENTER),
    ColumnDef("Key Name", 25, Alignments.LEFT),
    ColumnDef("Algorithm", 14, Alignments.CENTER),
    ColumnDef("Created", 12, Alignments.CENTER),
    ColumnDef("Backup Status", 16, Alignments.CENTER),
    ColumnDef("Status", 10, Alignments.CENTER),
    ColumnDef("Notes", 40, Alignments.LEFT, is_manual=True),
)

ENCRYPTION_CONFIG = SheetConfig(name="Encryption", columns=ENCRYPTION_COLUMNS)

# Dropdown options
KEY_TYPE_OPTIONS = ["SMK", "DMK", "TDE Certificate", "DEK"]
BACKUP_STATUS_OPTIONS = ["✓ Backed Up", "⚠️ Not Backed Up", "N/A"]
STATUS_OPTIONS = ["PASS", "FAIL", "WARN", "N/A"]


class EncryptionSheetMixin(ServerGroupMixin, BaseSheetMixin):
    """Mixin for Encryption sheet with server/instance grouping."""
    
    _encryption_sheet = None
    
    def add_encryption_row(
        self,
        server_name: str,
        instance_name: str,
        database_name: str,
        key_type: str,
        key_name: str,
        algorithm: str,
        created_date: Any,
        backup_status: str,
        status: str,
    ) -> None:
        """Add an encryption row."""
        if self._encryption_sheet is None:
            self._encryption_sheet = self._ensure_sheet_with_uuid(ENCRYPTION_CONFIG)
            self._init_grouping(self._encryption_sheet, ENCRYPTION_CONFIG)
            self._add_encryption_dropdowns()
        
        ws = self._encryption_sheet
        
        # Track grouping and get row color
        row_color = self._track_group(server_name, instance_name, ENCRYPTION_CONFIG.name)
        
        # Format date
        created_str = ""
        if created_date:
            try:
                created_str = created_date.strftime("%Y-%m-%d") if hasattr(created_date, "strftime") else str(created_date)[:10]
            except (AttributeError, TypeError):
                created_str = str(created_date)[:10] if created_date else ""
        
        data = [
            server_name,
            instance_name or "(Default)",
            database_name or "(Instance)",
            key_type,
            key_name or "",
            algorithm or "",
            created_str,
            None,  # Backup Status - styled separately
            None,  # Status - styled separately
            "",    # Notes
        ]
        
        row, row_uuid = self._write_row_with_uuid(ws, ENCRYPTION_CONFIG, data)
        
        # Apply row color to data columns
        self._apply_row_color(row, row_color, data_cols=[2, 3, 4, 5, 6, 7, 8], ws=ws)
        
        # Style Backup Status column (column 8)
        backup_cell = ws.cell(row=row, column=8)
        backup_lower = (backup_status or "").lower()
        if "backed up" in backup_lower and "not" not in backup_lower:
            backup_cell.value = "✓ Backed Up"
            backup_cell.fill = Fills.PASS
            backup_cell.font = Fonts.PASS
        elif "not" in backup_lower or "no" in backup_lower:
            backup_cell.value = "⚠️ Not Backed Up"
            backup_cell.fill = Fills.WARN
            backup_cell.font = Fonts.WARN
        else:
            backup_cell.value = backup_status or "N/A"
        backup_cell.alignment = Alignments.CENTER
        
        # Style Status column (column 9)
        status_cell = ws.cell(row=row, column=9)
        status_upper = (status or "").upper()
        if status_upper == "PASS":
            status_cell.value = "PASS"
            status_cell.fill = Fills.PASS
            status_cell.font = Fonts.PASS
        elif status_upper == "FAIL":
            status_cell.value = "FAIL"
            status_cell.fill = Fills.FAIL
            status_cell.font = Fonts.FAIL
        elif status_upper == "WARN":
            status_cell.value = "WARN"
            status_cell.fill = Fills.WARN
            status_cell.font = Fonts.WARN
        else:
            status_cell.value = status or "N/A"
        status_cell.alignment = Alignments.CENTER
    
    def _add_encryption_dropdowns(self) -> None:
        """Add dropdown validations to the Encryption sheet."""
        ws = self._encryption_sheet
        if ws is None:
            return
        
        # Key Type dropdown (column 4)
        add_dropdown_validation(ws, column_letter="D", options=KEY_TYPE_OPTIONS)
        
        # Backup Status dropdown (column 8)
        add_dropdown_validation(ws, column_letter="H", options=BACKUP_STATUS_OPTIONS)
        
        # Status dropdown (column 9)
        add_dropdown_validation(ws, column_letter="I", options=STATUS_OPTIONS)
