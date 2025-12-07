"""
Triggers Sheet Module.

Handles the Triggers worksheet for server and database trigger audit.
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


class TriggerSheetMixin(BaseSheetMixin):
    """Mixin for Triggers sheet functionality."""
    
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
        """
        Add a trigger row.
        
        Server-level triggers are highlighted as they require extra review.
        
        Args:
            server_name: Server hostname
            instance_name: SQL Server instance name
            level: Trigger level ("SERVER" or "DATABASE")
            database_name: Database name (None for server triggers)
            trigger_name: Name of the trigger
            event_type: Event that fires the trigger
            is_enabled: Whether the trigger is enabled
        """
        if self._trigger_sheet is None:
            self._trigger_sheet = self._ensure_sheet(TRIGGER_CONFIG)
        
        ws = self._trigger_sheet
        
        data = [
            server_name,
            instance_name or "(Default)",
            level,
            database_name or "",
            trigger_name,
            event_type or "",
            None,  # Enabled - styled separately
            "",    # Purpose
        ]
        
        row = self._write_row(ws, TRIGGER_CONFIG, data)
        
        apply_boolean_styling(ws.cell(row=row, column=7), is_enabled)
        
        # Highlight server-level triggers
        if level.upper() == "SERVER":
            for col in range(1, 6):
                ws.cell(row=row, column=col).fill = Fills.INFO
