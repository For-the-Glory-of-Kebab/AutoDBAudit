"""
Services Sheet Module.

Handles the Services worksheet for SQL Server services audit.
Groups by Server with color rotation.

Discrepancy Logic:
- Essential services (Database Engine, SQL Agent): Only check account compliance
- Non-essential services (Browser, Integration, Analysis, etc.): Need justification


UUID Support (v3):
    - Column A: Hidden UUID for stable row identification
    - All other columns shifted +1 from original positions
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
    ACTION_COLUMN,
    STATUS_COLUMN,
    LAST_REVIEWED_COLUMN,
    apply_action_needed_styling,
)


__all__ = ["ServiceSheetMixin", "SERVICE_CONFIG"]


SERVICE_COLUMNS = (
    ACTION_COLUMN,  # Column A: Action indicator
    ColumnDef("Server", 16, Alignments.LEFT),
    ColumnDef("Instance", 14, Alignments.LEFT),
    ColumnDef("Service Name", 40, Alignments.LEFT),
    ColumnDef("Type", 18, Alignments.LEFT),
    ColumnDef("Status", 12, Alignments.CENTER),
    ColumnDef("Startup", 12, Alignments.CENTER),
    ColumnDef("Service Account", 35, Alignments.LEFT),
    ColumnDef("Compliant", 10, Alignments.CENTER),
    STATUS_COLUMN,  # Review Status dropdown
    ColumnDef("Justification", 40, Alignments.LEFT, is_manual=True),
    LAST_REVIEWED_COLUMN,
)

SERVICE_CONFIG = SheetConfig(name="Services", columns=SERVICE_COLUMNS)

# Essential services that are expected on a SQL Server (no justification needed)
ESSENTIAL_SERVICE_TYPES = frozenset({
    "database engine",
    "sql agent",
    "sql server",
    "agent",
})

# Non-essential services that need justification if enabled
# These are not strictly required for core SQL Server functionality
NON_ESSENTIAL_SERVICE_TYPES = frozenset({
    "sql browser",
    "full-text search",
    "analysis services",
    "reporting services",
    "integration services",
    "launchpad",
    "launchpad (ml)",
    "vss writer",
    "ceip telemetry",
    "polybase",
    "ad helper",  # Active Directory helper
    "other",
    "other sql service",
})

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
            self._service_sheet = self._ensure_sheet_with_uuid(SERVICE_CONFIG)
            self._svc_last_server = ""
            self._svc_last_instance = ""
            self._svc_server_start_row = 2
            self._svc_instance_start_row = 2
            self._svc_server_idx = 0
            self._svc_instance_alt = False
            self._add_service_dropdowns()
        
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
        
        # Check account compliance - service account should not be virtual
        account_compliant = True
        if service_account:
            acct_lower = service_account.lower().strip()
            if acct_lower in NON_COMPLIANT_ACCOUNTS:
                account_compliant = False
        
        # Check if this is a non-essential service that needs justification
        service_type_lower = (service_type or "").lower().strip()
        is_essential = any(s in service_type_lower for s in ESSENTIAL_SERVICE_TYPES)
        is_non_essential = any(s in service_type_lower for s in NON_ESSENTIAL_SERVICE_TYPES) or not is_essential
        
        # Check if this is specifically SQL Agent
        is_sql_agent = "agent" in service_type_lower or "sql agent" in service_type_lower
        
        # Service is running and enabled? Non-essential services need justification
        is_running = "running" in (status or "").lower()
        is_stopped = "stopped" in (status or "").lower()
        is_auto = "auto" in (startup_type or "").lower()
        is_disabled = "disabled" in (startup_type or "").lower()
        
        # Needs action if:
        # 1. Account is non-compliant (for any service), OR
        # 2. Non-essential service is running/enabled (needs justification), OR
        # 3. SQL Agent is stopped or disabled (Q2: WARNING, may need justification)
        needs_action = (
            not account_compliant or 
            (is_non_essential and is_running and is_auto) or
            (is_sql_agent and (is_stopped or is_disabled))  # Q2: Agent down = discrepancy
        )
        
        # Compliant column should match the action indicator
        # If needs_action = True (⏳), then compliant = False (✗)
        # This prevents confusion where ⏳ shows but Compliant says ✓
        is_compliant = not needs_action
        
        if needs_action:
            self._increment_warn()
        else:
            self._increment_pass()
        
        data = [
            None,  # Action indicator (column A)
            server_name,
            inst_display,
            service_name,
            service_type,
            None,  # Status - styled separately
            None,  # Startup - styled separately
            service_account,
            None,  # Compliant
            "",    # Justification
        ]
        
        row, row_uuid = self._write_row_with_uuid(ws, SERVICE_CONFIG, data)
        
        # Apply action indicator (column 1)
        apply_action_needed_styling(ws.cell(row=row, column=2), needs_action)
        
        # Apply color to data columns (shifted +1 for action column)
        fill = PatternFill(start_color=row_color, end_color=row_color, fill_type="solid")
        for col in [2, 3, 4, 5, 8]:
            ws.cell(row=row, column=col).fill = fill
        
        # Style status column (column 6)
        status_cell = ws.cell(row=row, column=6)
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
        
        # Style startup type column (column 7)
        startup_cell = ws.cell(row=row, column=7)
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
        
        # Style Compliant column (column 9)
        apply_boolean_styling(ws.cell(row=row, column=9), is_compliant)
    
    def _merge_svc_instance(self, ws) -> None:
        """Merge Instance cells for current instance group."""
        current_row = self._row_counters[SERVICE_CONFIG.name]
        if current_row > self._svc_instance_start_row:
            merge_server_cells(
                ws,
                server_col=3,  # Instance column (shifted +1 for action column)
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
                server_col=2,  # Server column (shifted +1 for action column)
                start_row=self._svc_server_start_row,
                end_row=current_row - 1,
                server_name=self._svc_last_server,
                is_alt=True,
            )
            merged = ws.cell(row=self._svc_server_start_row, column=2)
            merged.fill = PatternFill(
                start_color=color_main, end_color=color_main, fill_type="solid"
            )
    
    def _finalize_services(self) -> None:
        """Finalize services sheet."""
        if self._service_sheet and self._svc_last_server:
            self._merge_svc_groups(self._service_sheet)
            self._finalize_sheet_with_uuid(self._service_sheet)
    
    def _add_service_dropdowns(self) -> None:
        """Add dropdown validations for status columns."""
        from autodbaudit.infrastructure.excel.base import (
            add_dropdown_validation, add_review_status_conditional_formatting, STATUS_VALUES
        )
        
        ws = self._service_sheet
        # With UUID: A=UUID, B=Action, C=Server, D=Instance, E=ServiceName, F=Type, G=Status, H=Startup, I=Account, J=Compliant, K=ReviewStatus
        add_dropdown_validation(ws, "G", ["✓ Running", "✗ Stopped", "Unknown"])  # Status
        add_dropdown_validation(ws, "H", ["⚡ Auto", "🔧 Manual", "⛔ Disabled"])  # Startup
        add_dropdown_validation(ws, "J", ["✓", "✗"])  # Compliant
        add_dropdown_validation(ws, "K", STATUS_VALUES.all())  # Review Status
        add_review_status_conditional_formatting(ws, "K")
