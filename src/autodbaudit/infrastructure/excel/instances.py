"""
Instances Sheet Module.

Handles the Instances worksheet for SQL Server instance properties.
This sheet provides a high-level overview of all SQL Server instances
being audited, including version information, clustering status, and
server hardware details.

Sheet Purpose:
    - Document all SQL Server instances in scope
    - Track version/edition for compliance and EOL planning
    - Identify clustered and HADR instances
    - Record server IP addresses for network documentation

Columns:
    - Server: Server hostname (grouped visually)
    - IP Address: Server IP for network identification
    - Instance: SQL Server instance name
    - Version: Full version string
    - SQL Year: Mapped year (2019, 2022, etc.)
    - Edition: Enterprise, Standard, Express, etc.
    - Patch Level: RTM, SP1, CU5, etc.
    - Clustered: Whether instance is clustered
    - HADR: AlwaysOn Availability Group enabled
    - OS Version: Windows Server version
    - Notes: Manual notes field

Visual Features:
    - Alternating row colors per server for multi-server reports
    - Boolean icons for Clustered/HADR status
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
    get_sql_year,
)


__all__ = ["InstanceSheetMixin", "INSTANCE_CONFIG"]


# Column definitions with enhanced server information
INSTANCE_COLUMNS = (
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("IP Address", 15, Alignments.CENTER),  # NEW: Server IP
    ColumnDef("Instance", 16, Alignments.LEFT),
    ColumnDef("Version", 14, Alignments.LEFT),
    ColumnDef("SQL Year", 10, Alignments.CENTER),
    ColumnDef("Edition", 30, Alignments.LEFT),
    ColumnDef("Patch Level", 12, Alignments.CENTER),
    ColumnDef("Clustered", 10, Alignments.CENTER),
    ColumnDef("HADR", 8, Alignments.CENTER),
    ColumnDef("OS Version", 22, Alignments.LEFT),  # NEW: Windows version
    ColumnDef("Notes", 35, Alignments.LEFT, is_manual=True),
)

INSTANCE_CONFIG = SheetConfig(name="Instances", columns=INSTANCE_COLUMNS)


class InstanceSheetMixin(BaseSheetMixin):
    """
    Mixin for Instances sheet functionality.
    
    Provides the `add_instance` method to record SQL Server instance
    details including version, edition, and clustering configuration.
    
    Attributes:
        _instance_sheet: Reference to the Instances worksheet
        _last_server: Tracks the last server name for alternating colors
        _server_group_alt: Toggles alternating background per server group
    """
    
    _instance_sheet = None
    _last_server: str = ""
    _server_group_alt: bool = False
    
    def add_instance(
        self,
        server_name: str,
        instance_name: str,
        version: str,
        version_major: int,
        edition: str,
        product_level: str,
        is_clustered: bool = False,
        is_hadr: bool = False,
        ip_address: str = "",
        os_version: str = "",
    ) -> None:
        """
        Add an instance row to the Instances sheet.
        
        Records comprehensive information about a SQL Server instance.
        Rows are visually grouped by server with alternating colors
        when multiple servers are present.
        
        Args:
            server_name: Server hostname (e.g., "SQLPROD01")
            instance_name: SQL instance name (e.g., "MSSQLSERVER" or "INST1")
            version: Full version string (e.g., "16.0.1160.1")
            version_major: Major version number for SQL year mapping
            edition: SQL Server edition (e.g., "Enterprise Edition")
            product_level: Patch level (e.g., "RTM", "SP1", "CU15")
            is_clustered: True if this is a clustered instance
            is_hadr: True if AlwaysOn Availability Groups are enabled
            ip_address: Server IP address (optional, for documentation)
            os_version: Windows Server version (optional)
        
        Example:
            writer.add_instance(
                server_name="SQLPROD01",
                instance_name="",  # Default instance
                version="16.0.1160.1",
                version_major=16,
                edition="Enterprise Edition (64-bit)",
                product_level="RTM",
                is_clustered=False,
                is_hadr=True,
                ip_address="10.0.1.50",
                os_version="Windows Server 2022",
            )
        """
        # Lazy-initialize the worksheet
        if self._instance_sheet is None:
            self._instance_sheet = self._ensure_sheet(INSTANCE_CONFIG)
            self._last_server = ""
            self._server_group_alt = False
        
        ws = self._instance_sheet
        
        # Toggle alternating color when server changes
        if server_name != self._last_server:
            self._server_group_alt = not self._server_group_alt
            self._last_server = server_name
        
        # Prepare row data
        data = [
            server_name,
            ip_address or "",
            instance_name or "(Default)",
            version,
            get_sql_year(version_major),
            edition,
            product_level,
            None,  # Clustered - styled separately
            None,  # HADR - styled separately
            os_version or "",
            "",    # Notes (manual field)
        ]
        
        row = self._write_row(ws, INSTANCE_CONFIG, data)
        
        # Apply alternating background for server grouping
        if self._server_group_alt:
            for col in range(1, len(INSTANCE_COLUMNS) + 1):
                cell = ws.cell(row=row, column=col)
                # Don't override manual field styling
                if not INSTANCE_COLUMNS[col-1].is_manual:
                    cell.fill = Fills.SERVER_ALT
        
        # Apply boolean styling with icons
        apply_boolean_styling(ws.cell(row=row, column=8), is_clustered)
        apply_boolean_styling(ws.cell(row=row, column=9), is_hadr)
