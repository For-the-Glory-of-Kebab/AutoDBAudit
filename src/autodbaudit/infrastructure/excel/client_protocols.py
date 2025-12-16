"""
Client Protocols Sheet Module.

Handles the Client Protocols worksheet for network protocol security audit.
Uses ServerGroupMixin for server/instance grouping.

Discrepancy Logic:
- Acceptable: Shared Memory + TCP/IP (enabled by default for network connectivity)
- Discrepant: Named Pipes, VIA, or other protocols (need justification if enabled)
"""

from __future__ import annotations

from openpyxl.styles import PatternFill

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    Fills,
    Fonts,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
    ACTION_COLUMN,
    STATUS_COLUMN,
    LAST_REVISED_COLUMN,
    apply_action_needed_styling,
)
from autodbaudit.infrastructure.excel.server_group import ServerGroupMixin


__all__ = ["ClientProtocolSheetMixin", "CLIENT_PROTOCOL_CONFIG"]


# Acceptable protocols that don't need justification
ACCEPTABLE_PROTOCOLS = frozenset({
    "shared memory",
    "tcp/ip",
})

# Protocols that need justification if enabled
DISCREPANT_PROTOCOLS = frozenset({
    "named pipes",
    "via",
})


CLIENT_PROTOCOL_COLUMNS = (
    ACTION_COLUMN,  # Column A: Action indicator
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Protocol", 18, Alignments.LEFT),
    ColumnDef("Enabled", 10, Alignments.CENTER),
    ColumnDef("Port", 10, Alignments.CENTER),
    ColumnDef("Status", 14, Alignments.CENTER),
    ColumnDef("Notes", 30, Alignments.LEFT),
    STATUS_COLUMN,  # Review Status dropdown
    ColumnDef("Justification", 40, Alignments.LEFT, is_manual=True),
    LAST_REVISED_COLUMN,
)

CLIENT_PROTOCOL_CONFIG = SheetConfig(name="Client Protocols", columns=CLIENT_PROTOCOL_COLUMNS)


class ClientProtocolSheetMixin(ServerGroupMixin, BaseSheetMixin):
    """Mixin for Client Protocols sheet with server/instance grouping."""
    
    _client_protocol_sheet = None
    
    def add_client_protocol(
        self,
        server_name: str,
        instance_name: str,
        protocol_name: str,
        is_enabled: bool,
        port: int | None = None,
        notes: str = "",
    ) -> None:
        """Add a client protocol row.
        
        Args:
            server_name: Server hostname
            instance_name: Instance name
            protocol_name: Protocol name (Shared Memory, TCP/IP, Named Pipes, VIA)
            is_enabled: Whether protocol is enabled
            port: Port number (for TCP/IP)
            notes: Additional notes about configuration
        """
        if self._client_protocol_sheet is None:
            self._client_protocol_sheet = self._ensure_sheet(CLIENT_PROTOCOL_CONFIG)
            self._init_grouping(self._client_protocol_sheet, CLIENT_PROTOCOL_CONFIG)
            self._add_protocol_dropdowns()
        
        ws = self._client_protocol_sheet
        
        # Track grouping and get row color
        row_color = self._track_group(server_name, instance_name, CLIENT_PROTOCOL_CONFIG.name)
        
        # Determine discrepancy status
        protocol_lower = protocol_name.lower().strip()
        is_acceptable = protocol_lower in ACCEPTABLE_PROTOCOLS
        is_discrepant = protocol_lower in DISCREPANT_PROTOCOLS
        
        # Needs action if: enabled AND not an acceptable protocol
        needs_action = is_enabled and not is_acceptable
        
        # Determine status
        if is_acceptable and is_enabled:
            status = "✅ Compliant"
        elif not is_enabled and is_discrepant:
            status = "✅ Disabled"  # Good - discrepant protocol is off
        elif is_enabled and is_discrepant:
            status = "⚠️ Needs Review"  # Enabled discrepant protocol
        elif not is_enabled and is_acceptable:
            status = "ℹ️ Disabled"  # Acceptable but turned off
        else:
            status = "—"
        
        data = [
            None,  # Action indicator (column A)
            server_name,
            instance_name or "(Default)",
            protocol_name,
            None,  # Enabled - styled separately
            str(port) if port else "—",
            None,  # Status - styled separately
            notes or "",
            "",    # Justification
            "",    # Last Revised
        ]
        
        row = self._write_row(ws, CLIENT_PROTOCOL_CONFIG, data)
        
        # Apply action indicator (column 1)
        apply_action_needed_styling(ws.cell(row=row, column=1), needs_action)
        
        # Apply row color to data columns
        self._apply_row_color(row, row_color, data_cols=[2, 3, 4, 6, 8], ws=ws)
        
        # Style Enabled column (column 5)
        enabled_cell = ws.cell(row=row, column=5)
        if is_enabled:
            enabled_cell.value = "✓ Yes"
            if is_acceptable:
                enabled_cell.fill = Fills.PASS
                enabled_cell.font = Fonts.PASS
            else:
                enabled_cell.fill = Fills.WARN
                enabled_cell.font = Fonts.WARN
        else:
            enabled_cell.value = "✗ No"
            enabled_cell.fill = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")
        
        # Style Status column (column 7)
        status_cell = ws.cell(row=row, column=7)
        status_cell.value = status
        if "Compliant" in status or (status == "✅ Disabled"):
            status_cell.fill = Fills.PASS
            status_cell.font = Fonts.PASS
        elif "Needs Review" in status:
            status_cell.fill = Fills.WARN
            status_cell.font = Fonts.WARN
            self._increment_warn()
        else:
            pass  # No special styling for neutral status
    
    def _finalize_client_protocols(self) -> None:
        """Finalize client protocols sheet - merge remaining groups."""
        if self._client_protocol_sheet:
            self._finalize_grouping(CLIENT_PROTOCOL_CONFIG.name)
    
    def _add_protocol_dropdowns(self) -> None:
        """Add dropdown validations for choice columns."""
        from autodbaudit.infrastructure.excel.base import (
            add_dropdown_validation, add_review_status_conditional_formatting, STATUS_VALUES
        )
        
        ws = self._client_protocol_sheet
        # Enabled column (F) - column 6 (Action=A, Server=B, Instance=C, Protocol=D, Order=E)
        add_dropdown_validation(ws, "F", ["✓ Yes", "✗ No"])
        # Status column (H) - column 8 (after Enabled=F, Connection=G)
        add_dropdown_validation(ws, "H", ["✅ Compliant", "✅ Disabled", "⚠️ Needs Review", "ℹ️ Disabled", "—"])
        # Review Status column (I) - column 9
        add_dropdown_validation(ws, "I", STATUS_VALUES.all())
        add_review_status_conditional_formatting(ws, "I")
