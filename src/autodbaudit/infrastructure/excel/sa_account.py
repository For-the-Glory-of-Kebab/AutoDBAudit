"""
SA Account Sheet Module.

Handles the SA Account worksheet for SA account security audit.
"""

from __future__ import annotations

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    apply_boolean_styling,
    apply_status_styling,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
)


__all__ = ["SAAccountSheetMixin", "SA_ACCOUNT_CONFIG"]


SA_ACCOUNT_COLUMNS = (
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Status", 12, Alignments.CENTER, is_status=True),
    ColumnDef("Is Disabled", 12, Alignments.CENTER),
    ColumnDef("Is Renamed", 12, Alignments.CENTER),
    ColumnDef("Current Name", 20, Alignments.LEFT),
    ColumnDef("Default DB", 15, Alignments.LEFT),
    ColumnDef("Remediation Notes", 45, Alignments.LEFT, is_manual=True),
)

SA_ACCOUNT_CONFIG = SheetConfig(name="SA Account", columns=SA_ACCOUNT_COLUMNS)


class SAAccountSheetMixin(BaseSheetMixin):
    """Mixin for SA Account sheet functionality."""
    
    _sa_account_sheet = None
    
    def add_sa_account(
        self,
        server_name: str,
        instance_name: str,
        is_disabled: bool,
        is_renamed: bool,
        current_name: str,
        default_db: str,
    ) -> None:
        """
        Add SA account audit row.
        
        Best practice: SA should be BOTH disabled AND renamed.
        
        Args:
            server_name: Server hostname
            instance_name: SQL Server instance name
            is_disabled: Whether SA login is disabled
            is_renamed: Whether SA has been renamed (e.g., to "$@")
            current_name: Current name of the SA login
            default_db: Default database for the SA login
        """
        if self._sa_account_sheet is None:
            self._sa_account_sheet = self._ensure_sheet(SA_ACCOUNT_CONFIG)
        
        ws = self._sa_account_sheet
        
        # Determine compliance status
        if is_disabled and is_renamed:
            status = "pass"
            self._increment_pass()
        elif is_disabled or is_renamed:
            status = "warn"  # Partial compliance
            self._increment_warn()
        else:
            status = "fail"  # Neither disabled nor renamed
            self._increment_issue()
        
        data = [
            server_name,
            instance_name or "(Default)",
            None,  # Status - styled separately
            None,  # Is Disabled - styled separately
            None,  # Is Renamed - styled separately
            current_name,
            default_db or "",
            "",    # Remediation Notes
        ]
        
        row = self._write_row(ws, SA_ACCOUNT_CONFIG, data)
        
        apply_status_styling(ws.cell(row=row, column=3), status)
        apply_boolean_styling(ws.cell(row=row, column=4), is_disabled)
        apply_boolean_styling(ws.cell(row=row, column=5), is_renamed)
