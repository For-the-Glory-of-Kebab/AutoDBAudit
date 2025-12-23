"""
All Sheet Specifications.

This file defines specs for ALL 20 sheets in the Excel report.
Each spec matches the EXCEL_COLUMNS.md documentation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterator

from .base import SheetSpec


# =============================================================================
# 1. Cover Sheet (Summary - no data rows)
# =============================================================================
COVER_SPEC = SheetSpec(
    sheet_name="Cover",
    entity_type="summary",
    writer_method=None,  # Cover is auto-generated
    sample_kwargs={},
    editable_cols={},  # Cover stats are read-only
    expected_key_pattern="",
    supports_exceptions=False,
    has_notes=False,
    has_justification=False,
    has_status=False,
    is_summary_sheet=True,
)

# =============================================================================
# 2. Instances Sheet
# =============================================================================
INSTANCES_SPEC = SheetSpec(
    sheet_name="Instances",
    entity_type="instance",
    writer_method="add_instance",
    sample_kwargs={
        "server_name": "TestServer",
        "instance_name": "INST1",
        "config_name": "TestConfig",
        "machine_name": "TEST-SQL-01",
        "ip_address": "192.168.1.100",
        "version": "15.0.4123.1",
        "product_level": "RTM",
        "edition": "Developer Edition",
        "is_clustered": False,
        "is_hadr": False,
        "os_info": "Windows Server 2019",
        "cpu_count": 4,
        "memory_gb": 16,
        "tcp_port": 1433,
        "version_major": 15,
    },
    editable_cols={
        "Notes": "notes",
        "Last Reviewed": "last_reviewed",
    },
    expected_key_pattern="instance|testserver|inst1",
    supports_exceptions=False,  # Instances are informational
    has_notes=True,
    has_justification=False,
)

# =============================================================================
# 3. SA Account Sheet
# =============================================================================
SA_ACCOUNT_SPEC = SheetSpec(
    sheet_name="SA Account",
    entity_type="sa_account",
    writer_method="add_sa_account",
    sample_kwargs={
        "server_name": "TestServer",
        "instance_name": "INST1",
        "is_disabled": True,
        "is_renamed": True,
        "current_name": "sa",
        "default_db": "master",
    },
    editable_cols={
        "Review Status": "review_status",
        "Justification": "justification",
        "Last Reviewed": "last_reviewed",
        "Notes": "notes",
    },
    expected_key_pattern="sa_account|testserver|inst1|sa",
    supports_exceptions=True,
    has_notes=True,
    has_justification=True,
)

# =============================================================================
# 4. Configuration Sheet
# =============================================================================
CONFIGURATION_SPEC = SheetSpec(
    sheet_name="Configuration",
    entity_type="config",
    writer_method="add_config_setting",
    sample_kwargs={
        "server_name": "TestServer",
        "instance_name": "INST1",
        "setting_name": "xp_cmdshell",
        "current_value": 0,
        "required_value": 0,
        "risk_level": "Critical",
    },
    editable_cols={
        "Review Status": "review_status",
        "Exception Reason": "justification",  # Note: uses "Exception Reason" not "Justification"
        "Last Reviewed": "last_reviewed",
    },
    expected_key_pattern="config|testserver|inst1|xp_cmdshell",
    supports_exceptions=True,
    has_notes=False,
    has_justification=True,
)

# =============================================================================
# 5. Server Logins Sheet
# =============================================================================
SERVER_LOGINS_SPEC = SheetSpec(
    sheet_name="Server Logins",
    entity_type="login",
    writer_method="add_login",
    sample_kwargs={
        "server_name": "TestServer",
        "instance_name": "INST1",
        "login_name": "weak_login",
        "login_type": "SQL Login",
        "is_disabled": False,
        "pwd_policy": True,
        "default_db": "master",
    },
    editable_cols={
        "Review Status": "review_status",
        "Justification": "justification",
        "Last Reviewed": "last_reviewed",
        "Notes": "notes",
    },
    expected_key_pattern="login|testserver|inst1|weak_login",
    supports_exceptions=True,
    has_notes=False,
    has_justification=True,
)

# =============================================================================
# 6. Sensitive Roles Sheet
# =============================================================================
SENSITIVE_ROLES_SPEC = SheetSpec(
    sheet_name="Sensitive Roles",
    entity_type="server_role_member",
    writer_method="add_role_member",
    sample_kwargs={
        "server_name": "TestServer",
        "instance_name": "INST1",
        "role_name": "sysadmin",
        "member_name": "risky_admin",
        "member_type": "SQL Login",
        "is_disabled": True,
    },
    editable_cols={
        "Review Status": "review_status",
        "Justification": "justification",
        "Last Reviewed": "last_reviewed",
    },
    expected_key_pattern="server_role_member|testserver|inst1|sysadmin|risky_admin",
    supports_exceptions=True,
    has_notes=False,
    has_justification=True,
)

# =============================================================================
# 7. Services Sheet
# =============================================================================
SERVICES_SPEC = SheetSpec(
    sheet_name="Services",
    entity_type="service",
    writer_method="add_service",
    sample_kwargs={
        "server_name": "TestServer",
        "instance_name": "INST1",
        "service_name": "SQLBrowser",
        "service_type": "SQL Server Browser",
        "status": "Running",
        "startup_type": "Automatic",
        "service_account": "NT SERVICE\\SQLBrowser",
    },
    editable_cols={
        "Review Status": "review_status",
        "Justification": "justification",
        "Last Reviewed": "last_reviewed",
    },
    expected_key_pattern="service|testserver|inst1|sqlbrowser",
    supports_exceptions=True,
    has_notes=False,
    has_justification=True,
)

# =============================================================================
# 8. Databases Sheet
# =============================================================================
DATABASES_SPEC = SheetSpec(
    sheet_name="Databases",
    entity_type="database",
    writer_method="add_database",
    sample_kwargs={
        "server_name": "TestServer",
        "instance_name": "INST1",
        "database_name": "RiskyDB",
        "owner": "sa",
        "recovery_model": "SIMPLE",
        "state": "ONLINE",
        "data_size_mb": 100.0,
        "log_size_mb": 10.0,
        "is_trustworthy": False,
    },
    editable_cols={
        "Review Status": "review_status",
        "Justification": "justification",
        "Last Reviewed": "last_reviewed",
        "Notes": "notes",
    },
    expected_key_pattern="database|testserver|inst1|riskydb",
    supports_exceptions=True,
    has_notes=True,
    has_justification=True,
)

# =============================================================================
# 9. Database Users Sheet
# =============================================================================
DATABASE_USERS_SPEC = SheetSpec(
    sheet_name="Database Users",
    entity_type="db_user",
    writer_method="add_db_user",
    sample_kwargs={
        "server_name": "TestServer",
        "instance_name": "INST1",
        "database_name": "AppDB",
        "user_name": "valid_user",
        "user_type": "SQL User",
        "mapped_login": None,
        "is_orphaned": False,
    },
    editable_cols={
        "Review Status": "review_status",
        "Justification": "justification",
        "Last Reviewed": "last_reviewed",
        "Notes": "notes",
    },
    expected_key_pattern="db_user|testserver|inst1|appdb|valid_user",
    supports_exceptions=True,
    has_notes=True,
    has_justification=True,
)

# =============================================================================
# 10. Database Roles Sheet
# =============================================================================
DATABASE_ROLES_SPEC = SheetSpec(
    sheet_name="Database Roles",
    entity_type="db_role",
    writer_method="add_db_role_member",
    sample_kwargs={
        "server_name": "TestServer",
        "instance_name": "INST1",
        "database_name": "AppDB",
        "role_name": "db_owner",
        "member_name": "risky_user",
        "member_type": "SQL User",
    },
    editable_cols={
        "Review Status": "review_status",
        "Justification": "justification",
        "Last Reviewed": "last_reviewed",
    },
    expected_key_pattern="db_role|testserver|inst1|appdb|db_owner|risky_user",
    supports_exceptions=True,
    has_notes=False,
    has_justification=True,
)

# =============================================================================
# 11. Orphaned Users Sheet
# =============================================================================
ORPHANED_USERS_SPEC = SheetSpec(
    sheet_name="Orphaned Users",
    entity_type="orphaned_user",
    writer_method="add_orphaned_user",
    sample_kwargs={
        "server_name": "TestServer",
        "instance_name": "INST1",
        "database_name": "LegacyDB",
        "user_name": "old_user",
        "user_type": "SQL User",
    },
    editable_cols={
        "Review Status": "review_status",
        "Justification": "justification",
        "Last Reviewed": "last_reviewed",  # Note: "Last Revised" not "Last Reviewed"
    },
    expected_key_pattern="orphaned_user|testserver|inst1|legacydb|old_user",
    supports_exceptions=True,
    has_notes=False,
    has_justification=True,
)

# =============================================================================
# 12. Permission Grants Sheet
# =============================================================================
PERMISSION_GRANTS_SPEC = SheetSpec(
    sheet_name="Permission Grants",
    entity_type="permission",
    writer_method="add_permission",
    sample_kwargs={
        "server_name": "TestServer",
        "instance_name": "INST1",
        "scope": "SERVER",
        "database_name": "",
        "grantee_name": "dev_team",
        "permission_name": "CONNECT",
        "state": "GRANT",
        "entity_name": "",
    },
    editable_cols={
        "Review Status": "review_status",
        "Justification": "justification",
        "Last Reviewed": "last_reviewed",
        "Notes": "notes",
    },
    expected_key_pattern="permission|testserver|inst1|server||dev_team|connect|",
    supports_exceptions=True,
    has_notes=True,
    has_justification=True,
)

# =============================================================================
# 13. Role Matrix Sheet (Informational)
# =============================================================================
ROLE_MATRIX_SPEC = SheetSpec(
    sheet_name="Role Matrix",
    entity_type="role_matrix",
    writer_method=None,  # Role Matrix is auto-generated from roles data
    sample_kwargs={},
    editable_cols={},  # Read-only matrix
    expected_key_pattern="",
    supports_exceptions=False,
    has_notes=False,
    has_justification=False,
    is_summary_sheet=True,  # It's a summary view
)

# =============================================================================
# 14. Linked Servers Sheet
# =============================================================================
LINKED_SERVERS_SPEC = SheetSpec(
    sheet_name="Linked Servers",
    entity_type="linked_server",
    writer_method="add_linked_server",
    sample_kwargs={
        "server_name": "TestServer",
        "instance_name": "INST1",
        "linked_server_name": "REMOTE_PROD",
        "product": "SQL Server",
        "provider": "SQLNCLI11",
        "data_source": "prod.internal",
        "rpc_out": False,
    },
    editable_cols={
        "Review Status": "review_status",
        "Purpose": "purpose",
        "Justification": "justification",
        "Last Reviewed": "last_reviewed",
    },
    expected_key_pattern="linked_server|testserver|inst1|remote_prod",
    supports_exceptions=True,
    has_notes=False,  # Has Purpose instead
    has_justification=True,
)

# =============================================================================
# 15. Triggers Sheet
# =============================================================================
TRIGGERS_SPEC = SheetSpec(
    sheet_name="Triggers",
    entity_type="trigger",
    writer_method="add_trigger",
    sample_kwargs={
        "server_name": "TestServer",
        "instance_name": "INST1",
        "level": "SERVER",
        "database_name": "",
        "trigger_name": "trg_logon_audit",
        "event_type": "LOGON",
        "is_enabled": True,
    },
    editable_cols={
        "Review Status": "review_status",
        "Notes": "notes",
        "Justification": "justification",
        "Last Reviewed": "last_reviewed",
    },
    expected_key_pattern="trigger|testserver|inst1|server||trg_logon_audit",
    supports_exceptions=True,
    has_notes=True,
    has_justification=True,
)

# =============================================================================
# 16. Backups Sheet
# =============================================================================
BACKUPS_SPEC = SheetSpec(
    sheet_name="Backups",
    entity_type="backup",
    writer_method="add_backup_info",
    sample_kwargs={
        "server_name": "TestServer",
        "instance_name": "INST1",
        "database_name": "CriticalDB",
        "recovery_model": "FULL",
        "last_backup_date": None,  # FAIL - no backup
        "days_since": None,
        "backup_path": "",
        "backup_size_mb": None,
    },
    editable_cols={
        "Review Status": "review_status",
        "Justification": "justification",
        "Last Reviewed": "last_reviewed",
        "Notes": "notes",
    },
    expected_key_pattern="backup|testserver|inst1|criticaldb|full",
    supports_exceptions=True,
    has_notes=True,
    has_justification=True,
)

# =============================================================================
# 17. Client Protocols Sheet
# =============================================================================
CLIENT_PROTOCOLS_SPEC = SheetSpec(
    sheet_name="Client Protocols",
    entity_type="protocol",
    writer_method="add_client_protocol",
    sample_kwargs={
        "server_name": "TestServer",
        "instance_name": "INST1",
        "protocol_name": "Named Pipes",
        "is_enabled": True,  # FAIL - should be disabled
        "port": None,
        "notes": "",
    },
    editable_cols={
        "Review Status": "review_status",
        "Justification": "justification",
        "Last Reviewed": "last_reviewed",
    },
    expected_key_pattern="protocol|testserver|inst1|named pipes",
    supports_exceptions=True,
    has_notes=False,  # Notes in sample_kwargs but not editable
    has_justification=True,
)

# =============================================================================
# 18. Encryption Sheet
# =============================================================================
ENCRYPTION_SPEC = SheetSpec(
    sheet_name="Encryption",
    entity_type="encryption",
    writer_method="add_encryption_row",
    sample_kwargs={
        "server_name": "TestServer",
        "instance_name": "INST1",
        "database_name": "master",
        "key_type": "SMK",
        "key_name": "##MS_ServiceMasterKey##",
        "algorithm": "AES_256",
        "created_date": datetime.now(),
        "backup_status": "Not Backed Up",
        "status": "WARN",
    },
    editable_cols={
        "Notes": "notes",
    },
    expected_key_pattern="encryption|testserver|inst1|smk|##ms_servicemasterkey##",
    supports_exceptions=False,  # Encryption only has Notes
    has_notes=True,
    has_justification=False,
)

# =============================================================================
# 19. Audit Settings Sheet
# =============================================================================
AUDIT_SETTINGS_SPEC = SheetSpec(
    sheet_name="Audit Settings",
    entity_type="audit_settings",
    writer_method="add_audit_setting",
    sample_kwargs={
        "server_name": "TestServer",
        "instance_name": "INST1",
        "setting_name": "Login Auditing",
        "current_value": "None",  # FAIL
        "recommended_value": "All",
    },
    editable_cols={
        "Review Status": "review_status",
        "Justification": "justification",  # Matches audit_settings.py
        "Last Reviewed": "last_reviewed",
    },
    expected_key_pattern="audit_settings|testserver|inst1|login auditing",
    supports_exceptions=True,
    has_notes=False,
    has_justification=True,
)

# =============================================================================
# 20. Actions Sheet (Log)
# =============================================================================
ACTIONS_SPEC = SheetSpec(
    sheet_name="Actions",
    entity_type="action",
    writer_method=None,  # Actions are populated by sync process
    sample_kwargs={},
    editable_cols={
        "Notes": "notes",
    },
    expected_key_pattern="",
    supports_exceptions=False,
    has_notes=True,
    has_justification=False,
    is_log_sheet=True,
)


# =============================================================================
# ALL SPECS COLLECTION
# =============================================================================
ALL_SHEET_SPECS: tuple[SheetSpec, ...] = (
    COVER_SPEC,  # 1
    INSTANCES_SPEC,  # 2
    SA_ACCOUNT_SPEC,  # 3
    CONFIGURATION_SPEC,  # 4
    SERVER_LOGINS_SPEC,  # 5
    SENSITIVE_ROLES_SPEC,  # 6
    SERVICES_SPEC,  # 7
    DATABASES_SPEC,  # 8
    DATABASE_USERS_SPEC,  # 9
    DATABASE_ROLES_SPEC,  # 10
    ORPHANED_USERS_SPEC,  # 11
    PERMISSION_GRANTS_SPEC,  # 12
    ROLE_MATRIX_SPEC,  # 13
    LINKED_SERVERS_SPEC,  # 14
    TRIGGERS_SPEC,  # 15
    BACKUPS_SPEC,  # 16
    CLIENT_PROTOCOLS_SPEC,  # 17
    ENCRYPTION_SPEC,  # 18
    AUDIT_SETTINGS_SPEC,  # 19
    ACTIONS_SPEC,  # 20
)


def get_spec_by_name(sheet_name: str) -> SheetSpec | None:
    """Get a sheet spec by its name."""
    for spec in ALL_SHEET_SPECS:
        if spec.sheet_name.lower() == sheet_name.lower():
            return spec
    return None


def get_specs_with_exceptions() -> Iterator[SheetSpec]:
    """Yield only specs that support exception tracking."""
    for spec in ALL_SHEET_SPECS:
        if spec.supports_exceptions:
            yield spec


def get_specs_with_notes() -> Iterator[SheetSpec]:
    """Yield only specs that have notes column."""
    for spec in ALL_SHEET_SPECS:
        if spec.has_notes:
            yield spec


def get_data_specs() -> Iterator[SheetSpec]:
    """Yield specs that have actual data rows (not summary/log)."""
    for spec in ALL_SHEET_SPECS:
        if spec.writer_method and not spec.is_summary_sheet and not spec.is_log_sheet:
            yield spec
