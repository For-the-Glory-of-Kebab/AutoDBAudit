"""
Audit Settings Sheet Module.

Handles the Audit Settings worksheet for login audit configuration.
"""

from __future__ import annotations

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    apply_status_styling,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
)


__all__ = ["AuditSettingSheetMixin", "AUDIT_SETTING_CONFIG"]


AUDIT_SETTING_COLUMNS = (
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Setting", 35, Alignments.LEFT),
    ColumnDef("Current Value", 15, Alignments.CENTER),
    ColumnDef("Recommended", 15, Alignments.CENTER),
    ColumnDef("Status", 12, Alignments.CENTER, is_status=True),
    ColumnDef("Notes", 45, Alignments.LEFT, is_manual=True),
)

AUDIT_SETTING_CONFIG = SheetConfig(name="Audit Settings", columns=AUDIT_SETTING_COLUMNS)


class AuditSettingSheetMixin(BaseSheetMixin):
    """Mixin for Audit Settings sheet functionality."""
    
    _audit_setting_sheet = None
    
    def add_audit_setting(
        self,
        server_name: str,
        instance_name: str,
        setting_name: str,
        current_value: str,
        recommended_value: str,
    ) -> None:
        """
        Add an audit setting row.
        
        Args:
            server_name: Server hostname
            instance_name: SQL Server instance name
            setting_name: Name of the audit setting
            current_value: Current setting value
            recommended_value: Recommended/required value
        """
        if self._audit_setting_sheet is None:
            self._audit_setting_sheet = self._ensure_sheet(AUDIT_SETTING_CONFIG)
        
        ws = self._audit_setting_sheet
        
        # Compare values (case-insensitive)
        status = "pass" if str(current_value).lower() == str(recommended_value).lower() else "fail"
        if status == "pass":
            self._increment_pass()
        else:
            self._increment_issue()
        
        data = [
            server_name,
            instance_name or "(Default)",
            setting_name,
            current_value,
            recommended_value,
            None,  # Status - styled separately
            "",    # Notes
        ]
        
        row = self._write_row(ws, AUDIT_SETTING_CONFIG, data)
        
        apply_status_styling(ws.cell(row=row, column=6), status)
