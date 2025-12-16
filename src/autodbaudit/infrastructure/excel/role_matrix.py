"""
Role Matrix Sheet Module.

Handles the Role Matrix worksheet for a pivoted view of database role memberships.
Requirement #27: Visual Matrix of Login-to-Role Mapping.
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
)
from autodbaudit.infrastructure.excel.server_group import ServerGroupMixin


__all__ = ["RoleMatrixSheetMixin", "ROLE_MATRIX_CONFIG"]


# Fixed roles to show as individual columns
FIXED_ROLES = [
    "db_owner",
    "db_securityadmin",
    "db_accessadmin",
    "db_backupoperator",
    "db_ddladmin",
    "db_datareader",
    "db_datawriter",
    "db_denydatareader",
    "db_denydatawriter",
]

# Column Definitions
# Server, Instance, Database, Principal, Type, [Fixed Roles...], Other Roles, Risk
# NOTE: Role Matrix is info-only (Q3 decision). Justifications go in Database Roles sheet.
ROLE_MATRIX_COLUMNS = [
    ColumnDef("Server", 18, Alignments.LEFT),
    ColumnDef("Instance", 15, Alignments.LEFT),
    ColumnDef("Database", 20, Alignments.LEFT),
    ColumnDef("Principal Name", 25, Alignments.LEFT),
    ColumnDef("Principal Type", 18, Alignments.CENTER),
]

# Add columns for each fixed role (narrow, centered)
for role in FIXED_ROLES:
    # Use shorter headers if needed, or rotate text in final styler if we were fancy
    # For now, just the name. 12 width fits most.
    ROLE_MATRIX_COLUMNS.append(ColumnDef(role, 12, Alignments.CENTER))

# Catch-all for custom roles
ROLE_MATRIX_COLUMNS.append(ColumnDef("Other Roles", 40, Alignments.LEFT))
ROLE_MATRIX_COLUMNS.append(ColumnDef("Risk", 12, Alignments.CENTER))

ROLE_MATRIX_CONFIG = SheetConfig(name="Role Matrix", columns=tuple(ROLE_MATRIX_COLUMNS))


class RoleMatrixSheetMixin(ServerGroupMixin, BaseSheetMixin):
    """Mixin for Role Matrix sheet."""

    _role_matrix_sheet = None

    def add_role_matrix_row(
        self,
        server_name: str,
        instance_name: str,
        database_name: str,
        principal_name: str,
        principal_type: str,
        roles: list[str],
    ) -> None:
        """
        Add a matrix row for a principal.

        Args:
            server_name: Server hostname
            instance_name: Instance name
            database_name: Database name
            principal_name: User/Principal name
            principal_type: SQL_USER, WINDOWS_USER, etc.
            roles: List of role names this user belongs to
        """
        if self._role_matrix_sheet is None:
            self._role_matrix_sheet = self._ensure_sheet(ROLE_MATRIX_CONFIG)
            self._init_grouping(self._role_matrix_sheet, ROLE_MATRIX_CONFIG)

        ws = self._role_matrix_sheet

        # Track grouping and get row color
        row_color = self._track_group(
            server_name, instance_name, ROLE_MATRIX_CONFIG.name
        )

        # Prepare Role Flags
        roles_lower = {r.lower() for r in roles}

        # Format Principal Type
        type_upper = (principal_type or "").upper()
        if "WINDOWS" in type_upper:
            type_display = "🪟 Windows"
        elif "SQL" in type_upper:
            type_display = "👤 SQL"
        elif "CERTIFICATE" in type_upper:
            type_display = "📜 Cert"
        elif "ASYMMETRIC" in type_upper:
            type_display = "🔑 Key"
        elif "ROLE" in type_upper:
            type_display = "📦 Role"
        else:
            type_display = principal_type

        row_data = [
            server_name,
            instance_name or "(Default)",
            database_name,
            principal_name,
            type_display,
        ]

        # Add column for each fixed role
        has_high_risk = False
        for fixed_role in FIXED_ROLES:
            if fixed_role in roles_lower:
                if fixed_role == "db_owner" and principal_name.lower() != "dbo":
                    row_data.append("👑 YES")
                    has_high_risk = True
                else:
                    row_data.append("✓")
            else:
                row_data.append("")  # Empty if not member

        # Other Roles (non-fixed)
        other_roles = [r for r in roles if r.lower() not in FIXED_ROLES]
        row_data.append(", ".join(sorted(other_roles)))

        # Risk
        if has_high_risk:
            row_data.append("🔴 High")
        else:
            row_data.append("—")

        row = self._write_row(ws, ROLE_MATRIX_CONFIG, row_data)

        # Apply row color (no action column now, Server is column 1)
        # Meta columns: 1=Server, 2=Instance, 3=Database, 4=Principal, 5=Type, last=Risk
        meta_cols = [1, 2, 3, 4, 5, len(ROLE_MATRIX_COLUMNS)]  # Server...Type + Risk
        self._apply_row_color(row, row_color, data_cols=meta_cols, ws=ws)

        # Style Matrix Cells (if checked)
        # Matrix columns are from index 7 to 7+len(FIXED_ROLES)-1 (1-based, shifted +1)
        start_col = 7
        for i, fixed_role in enumerate(FIXED_ROLES):
            if fixed_role in roles_lower:
                cell = ws.cell(row=row, column=start_col + i)
                cell.alignment = Alignments.CENTER
                if fixed_role == "db_owner" and principal_name.lower() != "dbo":
                    cell.fill = Fills.FAIL
                    cell.font = Fonts.FAIL
                else:
                    cell.font = Fonts.PASS  # Checkmark in green

        # Style Risk
        risk_col_idx = len(ROLE_MATRIX_COLUMNS)  # Last column
        risk_cell = ws.cell(row=row, column=risk_col_idx)
        if has_high_risk:
            risk_cell.fill = Fills.FAIL
            risk_cell.font = Fonts.FAIL
        else:
            risk_cell.fill = PatternFill(
                start_color="F5F5F5", end_color="F5F5F5", fill_type="solid"
            )

    def _finalize_role_matrix(self) -> None:
        """Finalize permissions sheet."""
        if self._role_matrix_sheet:
            self._finalize_grouping(ROLE_MATRIX_CONFIG.name)
