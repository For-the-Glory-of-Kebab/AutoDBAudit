"""
Configuration Sheet Module.

Handles the Configuration worksheet for sp_configure security settings.
"""

from __future__ import annotations

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    Fills,
    apply_status_styling,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
)


__all__ = ["ConfigSheetMixin", "CONFIG_CONFIG"]


CONFIG_COLUMNS = (
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Setting", 35, Alignments.LEFT),
    ColumnDef("Current", 12, Alignments.CENTER),
    ColumnDef("Required", 12, Alignments.CENTER),
    ColumnDef("Status", 12, Alignments.CENTER, is_status=True),
    ColumnDef("Risk", 10, Alignments.CENTER),
    ColumnDef("Exception Reason", 45, Alignments.LEFT, is_manual=True),
)

CONFIG_CONFIG = SheetConfig(name="Configuration", columns=CONFIG_COLUMNS)


class ConfigSheetMixin(BaseSheetMixin):
    """Mixin for Configuration sheet functionality."""
    
    _config_sheet = None
    
    def add_config_setting(
        self,
        server_name: str,
        instance_name: str,
        setting_name: str,
        current_value: int,
        required_value: int,
        risk_level: str = "medium",
    ) -> None:
        """
        Add a configuration setting row.
        
        Args:
            server_name: Server hostname
            instance_name: SQL Server instance name
            setting_name: Name of the sp_configure setting
            current_value: Current configured value
            required_value: Required/recommended value
            risk_level: Risk level if non-compliant (critical/high/medium/low)
        """
        if self._config_sheet is None:
            self._config_sheet = self._ensure_sheet(CONFIG_CONFIG)
        
        ws = self._config_sheet
        
        # Determine compliance status
        status = "pass" if current_value == required_value else "fail"
        if status == "pass":
            self._increment_pass()
        else:
            self._increment_issue()
        
        data = [
            server_name,
            instance_name or "(Default)",
            setting_name,
            str(current_value),
            str(required_value),
            None,  # Status - styled separately
            risk_level.title(),
            "",    # Exception Reason
        ]
        
        row = self._write_row(ws, CONFIG_CONFIG, data)
        
        apply_status_styling(ws.cell(row=row, column=6), status)
        
        # Highlight critical settings
        if risk_level.lower() == "critical":
            ws.cell(row=row, column=7).fill = Fills.CRITICAL
        elif risk_level.lower() == "high":
            ws.cell(row=row, column=7).fill = Fills.FAIL
