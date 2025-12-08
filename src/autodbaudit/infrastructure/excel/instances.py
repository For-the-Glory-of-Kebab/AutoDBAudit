"""
Instances Sheet Module.

Handles the Instances worksheet for SQL Server instance properties.
Visual grouping with rotating colors for different servers.
"""

from __future__ import annotations

from openpyxl.styles import PatternFill

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    apply_boolean_styling,
    merge_server_cells,
    SERVER_GROUP_COLORS,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
    get_sql_year,
    LAST_REVISED_COLUMN,
)


__all__ = ["InstanceSheetMixin", "INSTANCE_CONFIG"]


INSTANCE_COLUMNS = (
    ColumnDef("Config Name", 22, Alignments.LEFT),  # From display_name
    ColumnDef("Server", 18, Alignments.LEFT),  # Connection target
    ColumnDef("Instance", 12, Alignments.LEFT),
    ColumnDef("Machine Name", 16, Alignments.LEFT),  # From SERVERPROPERTY
    ColumnDef("IP Address", 16, Alignments.LEFT),  # From dm_exec_connections
    ColumnDef("Version", 12, Alignments.LEFT),
    ColumnDef("Build", 14, Alignments.LEFT),
    ColumnDef("SQL Year", 8, Alignments.CENTER),
    ColumnDef("Edition", 20, Alignments.LEFT),
    ColumnDef("Clustered", 8, Alignments.CENTER),
    ColumnDef("HADR", 6, Alignments.CENTER),
    ColumnDef("OS", 18, Alignments.LEFT),
    ColumnDef("CPU", 4, Alignments.CENTER),
    ColumnDef("RAM", 5, Alignments.CENTER),
    ColumnDef("Notes", 24, Alignments.LEFT, is_manual=True),
    LAST_REVISED_COLUMN,
)

INSTANCE_CONFIG = SheetConfig(name="Instances", columns=INSTANCE_COLUMNS)


class InstanceSheetMixin(BaseSheetMixin):
    """Mixin for Instances sheet functionality."""
    
    _instance_sheet = None
    _instance_last_server: str = ""
    _instance_server_start_row: int = 2
    _instance_server_idx: int = 0
    
    def add_instance(
        self,
        config_name: str,  # NEW: display_name from config
        server_name: str,  # Connection target (localhost, localhost,1434)
        instance_name: str,
        machine_name: str,  # NEW: from SERVERPROPERTY('MachineName')
        ip_address: str,  # From dm_exec_connections
        tcp_port: int | None,
        version: str,
        version_major: int,
        edition: str,
        product_level: str,
        is_clustered: bool = False,
        is_hadr: bool = False,
        os_info: str = "",
        cpu_count: int | None = None,
        memory_gb: int | None = None,
        cu_level: str = "",
        build_number: int | None = None,
    ) -> None:
        """Add an instance row to the Instances sheet."""
        if self._instance_sheet is None:
            self._instance_sheet = self._ensure_sheet(INSTANCE_CONFIG)
            self._instance_last_server = ""
            self._instance_server_start_row = 2
            self._instance_server_idx = 0
            self._add_instance_dropdowns()
        
        ws = self._instance_sheet
        current_row = self._row_counters[INSTANCE_CONFIG.name]
        
        # Check if server changed
        if server_name != self._instance_last_server:
            if self._instance_last_server:
                self._merge_instance_server(ws)
                self._instance_server_idx += 1
            
            self._instance_server_start_row = current_row
            self._instance_last_server = server_name
        
        color_main, color_light = SERVER_GROUP_COLORS[
            self._instance_server_idx % len(SERVER_GROUP_COLORS)
        ]
        
        # Build info string
        build_parts = [product_level]
        if cu_level:
            build_parts.append(cu_level)
        if build_number:
            build_parts.append(f"({build_number})")
        build_info = " ".join(build_parts)
        
        # Format IP with port
        ip_display = ip_address or ""
        if ip_display and tcp_port:
            ip_display = f"{ip_address}:{tcp_port}"
        elif tcp_port and not ip_display:
            ip_display = f":{tcp_port}"  # Just port if no IP
        
        data = [
            config_name,  # Config Name
            server_name,  # Server (connection target)
            instance_name or "(Default)",
            machine_name or "",  # Machine Name
            ip_display,  # IP Address
            version,
            build_info,
            get_sql_year(version_major),
            edition,
            None,  # Clustered
            None,  # HADR
            os_info or "",
            str(cpu_count) if cpu_count else "",
            str(memory_gb) if memory_gb else "",
            "",    # Notes
            "",    # Last Revised
        ]
        
        row = self._write_row(ws, INSTANCE_CONFIG, data)
        
        fill = PatternFill(start_color=color_light, end_color=color_light, fill_type="solid")
        # All data columns except Clustered (10), HADR (11), manual columns
        for col in [1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 13, 14]:
            ws.cell(row=row, column=col).fill = fill
        
        apply_boolean_styling(ws.cell(row=row, column=10), is_clustered)
        apply_boolean_styling(ws.cell(row=row, column=11), is_hadr)
    
    def _merge_instance_server(self, ws) -> None:
        """Merge Server cells for current server group."""
        current_row = self._row_counters[INSTANCE_CONFIG.name]
        if current_row > self._instance_server_start_row:
            color_main, _ = SERVER_GROUP_COLORS[
                self._instance_server_idx % len(SERVER_GROUP_COLORS)
            ]
            merge_server_cells(
                ws,
                server_col=2,  # Server column (was 1)
                start_row=self._instance_server_start_row,
                end_row=current_row - 1,
                server_name=self._instance_last_server,
                is_alt=True,
            )
            merged_cell = ws.cell(row=self._instance_server_start_row, column=2)
            merged_cell.fill = PatternFill(
                start_color=color_main, end_color=color_main, fill_type="solid"
            )
    
    def _finalize_instances(self) -> None:
        """Finalize instances sheet - merge remaining server group."""
        if self._instance_sheet and self._instance_last_server:
            self._merge_instance_server(self._instance_sheet)
    
    def _add_instance_dropdowns(self) -> None:
        """Add dropdown validations for boolean columns."""
        from autodbaudit.infrastructure.excel.base import add_dropdown_validation
        
        ws = self._instance_sheet
        # Clustered column (J) - column 10
        add_dropdown_validation(ws, "J", ["✓", "✗"])
        # HADR column (K) - column 11
        add_dropdown_validation(ws, "K", ["✓", "✗"])
