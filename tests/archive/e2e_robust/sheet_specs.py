"""
Sheet Roundtrip Test Infrastructure.

Defines per-sheet test specifications for comprehensive E2E validation.
Each sheet has:
- Key columns (how to identify rows)
- Editable columns (what user can edit)
- Sample data (for writing to Excel via real writer)
- Expected annotations (after reading back)

This integrates with e2e_robust to provide comprehensive coverage.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class SheetTestSpec:
    """Specification for testing a single sheet's roundtrip."""

    # Sheet identity
    sheet_name: str
    entity_type: str

    # Columns that make up the key (for matching)
    key_cols: List[str]

    # Editable columns: {Excel Header -> DB field name}
    editable_cols: Dict[str, str]

    # Writer method name (e.g., "add_login")
    writer_method: str

    # Sample write data (kwargs for writer method)
    sample_data: Dict[str, Any] = field(default_factory=dict)

    # Annotations to add (after write, before read)
    # {Row: {Column: Value}}
    annotations_to_add: Dict[int, Dict[str, str]] = field(default_factory=dict)

    # Expected entity key format (lowercase)
    expected_key_pattern: str = ""

    # Does this sheet have exceptions? (FAIL rows with justification)
    supports_exceptions: bool = True

    # If true, also test exception detection
    test_exception_detection: bool = True


# ============================================================================
# SHEET SPECIFICATIONS - ONE PER SHEET
# ============================================================================

SHEET_SPECS: List[SheetTestSpec] = [
    SheetTestSpec(
        sheet_name="Server Logins",
        entity_type="login",
        key_cols=["Server", "Instance", "Login Name"],
        editable_cols={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Revised": "last_reviewed",
            "Notes": "notes",
        },
        writer_method="add_login",
        sample_data={
            "server_name": "TestServer",
            "instance_name": "INST1",
            "login_name": "test_login",
            "login_type": "SQL Login",
            "is_disabled": False,
            "pwd_policy": False,  # FAIL - triggers action
            "default_db": "master",
        },
        annotations_to_add={
            2: {"Justification": "Test exception", "Review Status": "✓ Exception"}
        },
        expected_key_pattern="login|testserver|inst1|test_login",
    ),
    SheetTestSpec(
        sheet_name="SA Account",
        entity_type="sa_account",
        key_cols=["Server", "Instance", "Current Name"],
        editable_cols={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
            "Notes": "notes",
        },
        writer_method="add_sa_account",
        sample_data={
            "server_name": "TestServer",
            "instance_name": "INST1",
            "is_disabled": False,
            "is_renamed": False,
            "current_name": "sa",
            "default_db": "master",
        },
        annotations_to_add={
            2: {
                "Justification": "Legacy app requires sa",
                "Review Status": "✓ Exception",
            }
        },
        expected_key_pattern="sa_account|testserver|inst1|sa",
    ),
    SheetTestSpec(
        sheet_name="Sensitive Roles",
        entity_type="server_role_member",
        key_cols=["Server", "Instance", "Member"],
        editable_cols={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Revised": "last_reviewed",
            # No Notes column in Excel
        },
        writer_method="add_role_member",  # Fixed method name
        sample_data={
            "server_name": "TestServer",
            "instance_name": "INST1",
            "role_name": "sysadmin",
            "member_name": "admin_user",
            "member_type": "SQL Login",
            "is_disabled": False,
        },
        annotations_to_add={
            2: {"Justification": "DBA team member", "Review Status": "✓ Exception"}
        },
        expected_key_pattern="server_role_member|testserver|inst1|admin_user",
    ),
    SheetTestSpec(
        sheet_name="Configuration",
        entity_type="config",
        key_cols=["Server", "Instance", "Setting"],
        editable_cols={
            "Review Status": "review_status",
            "Exception Reason": "justification",  # Different column name!
            "Last Reviewed": "last_reviewed",
            # No Notes column in Excel
        },
        writer_method="add_config_setting",
        sample_data={
            "server_name": "TestServer",
            "instance_name": "INST1",
            "setting_name": "xp_cmdshell",
            "current_value": 1,  # Fixed: was configured_value
            "required_value": 0,
            "risk_level": "high",
        },
        annotations_to_add={
            2: {
                "Exception Reason": "Required for maintenance",
                "Review Status": "✓ Exception",
            }
        },
        expected_key_pattern="config|testserver|inst1|xp_cmdshell",
    ),
    SheetTestSpec(
        sheet_name="Backups",
        entity_type="backup",
        key_cols=["Server", "Instance", "Database", "Recovery Model"],
        editable_cols={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
            "Notes": "notes",
        },
        writer_method="add_backup_info",
        sample_data={
            "server_name": "TestServer",
            "instance_name": "INST1",
            "database_name": "AppDB",
            "recovery_model": "FULL",
            "last_backup_date": None,  # No backup = FAIL
            "days_since": None,
            "backup_path": "",
            "backup_size_mb": None,
        },
        annotations_to_add={
            2: {
                "Justification": "Dev DB - no backup needed",
                "Review Status": "✓ Exception",
            }
        },
        expected_key_pattern="backup|testserver|inst1|appdb|full",
    ),
    SheetTestSpec(
        sheet_name="Linked Servers",
        entity_type="linked_server",
        key_cols=["Server", "Instance", "Linked Server"],
        editable_cols={
            "Review Status": "review_status",
            "Purpose": "purpose",
            "Justification": "justification",
            "Last Revised": "last_reviewed",
            # No Notes column in Excel
        },
        writer_method="add_linked_server",
        sample_data={
            "server_name": "TestServer",
            "instance_name": "INST1",
            "linked_server_name": "REMOTE_DB",
            "product": "SQL Server",
            "provider": "SQLNCLI11",
            "data_source": "remotehost",
            "rpc_out": True,
            "risk_level": "HIGH_PRIVILEGE",
        },
        annotations_to_add={
            2: {
                "Purpose": "Legacy reporting",
                "Justification": "Required for reports",
                "Review Status": "✓ Exception",
            }
        },
        expected_key_pattern="linked_server|testserver|inst1|remote_db",
    ),
    SheetTestSpec(
        sheet_name="Database Roles",
        entity_type="db_role",
        key_cols=["Server", "Instance", "Database", "Role", "Member"],
        editable_cols={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
            # No Notes column in Excel
        },
        writer_method="add_db_role_member",
        sample_data={
            "server_name": "TestServer",
            "instance_name": "INST1",
            "database_name": "AppDB",
            "role_name": "db_owner",
            "member_name": "app_user",
            "member_type": "SQL User",
        },
        annotations_to_add={
            2: {"Justification": "App needs db_owner", "Review Status": "✓ Exception"}
        },
        expected_key_pattern="db_role|testserver|inst1|appdb|db_owner|app_user",
    ),
    SheetTestSpec(
        sheet_name="Databases",
        entity_type="database",
        key_cols=["Server", "Instance", "Database"],
        editable_cols={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
            "Notes": "notes",
        },
        writer_method="add_database",
        sample_data={
            "server_name": "TestServer",
            "instance_name": "INST1",
            "database_name": "AppDB",
            "owner": "sa",
            "recovery_model": "SIMPLE",
            "state": "ONLINE",
            "data_size_mb": 100.0,
            "log_size_mb": 10.0,
            "is_trustworthy": True,  # FAIL condition
        },
        annotations_to_add={2: {"Notes": "Legacy database"}},
        expected_key_pattern="database|testserver|inst1|appdb",
        test_exception_detection=False,  # No exception, just notes
    ),
    SheetTestSpec(
        sheet_name="Triggers",
        entity_type="trigger",
        key_cols=["Server", "Instance", "Database", "Trigger Name"],
        editable_cols={
            "Purpose": "purpose",
            # No Notes column in Excel
        },
        writer_method="add_trigger",
        sample_data={
            "server_name": "TestServer",
            "instance_name": "INST1",
            "level": "DATABASE",  # Fixed: was trigger_type
            "database_name": "AppDB",
            "trigger_name": "trg_audit",
            "event_type": "ALTER_TABLE",  # Fixed: was trigger_events
            "is_enabled": True,
        },
        annotations_to_add={2: {"Purpose": "Audit logging trigger"}},
        expected_key_pattern="trigger|testserver|inst1|appdb|trg_audit",
        supports_exceptions=False,  # Triggers don't have exceptions
        test_exception_detection=False,
    ),
    SheetTestSpec(
        sheet_name="Database Users",
        entity_type="db_user",
        key_cols=["Server", "Instance", "Database", "User Name"],
        editable_cols={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
            "Notes": "notes",
        },
        writer_method="add_db_user",
        sample_data={
            "server_name": "TestServer",
            "instance_name": "INST1",
            "database_name": "AppDB",
            "user_name": "app_user",
            "user_type": "SQL User",
            "mapped_login": "app_login",  # Fixed
            "is_orphaned": False,  # Fixed
        },
        annotations_to_add={2: {"Notes": "Application service account"}},
        expected_key_pattern="db_user|testserver|inst1|appdb|app_user",
        test_exception_detection=False,
    ),
    SheetTestSpec(
        sheet_name="Services",
        entity_type="service",
        key_cols=["Server", "Instance", "Service Name"],
        editable_cols={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
            # No Notes column in Excel
        },
        writer_method="add_service",
        sample_data={
            "server_name": "TestServer",
            "instance_name": "INST1",
            "service_name": "MSSQLSERVER",
            "service_type": "SQL Server",
            "status": "Running",
            "startup_type": "Automatic",
            "service_account": "NT Service\\MSSQLSERVER",
            # Removed is_compliant - not a param
        },
        annotations_to_add={},
        expected_key_pattern="service|testserver|inst1|mssqlserver",
        test_exception_detection=False,
    ),
    SheetTestSpec(
        sheet_name="Permission Grants",
        entity_type="permission",
        key_cols=["Server", "Instance", "Scope", "Grantee", "Permission"],
        editable_cols={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
            "Notes": "notes",
        },
        writer_method="add_permission",
        sample_data={
            "server_name": "TestServer",
            "instance_name": "INST1",
            "scope": "SERVER",
            "database_name": "",  # Empty for SERVER scope
            "grantee_name": "app_user",  # Fixed
            "permission_name": "ALTER ANY LOGIN",  # Fixed
            "state": "GRANT",
            "entity_name": "",  # Fixed
            # Removed entity_type and risk_level - not params
        },
        annotations_to_add={
            2: {"Justification": "Required for admin", "Review Status": "✓ Exception"}
        },
        expected_key_pattern="permission|testserver|inst1|server|app_user|alter any login",
    ),
    SheetTestSpec(
        sheet_name="Orphaned Users",
        entity_type="orphaned_user",
        key_cols=["Server", "Instance", "Database", "User Name"],
        editable_cols={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Revised": "last_reviewed",
            # No Notes column in Excel
        },
        writer_method="add_orphaned_user",
        sample_data={
            "server_name": "TestServer",
            "instance_name": "INST1",
            "database_name": "AppDB",
            "user_name": "orphan_user",
            "user_type": "SQL User",
        },
        annotations_to_add={
            2: {
                "Justification": "Scheduled for cleanup",
                "Review Status": "✓ Exception",
            }
        },
        expected_key_pattern="orphaned_user|testserver|inst1|appdb|orphan_user",
    ),
    SheetTestSpec(
        sheet_name="Audit Settings",
        entity_type="audit_settings",
        key_cols=["Server", "Instance", "Setting"],
        editable_cols={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
            "Notes": "notes",
        },
        writer_method="add_audit_setting",
        sample_data={
            "server_name": "TestServer",
            "instance_name": "INST1",
            "setting_name": "login_auditing",
            "current_value": "None",
            "recommended_value": "All",
            # Removed status - not a param
        },
        annotations_to_add={
            2: {
                "Justification": "Will enable after migration",
                "Review Status": "✓ Exception",
            }
        },
        expected_key_pattern="audit_settings|testserver|inst1|login_auditing",
    ),
]


def get_sheet_spec(sheet_name: str) -> Optional[SheetTestSpec]:
    """Get specification for a sheet by name."""
    for spec in SHEET_SPECS:
        if spec.sheet_name == sheet_name:
            return spec
    return None


def get_all_sheet_names() -> List[str]:
    """Get all sheet names that have test specs."""
    return [spec.sheet_name for spec in SHEET_SPECS]
