"""
Configuration Sheet Module.

Handles the Configuration worksheet for sp_configure security settings.
Uses ServerGroupMixin for server/instance grouping.
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
from autodbaudit.infrastructure.excel.server_group import ServerGroupMixin


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


class ConfigSheetMixin(ServerGroupMixin, BaseSheetMixin):
    """Mixin for Configuration sheet with server/instance grouping."""
    
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
        """Add a configuration setting row."""
        if self._config_sheet is None:
            self._config_sheet = self._ensure_sheet(CONFIG_CONFIG)
            self._init_grouping(self._config_sheet, CONFIG_CONFIG)
            self._add_config_dropdowns()
        
        ws = self._config_sheet
        
        # Track grouping and get row color
        row_color = self._track_group(server_name, instance_name, CONFIG_CONFIG.name)
        
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
            None,  # Status
            risk_level.title(),
            "",    # Exception Reason
        ]
        
        row = self._write_row(ws, CONFIG_CONFIG, data)
        
        # Apply row color to data columns
        self._apply_row_color(row, row_color, data_cols=[1, 2, 3, 4, 5], ws=ws)
        
        # Apply status styling
        apply_status_styling(ws.cell(row=row, column=6), status)
        
        # Highlight risk column
        if risk_level.lower() == "critical":
            ws.cell(row=row, column=7).fill = Fills.CRITICAL
        elif risk_level.lower() == "high":
            ws.cell(row=row, column=7).fill = Fills.FAIL
    
    def _finalize_config(self) -> None:
        """Finalize config sheet - merge remaining groups."""
        if self._config_sheet:
            self._finalize_grouping(CONFIG_CONFIG.name)
    
    def _add_config_dropdowns(self) -> None:
        """Add dropdown validations for status columns."""
        from autodbaudit.infrastructure.excel.base import add_dropdown_validation
        
        ws = self._config_sheet
        # Status column (F) - column 6
        add_dropdown_validation(ws, "F", ["✅ PASS", "❌ FAIL"])
        # Risk column (G) - column 7
        add_dropdown_validation(ws, "G", ["Critical", "High", "Medium", "Low"])
