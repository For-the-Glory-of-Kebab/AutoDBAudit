"""
Services Sheet Module.

Handles the Services worksheet for SQL Server services audit.
Groups by Server with color rotation.
"""

from __future__ import annotations

from openpyxl.styles import PatternFill

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    Fonts,
    Fills,
    apply_boolean_styling,
    merge_server_cells,
    SERVER_GROUP_COLORS,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
)


__all__ = ["ServiceSheetMixin", "SERVICE_CONFIG"]


SERVICE_COLUMNS = (
    ColumnDef("Server", 16, Alignments.LEFT),
    ColumnDef("Instance", 14, Alignments.LEFT),
    ColumnDef("Service Name", 40, Alignments.LEFT),
    ColumnDef("Type", 18, Alignments.LEFT),
    ColumnDef("Status", 12, Alignments.CENTER),
    ColumnDef("Startup", 12, Alignments.CENTER),
    ColumnDef("Service Account", 35, Alignments.LEFT),
    ColumnDef("Compliant", 10, Alignments.CENTER),
    ColumnDef("Notes", 35, Alignments.LEFT, is_manual=True),
)

SERVICE_CONFIG = SheetConfig(name="Services", columns=SERVICE_COLUMNS)

# Virtual/built-in accounts that are non-compliant per requirements
NON_COMPLIANT_ACCOUNTS = frozenset({
    "localservice",
    "local service",
    "nt authority\\localservice",
    "networkservice", 
    "network service",
    "nt authority\\networkservice",
    "localsystem",
    "local system",
    "nt authority\\system",
    "nt authority\\local service",
    "nt authority\\network service",
})


class ServiceSheetMixin(BaseSheetMixin):
    """Mixin for Services sheet with server grouping."""
    
    _service_sheet = None
    _svc_last_server: str = ""
    _svc_last_instance: str = ""
    _svc_server_start_row: int = 2
    _svc_instance_start_row: int = 2
    _svc_server_idx: int = 0
    _svc_instance_alt: bool = False
    
    def add_service(
        self,
        server_name: str,
        instance_name: str,
        service_name: str,
        service_type: str,
        status: str,
        startup_type: str,
        service_account: str,
    ) -> None:
        """Add a SQL service row."""
        if self._service_sheet is None:
            self._service_sheet = self._ensure_sheet(SERVICE_CONFIG)
            self._svc_last_server = ""
            self._svc_last_instance = ""
            self._svc_server_start_row = 2
            self._svc_instance_start_row = 2
            self._svc_server_idx = 0
            self._svc_instance_alt = False
        
        ws = self._service_sheet
        current_row = self._row_counters[SERVICE_CONFIG.name]
        inst_display = instance_name or "(Default)"
        
        # Check if server changed
        if server_name != self._svc_last_server:
            if self._svc_last_server:
                self._merge_svc_groups(ws)
                self._svc_server_idx += 1
            
            self._svc_server_start_row = current_row
            self._svc_instance_start_row = current_row
            self._svc_last_server = server_name
            self._svc_last_instance = inst_display
            self._svc_instance_alt = False
        elif inst_display != self._svc_last_instance:
            self._merge_svc_instance(ws)
            self._svc_instance_start_row = current_row
            self._svc_last_instance = inst_display
            self._svc_instance_alt = not self._svc_instance_alt
        
        color_main, color_light = SERVER_GROUP_COLORS[
            self._svc_server_idx % len(SERVER_GROUP_COLORS)
        ]
        row_color = color_main if self._svc_instance_alt else color_light
        
        # Check compliance - service account should not be virtual
        is_compliant = True
        if service_account:
            acct_lower = service_account.lower().strip()
            if acct_lower in NON_COMPLIANT_ACCOUNTS:
                is_compliant = False
        
        if is_compliant:
            self._increment_pass()
        else:
            self._increment_warn()
        
        data = [
            server_name,
            inst_display,
            service_name,
            service_type,
            None,  # Status - styled separately
            None,  # Startup - styled separately
            service_account,
            None,  # Compliant
            "",    # Notes
        ]
        
        row = self._write_row(ws, SERVICE_CONFIG, data)
        
        # Apply color to data columns
        fill = PatternFill(start_color=row_color, end_color=row_color, fill_type="solid")
        for col in [1, 2, 3, 4, 7]:
            ws.cell(row=row, column=col).fill = fill
        
        # Style status column (column 5)
        status_cell = ws.cell(row=row, column=5)
        status_lower = (status or "").lower()
        if "running" in status_lower:
            status_cell.value = "✓ Running"
            status_cell.fill = Fills.PASS
            status_cell.font = Fonts.PASS
        elif "stopped" in status_lower:
            status_cell.value = "✗ Stopped"
            status_cell.fill = Fills.WARN
            status_cell.font = Fonts.WARN
        else:
            status_cell.value = status or "Unknown"
        
        # Style startup type column (column 6)
        startup_cell = ws.cell(row=row, column=6)
        startup_lower = (startup_type or "").lower()
        if "auto" in startup_lower:
            startup_cell.value = "⚡ Auto"
            startup_cell.fill = Fills.PASS
        elif "manual" in startup_lower:
            startup_cell.value = "🔧 Manual"
            startup_cell.fill = PatternFill(start_color="FFF3E0", end_color="FFF3E0", fill_type="solid")
        elif "disabled" in startup_lower:
            startup_cell.value = "⛔ Disabled"
            startup_cell.fill = Fills.WARN
        else:
            startup_cell.value = startup_type or ""
        
        apply_boolean_styling(ws.cell(row=row, column=8), is_compliant)
    
    def _merge_svc_instance(self, ws) -> None:
        """Merge Instance cells for current instance group."""
        current_row = self._row_counters[SERVICE_CONFIG.name]
        if current_row > self._svc_instance_start_row:
            merge_server_cells(
                ws,
                server_col=2,
                start_row=self._svc_instance_start_row,
                end_row=current_row - 1,
                server_name=self._svc_last_instance,
                is_alt=self._svc_instance_alt,
            )
    
    def _merge_svc_groups(self, ws) -> None:
        """Merge both Server and Instance cells."""
        self._merge_svc_instance(ws)
        current_row = self._row_counters[SERVICE_CONFIG.name]
        if current_row > self._svc_server_start_row:
            color_main, _ = SERVER_GROUP_COLORS[
                self._svc_server_idx % len(SERVER_GROUP_COLORS)
            ]
            merge_server_cells(
                ws,
                server_col=1,
                start_row=self._svc_server_start_row,
                end_row=current_row - 1,
                server_name=self._svc_last_server,
                is_alt=True,
            )
            merged = ws.cell(row=self._svc_server_start_row, column=1)
            merged.fill = PatternFill(
                start_color=color_main, end_color=color_main, fill_type="solid"
            )
    
    def _finalize_services(self) -> None:
        """Finalize services sheet."""
        if self._service_sheet and self._svc_last_server:
            self._merge_svc_groups(self._service_sheet)
