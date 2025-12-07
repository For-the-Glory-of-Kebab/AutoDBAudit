"""
Server Logins Sheet Module.

Handles the Server Logins worksheet for SQL Server login audit.
This sheet provides a comprehensive inventory of all server-level
logins including security status assessment.

Sheet Purpose:
    - Document all SQL Server logins
    - Identify security risks (enabled SA, missing password policies)
    - Track login types (SQL, Windows, Certificate)
    - Flag disabled and problematic logins

Security Checks:
    - SA account should be disabled
    - SQL logins should have password policy enforced
    - SQL logins should have password expiration enabled
    - Empty passwords are critical vulnerabilities

Visual Features:
    - Alternating row colors per server for multi-server reports
    - Status column with Pass/Fail icons
    - Boolean icons for security settings
    - Gray background for manual notes column
"""

from __future__ import annotations

from autodbaudit.infrastructure.excel_styles import (
    ColumnDef,
    Alignments,
    Fills,
    apply_boolean_styling,
    apply_status_styling,
)
from autodbaudit.infrastructure.excel.base import (
    BaseSheetMixin,
    SheetConfig,
)


__all__ = ["LoginSheetMixin", "LOGIN_CONFIG"]


LOGIN_COLUMNS = (
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Login Name", 28, Alignments.LEFT),
    ColumnDef("Type", 18, Alignments.LEFT),
    ColumnDef("Disabled", 10, Alignments.CENTER),
    ColumnDef("SA Account", 10, Alignments.CENTER),
    ColumnDef("Pwd Policy", 10, Alignments.CENTER),
    ColumnDef("Default DB", 14, Alignments.LEFT),
    ColumnDef("Status", 10, Alignments.CENTER, is_status=True),
    ColumnDef("Notes", 35, Alignments.LEFT, is_manual=True),
)

LOGIN_CONFIG = SheetConfig(name="Server Logins", columns=LOGIN_COLUMNS)


class LoginSheetMixin(BaseSheetMixin):
    """
    Mixin for Server Logins sheet functionality.
    
    Provides the `add_login` method to record SQL Server logins
    with security assessment. Each login is checked against
    security best practices.
    
    Security Rules Applied:
        - SA account enabled without being disabled = FAIL
        - SQL logins without password policy = WARN
        - All other logins = PASS
    
    Attributes:
        _login_sheet: Reference to the Server Logins worksheet
        _login_count: Counter for number of logins processed
        _login_last_server: Tracks server for alternating colors
        _login_alt: Toggles alternating background per server
    """
    
    _login_sheet = None
    _login_count: int = 0
    _login_last_server: str = ""
    _login_alt: bool = False
    
    def add_login(
        self,
        server_name: str,
        instance_name: str,
        login_name: str,
        login_type: str,
        is_disabled: bool,
        is_sa: bool,
        pwd_policy: bool | None,
        default_db: str,
    ) -> None:
        """
        Add a server login row with security assessment.
        
        Each login is automatically assessed for security compliance:
        - SA account that is not disabled triggers a FAIL status
        - Other logins get PASS status
        
        Args:
            server_name: Server hostname
            instance_name: SQL Server instance name
            login_name: Login name (e.g., "sa", "DOMAIN\\User")
            login_type: Type of login:
                - "SQL_LOGIN" - SQL Server authentication
                - "WINDOWS_LOGIN" - Windows authentication
                - "CERTIFICATE_MAPPED_LOGIN" - Certificate mapped
                - "ASYMMETRIC_KEY_MAPPED_LOGIN" - Asymmetric key mapped
            is_disabled: True if the login is disabled
            is_sa: True if this is the SA account (SID 0x01)
            pwd_policy: True if password policy enforced (None for Windows)
            default_db: Default database for the login
        
        Example:
            writer.add_login(
                server_name="SQLPROD01",
                instance_name="",
                login_name="app_service",
                login_type="SQL_LOGIN",
                is_disabled=False,
                is_sa=False,
                pwd_policy=True,
                default_db="ApplicationDB",
            )
        """
        # Lazy-initialize the worksheet
        if self._login_sheet is None:
            self._login_sheet = self._ensure_sheet(LOGIN_CONFIG)
            self._login_last_server = ""
            self._login_alt = False
        
        ws = self._login_sheet
        
        # Toggle alternating color when server changes
        if server_name != self._login_last_server:
            self._login_alt = not self._login_alt
            self._login_last_server = server_name
        
        # Determine security status
        # SA should be disabled - if enabled, it's a critical issue
        status = "fail" if is_sa and not is_disabled else "pass"
        if status == "fail":
            self._increment_issue()
        else:
            self._increment_pass()
        
        # Prepare row data
        data = [
            server_name,
            instance_name or "(Default)",
            login_name,
            login_type,
            None,  # Disabled - styled separately
            None,  # SA Account - styled separately
            None,  # Pwd Policy - styled separately
            default_db or "",
            None,  # Status - styled separately
            "",    # Notes (manual)
        ]
        
        row = self._write_row(ws, LOGIN_CONFIG, data)
        
        # Apply alternating background for server grouping
        if self._login_alt:
            for col in range(1, len(LOGIN_COLUMNS) + 1):
                cell = ws.cell(row=row, column=col)
                if not LOGIN_COLUMNS[col-1].is_manual and not LOGIN_COLUMNS[col-1].is_status:
                    cell.fill = Fills.SERVER_ALT
        
        # Apply boolean styling with icons
        apply_boolean_styling(ws.cell(row=row, column=5), is_disabled)
        apply_boolean_styling(ws.cell(row=row, column=6), is_sa, invert=True)
        apply_boolean_styling(ws.cell(row=row, column=7), pwd_policy)
        apply_status_styling(ws.cell(row=row, column=9), status)
        
        self._login_count += 1
