"""
Audit Settings Sheet Module.

Handles the Audit Settings worksheet for login audit configuration.
Uses ServerGroupMixin for server/instance grouping.


UUID Support (v3):
    - Column A: Hidden UUID for stable row identification
    - All other columns shifted +1 from original positions
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
    ACTION_COLUMN,
    STATUS_COLUMN,
    LAST_REVIEWED_COLUMN,
    apply_action_needed_styling,
)
from autodbaudit.infrastructure.excel.server_group import ServerGroupMixin


__all__ = ["AuditSettingSheetMixin", "AUDIT_SETTING_CONFIG"]


AUDIT_SETTING_COLUMNS = (
    ACTION_COLUMN,  # Column A: Action indicator (⏳ needs attention)
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Setting", 35, Alignments.LEFT),
    ColumnDef("Current Value", 15, Alignments.CENTER),
    ColumnDef("Recommended", 15, Alignments.CENTER),
    ColumnDef("Status", 12, Alignments.CENTER, is_status=True),
    STATUS_COLUMN,  # Review Status dropdown
    ColumnDef("Justification", 35, Alignments.LEFT, is_manual=True),
    LAST_REVIEWED_COLUMN,
    ColumnDef("Notes", 30, Alignments.LEFT, is_manual=True),
)

AUDIT_SETTING_CONFIG = SheetConfig(name="Audit Settings", columns=AUDIT_SETTING_COLUMNS)


class AuditSettingSheetMixin(ServerGroupMixin, BaseSheetMixin):
    """Mixin for Audit Settings sheet with server/instance grouping."""
    
    _audit_setting_sheet = None
    
    def add_audit_setting(
        self,
        server_name: str,
        instance_name: str,
        setting_name: str,
        current_value: str,
        recommended_value: str,
    ) -> None:
        """Add an audit setting row."""
        if self._audit_setting_sheet is None:
            self._audit_setting_sheet = self._ensure_sheet_with_uuid(AUDIT_SETTING_CONFIG)
            self._init_grouping(self._audit_setting_sheet, AUDIT_SETTING_CONFIG)
            self._add_audit_dropdowns()
        
        ws = self._audit_setting_sheet
        
        # Track grouping and get row color
        row_color = self._track_group(server_name, instance_name, AUDIT_SETTING_CONFIG.name)
        
        status = "pass" if str(current_value).lower() == str(recommended_value).lower() else "fail"
        if status == "pass":
            self._increment_pass()
        else:
            self._increment_issue()
        
        # Determine if action needed (FAIL status)
        needs_action = status == "fail"
        
        data = [
            None,  # Action indicator (column A)
            server_name,
            instance_name or "(Default)",
            setting_name,
            current_value,
            recommended_value,
            None,  # Status
            "",    # Justification
            "",    # Notes
        ]
        
        row, row_uuid = self._write_row_with_uuid(ws, AUDIT_SETTING_CONFIG, data)
        
        # Apply action indicator (column 1)
        apply_action_needed_styling(ws.cell(row=row, column=2), needs_action)
        
        # Apply row color (shifted +1 for action column)
        self._apply_row_color(row, row_color, data_cols=[3, 4, 5, 6, 7], ws=ws)
        
        # Status column (column 7, shifted +1)
        apply_status_styling(ws.cell(row=row, column=7), status)
    
    def _finalize_audit_settings(self) -> None:
        """Finalize audit settings sheet - merge remaining groups."""
        if self._audit_setting_sheet:
            self._finalize_grouping(AUDIT_SETTING_CONFIG.name)
            self._finalize_sheet_with_uuid(self._audit_setting_sheet)
    
    def _add_audit_dropdowns(self) -> None:
        """Add dropdown validations for status columns."""
        from autodbaudit.infrastructure.excel.base import (
            add_dropdown_validation, add_review_status_conditional_formatting, STATUS_VALUES
        )
        
        ws = self._audit_setting_sheet
        # Status column (G = 7, shifted +1)
        add_dropdown_validation(ws, "H", ["PASS", "FAIL"])
        # Review Status column (H) - column 8
        add_dropdown_validation(ws, "I", STATUS_VALUES.all())
        add_review_status_conditional_formatting(ws, "I")
