"""
Triggers Sheet Module.

Handles the Triggers worksheet for server and database trigger audit.
Uses ServerGroupMixin for server/instance grouping.

Per db-requirements.md Req 12: Triggers at all levels (server, database)
should be reviewed periodically.


UUID Support (v3):
    - Column A: Hidden UUID for stable row identification
    - All other columns shifted +1 from original positions
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
    ACTION_COLUMN,
    STATUS_COLUMN,
    LAST_REVIEWED_COLUMN,
    apply_action_needed_styling,
)
from autodbaudit.infrastructure.excel.server_group import ServerGroupMixin


__all__ = ["TriggerSheetMixin", "TRIGGER_CONFIG"]


TRIGGER_COLUMNS = (
    ACTION_COLUMN,  # Column A: Action indicator for discrepant triggers
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Scope", 10, Alignments.CENTER),  # "SERVER" or "DATABASE"
    ColumnDef(
        "Database", 20, Alignments.LEFT
    ),  # Database name (empty for SERVER scope)
    ColumnDef("Trigger Name", 28, Alignments.LEFT),
    ColumnDef("Event", 18, Alignments.LEFT),
    ColumnDef("Enabled", 10, Alignments.CENTER),
    STATUS_COLUMN,  # Review Status dropdown
    ColumnDef(
        "Notes", 40, Alignments.LEFT, is_manual=True
    ),  # Purpose/notes for trigger
    ColumnDef("Justification", 40, Alignments.LEFT, is_manual=True),
    LAST_REVIEWED_COLUMN,
)

TRIGGER_CONFIG = SheetConfig(name="Triggers", columns=TRIGGER_COLUMNS)


class TriggerSheetMixin(ServerGroupMixin, BaseSheetMixin):
    """Mixin for Triggers sheet with server/instance grouping."""

    _trigger_sheet = None

    def add_trigger(
        self,
        server_name: str,
        instance_name: str,
        trigger_name: str,
        event_type: str,
        is_enabled: bool,
        level: str = "DATABASE",  # "SERVER" or "DATABASE"
        database_name: str | None = None,
    ) -> None:
        """Add a trigger row.

        Args:
            server_name: Server hostname
            instance_name: SQL Server instance name
            trigger_name: Name of the trigger
            event_type: Event that fires the trigger
            is_enabled: Whether trigger is enabled
            level: "SERVER" for server-level triggers, "DATABASE" for database-level
            database_name: Database containing the trigger (required for DATABASE scope)
        """
        if self._trigger_sheet is None:
            self._trigger_sheet = self._ensure_sheet_with_uuid(TRIGGER_CONFIG)
            self._init_grouping(self._trigger_sheet, TRIGGER_CONFIG)
            self._add_trigger_dropdowns()

        ws = self._trigger_sheet

        # Track grouping and get row color
        row_color = self._track_group(server_name, instance_name, TRIGGER_CONFIG.name)

        # Normalize scope to uppercase
        scope = level.upper() if level else "DATABASE"

        # Server-level triggers need review (unusual, potential security concern)
        is_server_trigger = scope == "SERVER"
        needs_action = is_server_trigger  # Server triggers should be reviewed

        # Database display: show "(Server)" for server triggers, actual name otherwise
        db_display = database_name or ("" if scope == "DATABASE" else "")

        data = [
            None,  # Action indicator (column A)
            server_name,
            instance_name or "(Default)",
            scope,  # "SERVER" or "DATABASE"
            db_display,
            trigger_name,
            event_type or "",
            None,  # Enabled (will be styled)
            "",  # Review Status (column I = 9)
            "",  # Notes (column J = 10)
            "",  # Justification (column K = 11)
            "",  # Last Revised (column L = 12)
        ]

        row, row_uuid = self._write_row_with_uuid(ws, TRIGGER_CONFIG, data)

        # Apply action indicator
        apply_action_needed_styling(ws.cell(row=row, column=2), needs_action)

        # Apply row color to data columns (shifted +1 for UUID, +1 for action = +2 total)
        # Server=3, Instance=4, Scope=5, Database=6, Trigger Name=7, Event=8
        self._apply_row_color(row, row_color, data_cols=[3, 4, 5, 6, 7, 8], ws=ws)

        # Style Enabled column (column 9, shifted +1 for UUID)
        apply_boolean_styling(ws.cell(row=row, column=9), is_enabled)

        # Highlight server-level triggers with info color
        if is_server_trigger:
            for col in [4, 5, 6, 7]:  # Scope, Database, Trigger Name, Event
                ws.cell(row=row, column=col).fill = Fills.INFO

    def _finalize_triggers(self) -> None:
        """Finalize triggers sheet - merge remaining groups."""
        if self._trigger_sheet:
            self._finalize_grouping(TRIGGER_CONFIG.name)
            self._finalize_sheet_with_uuid(self._trigger_sheet)

    def _add_trigger_dropdowns(self) -> None:
        """Add dropdown validations for status columns."""
        from autodbaudit.infrastructure.excel.base import (
            add_dropdown_validation,
            add_review_status_conditional_formatting,
            STATUS_VALUES,
        )

        ws = self._trigger_sheet
        # Scope column (D) - column 4
        add_dropdown_validation(ws, "E", ["SERVER", "DATABASE"])
        # Enabled column (H) - column 8
        add_dropdown_validation(ws, "I", ["✓", "✗"])
        # Review Status column (I) - column 9
        add_dropdown_validation(ws, "J", STATUS_VALUES.all())
        add_review_status_conditional_formatting(ws, "J")
