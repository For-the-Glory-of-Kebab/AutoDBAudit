"""
Triggers Sheet Module.

Handles the Triggers worksheet for server and database trigger audit.
Uses ServerGroupMixin for server/instance grouping.
"""

from __future__ import annotations

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    Fills,
    apply_boolean_styling,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
)
from autodbaudit.infrastructure.excel.server_group import ServerGroupMixin


__all__ = ["TriggerSheetMixin", "TRIGGER_CONFIG"]


TRIGGER_COLUMNS = (
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Level", 12, Alignments.CENTER),
    ColumnDef("Database", 20, Alignments.LEFT),
    ColumnDef("Trigger Name", 30, Alignments.LEFT),
    ColumnDef("Event", 20, Alignments.LEFT),
    ColumnDef("Enabled", 10, Alignments.CENTER),
    ColumnDef("Purpose", 45, Alignments.LEFT, is_manual=True),
)

TRIGGER_CONFIG = SheetConfig(name="Triggers", columns=TRIGGER_COLUMNS)


class TriggerSheetMixin(ServerGroupMixin, BaseSheetMixin):
    """Mixin for Triggers sheet with server/instance grouping."""
    
    _trigger_sheet = None
    
    def add_trigger(
        self,
        server_name: str,
        instance_name: str,
        level: str,
        database_name: str | None,
        trigger_name: str,
        event_type: str,
        is_enabled: bool,
    ) -> None:
        """Add a trigger row."""
        if self._trigger_sheet is None:
            self._trigger_sheet = self._ensure_sheet(TRIGGER_CONFIG)
            self._init_grouping(self._trigger_sheet, TRIGGER_CONFIG)
        
        ws = self._trigger_sheet
        
        # Track grouping and get row color
        row_color = self._track_group(server_name, instance_name, TRIGGER_CONFIG.name)
        
        data = [
            server_name,
            instance_name or "(Default)",
            level,
            database_name or "",
            trigger_name,
            event_type or "",
            None,  # Enabled
            "",    # Purpose
        ]
        
        row = self._write_row(ws, TRIGGER_CONFIG, data)
        
        self._apply_row_color(row, row_color, data_cols=[1, 2, 3, 4, 5, 6], ws=ws)
        apply_boolean_styling(ws.cell(row=row, column=7), is_enabled)
        
        # Highlight server-level triggers
        if level.upper() == "SERVER":
            for col in [3, 4, 5, 6]:
                ws.cell(row=row, column=col).fill = Fills.INFO
    
    def _finalize_triggers(self) -> None:
        """Finalize triggers sheet - merge remaining groups."""
        if self._trigger_sheet:
            self._finalize_grouping(TRIGGER_CONFIG.name)
