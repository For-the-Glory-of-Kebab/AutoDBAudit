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
    ACTION_COLUMN,
    STATUS_COLUMN,
    LAST_REVIEWED_COLUMN,
    apply_action_needed_styling,
)
from autodbaudit.infrastructure.excel.server_group import ServerGroupMixin


__all__ = ["ConfigSheetMixin", "CONFIG_CONFIG"]


CONFIG_COLUMNS = (
    ACTION_COLUMN,  # Column A: Action indicator
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Setting", 35, Alignments.LEFT),
    ColumnDef("Current", 12, Alignments.CENTER),
    ColumnDef("Required", 12, Alignments.CENTER),
    ColumnDef("Status", 12, Alignments.CENTER, is_status=True),
    ColumnDef("Risk", 10, Alignments.CENTER),
    STATUS_COLUMN,  # Review Status dropdown
    ColumnDef("Exception Reason", 45, Alignments.LEFT, is_manual=True),
    LAST_REVIEWED_COLUMN,
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
            None,  # Action indicator (column A)
            server_name,
            instance_name or "(Default)",
            setting_name,
            str(current_value),
            str(required_value),
            None,  # Status
            (risk_level or "Low").title(),
            "",  # Exception Reason
        ]

        row = self._write_row(ws, CONFIG_CONFIG, data)

        # Apply action indicator (column A) - show ⏳ for FAIL items
        needs_action = status != "pass"
        apply_action_needed_styling(ws.cell(row=row, column=1), needs_action)

        # Apply row color to data columns (shifted +1: Server=2, Instance=3, Setting=4, etc.)
        self._apply_row_color(row, row_color, data_cols=[2, 3, 4, 5, 6], ws=ws)

        # Apply status styling (Status is now column 7, shifted +1)
        apply_status_styling(ws.cell(row=row, column=7), status)

        # Highlight risk column (Risk is now column 8, shifted +1)
        if risk_level.lower() == "critical":
            ws.cell(row=row, column=8).fill = Fills.CRITICAL
        elif risk_level.lower() == "high":
            ws.cell(row=row, column=8).fill = Fills.FAIL

    def _finalize_config(self) -> None:
        """Finalize config sheet - merge remaining groups."""
        if self._config_sheet:
            self._finalize_grouping(CONFIG_CONFIG.name)

    def _add_config_dropdowns(self) -> None:
        """Add dropdown validations for status columns."""
        from autodbaudit.infrastructure.excel.base import add_dropdown_validation

        ws = self._config_sheet
        # Status column (G) - column 7 (shifted +1 from F)
        add_dropdown_validation(ws, "G", ["✅ PASS", "❌ FAIL"])
        # Risk column (H) - column 8 (shifted +1 from G)
        add_dropdown_validation(ws, "H", ["Critical", "High", "Medium", "Low"])
