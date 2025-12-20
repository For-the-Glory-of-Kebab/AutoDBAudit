import pytest
from autodbaudit.application.annotation_sync import SHEET_ANNOTATION_CONFIG
from autodbaudit.infrastructure.excel.instances import INSTANCE_COLUMNS
from autodbaudit.infrastructure.excel.logins import LOGIN_COLUMNS
from autodbaudit.infrastructure.excel.roles import (
    ROLE_COLUMNS as SERVER_ROLE_MEMBER_COLUMNS,
)
from autodbaudit.infrastructure.excel.config import CONFIG_COLUMNS
from autodbaudit.infrastructure.excel.services import SERVICE_COLUMNS
from autodbaudit.infrastructure.excel.databases import DATABASE_COLUMNS
from autodbaudit.infrastructure.excel.db_users import DB_USER_COLUMNS
from autodbaudit.infrastructure.excel.db_roles import (
    DB_ROLE_COLUMNS as DB_ROLE_MEMBER_COLUMNS,
)
from autodbaudit.infrastructure.excel.permissions import PERMISSION_COLUMNS
from autodbaudit.infrastructure.excel.orphaned_users import ORPHANED_USER_COLUMNS
from autodbaudit.infrastructure.excel.linked_servers import LINKED_SERVER_COLUMNS
from autodbaudit.infrastructure.excel.triggers import TRIGGER_COLUMNS
from autodbaudit.infrastructure.excel.client_protocols import (
    CLIENT_PROTOCOL_COLUMNS as PROTOCOL_COLUMNS,
)
from autodbaudit.infrastructure.excel.backups import BACKUP_COLUMNS

# Map sheet names to their column definitions
SHEET_COLUMNS_MAP = {
    "Instances": INSTANCE_COLUMNS,
    "Server Logins": LOGIN_COLUMNS,
    "Sensitive Roles": SERVER_ROLE_MEMBER_COLUMNS,
    "Configuration": CONFIG_COLUMNS,
    "Services": SERVICE_COLUMNS,
    "Databases": DATABASE_COLUMNS,
    "Database Users": DB_USER_COLUMNS,
    "Database Roles": DB_ROLE_MEMBER_COLUMNS,
    "Permission Grants": PERMISSION_COLUMNS,
    "Orphaned Users": ORPHANED_USER_COLUMNS,
    "Linked Servers": LINKED_SERVER_COLUMNS,
    "Triggers": TRIGGER_COLUMNS,
    "Client Protocols": PROTOCOL_COLUMNS,
    "Backups": BACKUP_COLUMNS,
}


def test_annotation_config_columns_exist():
    """Verify that all editable_cols in SHEET_ANNOTATION_CONFIG exist in the actual Excel column definitions."""

    for sheet_name, config in SHEET_ANNOTATION_CONFIG.items():
        if sheet_name not in SHEET_COLUMNS_MAP:
            # Skip sheets we haven't imported columns for (e.g. SA Account, Summary, etc if any)
            print(
                f"Skipping verification for {sheet_name} (Columns not mapped in test)"
            )
            continue

        excel_columns = SHEET_COLUMNS_MAP[sheet_name]
        excel_col_names = {col.name for col in excel_columns}

        print(f"Verifying {sheet_name}...")

        for editable_col in config["editable_cols"].keys():
            # Special case: Notes/Comments might be standard but verify name matches exactly
            assert (
                editable_col in excel_col_names
            ), f"Column '{editable_col}' defined in SHEET_ANNOTATION_CONFIG['{sheet_name}'] not found in Excel definition. Available: {sorted(excel_col_names)}"


if __name__ == "__main__":
    # fast run
    try:
        test_annotation_config_columns_exist()
        print("ALL CHECKS PASSED")
    except AssertionError as e:
        print(f"FAILED: {e}")
        exit(1)
