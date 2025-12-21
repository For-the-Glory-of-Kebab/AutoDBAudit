"""
Excel Report Package.

Provides comprehensive Excel audit report generation with modular,
maintainable architecture. Each sheet is implemented in its own module.

Usage:
    from autodbaudit.infrastructure.excel import EnhancedReportWriter
    
    writer = EnhancedReportWriter()
    writer.set_audit_info(run_id=1, organization="Acme Corp")
    writer.add_instance(...)
    writer.add_login(...)
    writer.save("report.xlsx")

Modules:
    base.py         - Shared utilities, column definitions, base classes
    row_uuid.py     - Row UUID utilities for stable synchronization (v3)
    writer.py       - Main EnhancedReportWriter class
    cover.py        - Cover sheet with summary
    instances.py    - SQL Server instances
    sa_account.py   - SA account security
    logins.py       - Server logins
    roles.py        - Server role membership
    config.py       - sp_configure security settings
    services.py     - SQL services
    databases.py    - Database properties
    db_users.py     - Database users (security matrix)
    db_roles.py     - Database role membership
    orphaned_users.py - Orphaned database users
    linked_servers.py - Linked server configuration
    triggers.py     - Server and database triggers
    backups.py      - Backup history and status
    audit_settings.py - Audit configuration
    actions.py      - Remediation action items
"""

from autodbaudit.infrastructure.excel.writer import EnhancedReportWriter
from autodbaudit.infrastructure.excel.base import SheetConfig, ColumnDef
from autodbaudit.infrastructure.excel.row_uuid import (
    UUID_COLUMN,
    generate_row_uuid,
    is_valid_uuid,
    read_row_uuid,
    write_row_uuid,
)

__all__ = [
    "EnhancedReportWriter",
    "SheetConfig",
    "ColumnDef",
    # Row UUID utilities
    "UUID_COLUMN",
    "generate_row_uuid",
    "is_valid_uuid",
    "read_row_uuid",
    "write_row_uuid",
]

