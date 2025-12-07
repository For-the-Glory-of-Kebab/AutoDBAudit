"""
Services Sheet Module.

Handles the Services worksheet for SQL Server services audit.
"""

from __future__ import annotations

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    apply_boolean_styling,
    apply_service_status_styling,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
)


__all__ = ["ServiceSheetMixin", "SERVICE_CONFIG"]


SERVICE_COLUMNS = (
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Service Type", 18, Alignments.LEFT),
    ColumnDef("Service Name", 35, Alignments.LEFT),
    ColumnDef("Status", 12, Alignments.CENTER),
    ColumnDef("Startup Type", 12, Alignments.CENTER),
    ColumnDef("Service Account", 35, Alignments.LEFT),
    ColumnDef("Compliant", 10, Alignments.CENTER),
    ColumnDef("Notes", 40, Alignments.LEFT, is_manual=True),
)

SERVICE_CONFIG = SheetConfig(name="Services", columns=SERVICE_COLUMNS)


class ServiceSheetMixin(BaseSheetMixin):
    """Mixin for Services sheet functionality."""
    
    _service_sheet = None
    
    def add_service(
        self,
        server_name: str,
        service_type: str,
        service_name: str,
        status: str,
        startup_type: str,
        service_account: str,
        is_compliant: bool,
    ) -> None:
        """
        Add a SQL service row.
        
        Args:
            server_name: Server hostname
            service_type: Type of service (Engine, Agent, SSRS, etc.)
            service_name: Windows service name
            status: Current status (Running, Stopped, etc.)
            startup_type: Startup type (Automatic, Manual, Disabled)
            service_account: Service account running the service
            is_compliant: Whether the service configuration is compliant
        """
        if self._service_sheet is None:
            self._service_sheet = self._ensure_sheet(SERVICE_CONFIG)
        
        ws = self._service_sheet
        
        if is_compliant:
            self._increment_pass()
        else:
            self._increment_warn()
        
        data = [
            server_name,
            service_type,
            service_name,
            None,  # Status - styled separately
            startup_type,
            service_account,
            None,  # Compliant - styled separately
            "",    # Notes
        ]
        
        row = self._write_row(ws, SERVICE_CONFIG, data)
        
        apply_service_status_styling(ws.cell(row=row, column=4), status)
        apply_boolean_styling(ws.cell(row=row, column=7), is_compliant)
