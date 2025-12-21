"""
Linked Servers Sheet Module.

Handles the Linked Servers worksheet for linked server security audit.
Uses ServerGroupMixin for server/instance grouping.
Includes login mapping info, impersonate settings, and data validation dropdowns.

UUID Support (v3):
    - Column A: Hidden UUID for stable row identification
    - All other columns shifted +1 from original positions
"""

from __future__ import annotations

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    Fills,
    Fonts,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
    LAST_REVIEWED_COLUMN,
    STATUS_COLUMN,
    ACTION_COLUMN,
    apply_action_needed_styling,
)
from autodbaudit.infrastructure.excel.server_group import ServerGroupMixin


__all__ = ["LinkedServerSheetMixin", "LINKED_SERVER_CONFIG"]


# Column definitions (WITHOUT UUID - it's added automatically)
LINKED_SERVER_COLUMNS = (
    ACTION_COLUMN,  # Column B (after UUID): Action indicator
    ColumnDef("Server", 16, Alignments.LEFT),  # Column C
    ColumnDef("Instance", 14, Alignments.LEFT),  # Column D
    ColumnDef("Linked Server", 22, Alignments.LEFT),  # Column E
    ColumnDef("Provider", 16, Alignments.LEFT),  # Column F
    ColumnDef("Data Source", 28, Alignments.LEFT),  # Column G
    ColumnDef("RPC Out", 10, Alignments.CENTER),  # Column H
    ColumnDef("Local Login", 16, Alignments.LEFT),  # Column I
    ColumnDef("Remote Login", 16, Alignments.LEFT),  # Column J
    ColumnDef("Impersonate", 12, Alignments.CENTER),  # Column K
    ColumnDef("Risk", 12, Alignments.CENTER),  # Column L
    STATUS_COLUMN,  # Column M: Review Status dropdown
    ColumnDef("Purpose", 30, Alignments.LEFT, is_manual=True),  # Column N
    ColumnDef("Justification", 40, Alignments.LEFT, is_manual=True),  # Column O
    LAST_REVIEWED_COLUMN,  # Column P
)

LINKED_SERVER_CONFIG = SheetConfig(name="Linked Servers", columns=LINKED_SERVER_COLUMNS)

# Column indices WITH UUID offset (Column A = UUID, B = 2, C = 3, etc.)
# Use these for cell access after _write_row_with_uuid
COL_UUID = 1
COL_ACTION = 2
COL_SERVER = 3
COL_INSTANCE = 4
COL_LINKED_SERVER = 5
COL_PROVIDER = 6
COL_DATA_SOURCE = 7
COL_RPC_OUT = 8
COL_LOCAL_LOGIN = 9
COL_REMOTE_LOGIN = 10
COL_IMPERSONATE = 11
COL_RISK = 12
COL_REVIEW_STATUS = 13
COL_PURPOSE = 14
COL_JUSTIFICATION = 15
COL_LAST_REVIEWED = 16


class LinkedServerSheetMixin(ServerGroupMixin, BaseSheetMixin):
    """Mixin for Linked Servers sheet with server/instance grouping and UUID support."""

    _linked_server_sheet = None
    _ls_validations_added = False

    def add_linked_server(
        self,
        server_name: str,
        instance_name: str,
        linked_server_name: str,
        product: str,  # Kept for API compatibility, not used
        provider: str,
        data_source: str,
        rpc_out: bool,
        local_login: str = "",
        remote_login: str = "",
        impersonate: bool = False,
        risk_level: str = "",
    ) -> tuple[int, str]:
        """
        Add a linked server row with login mapping and security info.
        
        Returns:
            Tuple of (row_number, row_uuid) for tracking
        """
        if self._linked_server_sheet is None:
            # Use UUID-aware sheet creation
            self._linked_server_sheet = self._ensure_sheet_with_uuid(LINKED_SERVER_CONFIG)
            self._init_grouping(self._linked_server_sheet, LINKED_SERVER_CONFIG)
            self._add_linked_server_validations()

        ws = self._linked_server_sheet

        # Track grouping and get row color
        row_color = self._track_group(
            server_name, instance_name, LINKED_SERVER_CONFIG.name
        )

        # Determine if this is a high-risk linked server needing attention
        is_high_risk = risk_level == "HIGH_PRIVILEGE"

        # Data for columns B onwards (UUID is handled by _write_row_with_uuid)
        data = [
            None,  # Action indicator (column B)
            server_name,  # Column C
            instance_name or "(Default)",  # Column D
            linked_server_name,  # Column E
            provider or "",  # Column F
            data_source or "",  # Column G
            None,  # RPC Out - styled separately (Column H)
            local_login or "",  # Column I
            remote_login or "",  # Column J
            None,  # Impersonate - styled separately (Column K)
            None,  # Risk - styled separately (Column L)
            "",  # Review Status (Column M)
            "",  # Purpose (Column N)
            "",  # Justification (Column O)
            "",  # Last Reviewed (Column P)
        ]

        # Write row with UUID generation
        row, row_uuid = self._write_row_with_uuid(ws, LINKED_SERVER_CONFIG, data)

        # Apply action indicator - show ⏳ for high-risk linked servers
        apply_action_needed_styling(ws.cell(row=row, column=COL_ACTION), is_high_risk)

        # Apply row color to data columns (not UUID)
        self._apply_row_color(
            row, row_color,
            data_cols=[COL_SERVER, COL_INSTANCE, COL_LINKED_SERVER,
                       COL_PROVIDER, COL_DATA_SOURCE, COL_LOCAL_LOGIN, COL_REMOTE_LOGIN],
            ws=ws
        )

        # RPC Out column with styled value
        rpc_cell = ws.cell(row=row, column=COL_RPC_OUT)
        if rpc_out:
            rpc_cell.value = "✓ Yes"
            rpc_cell.fill = Fills.PASS
            rpc_cell.font = Fonts.PASS
        else:
            rpc_cell.value = "✗ No"
            rpc_cell.fill = Fills.WARN

        # Impersonate column with styled value
        impersonate_cell = ws.cell(row=row, column=COL_IMPERSONATE)
        if impersonate:
            impersonate_cell.value = "✓ Yes"
            impersonate_cell.fill = Fills.WARN  # Worth noting
        else:
            impersonate_cell.value = "✗ No"
            impersonate_cell.fill = Fills.PASS

        # Risk column with styled value
        risk_cell = ws.cell(row=row, column=COL_RISK)
        if is_high_risk:
            risk_cell.value = "🔴 High"
            risk_cell.fill = Fills.FAIL
            risk_cell.font = Fonts.FAIL
            self._increment_warn()
        else:
            risk_cell.value = "🟢 Normal"
            risk_cell.fill = Fills.PASS

        return row, row_uuid

    def _add_linked_server_validations(self) -> None:
        """Add dropdown data validation to choice columns."""
        if self._ls_validations_added:
            return

        from autodbaudit.infrastructure.excel.base import (
            add_dropdown_validation,
            add_review_status_conditional_formatting,
            STATUS_VALUES,
        )

        ws = self._linked_server_sheet
        
        # Column letters shifted +1 for UUID (A=UUID, B=Action, C=Server, etc.)
        # RPC Out dropdown (column H)
        add_dropdown_validation(ws, "H", ["✓ Yes", "✗ No"])
        # Impersonate dropdown (column K)
        add_dropdown_validation(ws, "K", ["✓ Yes", "✗ No"])
        # Risk dropdown (column L)
        add_dropdown_validation(ws, "L", ["🟢 Normal", "🔴 HIGH"])
        # Review Status dropdown (column M)
        add_dropdown_validation(ws, "M", STATUS_VALUES.all())
        add_review_status_conditional_formatting(ws, "M")

        self._ls_validations_added = True

    def _finalize_linked_servers(self) -> None:
        """Finalize linked servers sheet - merge remaining groups and apply UUID protection."""
        if self._linked_server_sheet:
            self._finalize_grouping(LINKED_SERVER_CONFIG.name)
            # Apply UUID column protection
            self._finalize_sheet_with_uuid(self._linked_server_sheet)

