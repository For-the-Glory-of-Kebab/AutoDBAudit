# Sheet Consistency Matrix

This document is auto-generated from `sheet_registry.py` as the SINGLE SOURCE OF TRUTH.

## Sheet Summary

| Sheet | Entity Type | Key Columns | Has UUID | Has Action | Tracks Exceptions |
|-------|-------------|-------------|----------|------------|-------------------|
| Cover | cover | - | ❌ | ❌ | ❌ |
| Instances | instance | Config Name, Server, Instance | ❌ | ❌ | ❌ |
| Actions | action | ID | ❌ | ❌ | ❌ |
| SA Account | sa_account | Server, Instance | ✅ | ✅ | ✅ |
| Configuration | config | Server, Instance, Setting | ✅ | ✅ | ✅ |
| Server Logins | login | Server, Instance, Login Name | ✅ | ✅ | ✅ |
| Sensitive Roles | server_role | Server, Instance, Role, Member | ✅ | ✅ | ✅ |
| Services | service | Server, Instance, Service Name | ✅ | ✅ | ✅ |
| Databases | database | Server, Instance, Database | ✅ | ✅ | ✅ |
| Database Users | db_user | Server, Instance, Database, User Name | ✅ | ✅ | ✅ |
| Database Roles | db_role | Server, Instance, Database, Role, Member | ✅ | ✅ | ✅ |
| Orphaned Users | orphaned_user | Server, Instance, Database, User Name | ✅ | ✅ | ✅ |
| Permission Grants | permission | Server, Instance, Scope, Grantee, Permission | ✅ | ✅ | ✅ |
| Role Matrix | role_matrix | Server, Instance, Database, Principal Name | ✅ | ❌ | ❌ |
| Linked Servers | linked_server | Server, Instance, Linked Server | ✅ | ✅ | ✅ |
| Triggers | trigger | Server, Instance, Scope, Trigger Name | ✅ | ✅ | ✅ |
| Backups | backup | Server, Instance, Database | ✅ | ✅ | ✅ |
| Client Protocols | protocol | Server, Instance, Protocol | ✅ | ✅ | ✅ |
| Encryption | encryption | Server, Instance, Key Type, Key Name | ✅ | ❌ | ❌ |
| Audit Settings | audit_settings | Server, Instance, Setting | ✅ | ✅ | ✅ |

## Entity Key Format

All entity keys follow the pattern: `entity_type|key_col1|key_col2|...`

Examples:
- SA Account: `sa_account|SQLPROD01|(Default)`
- Backups: `backup|SQLPROD01|(Default)|MyDatabase`
- Database Roles: `db_role|SQLPROD01|(Default)|MyDB|db_owner|UserName`

## Editable Columns

Standard editable columns (most sheets):
- `Review Status` → `review_status`
- `Justification` → `justification`
- `Last Reviewed` → `last_reviewed`
- `Notes` → `notes`

Special annotation columns:
- Configuration: `Exception Reason`
- Linked Servers: `Purpose`
- Triggers: `Notes`

## Source of Truth

**File**: `src/autodbaudit/domain/sheet_registry.py`

This file is the SINGLE SOURCE OF TRUTH for:
- Sheet names
- Entity types
- Key columns
- Editable column mappings

All other modules MUST import from this registry.
