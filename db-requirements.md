# SQL Server Audit Requirements

> **Note**: This is the source-of-truth for security compliance requirements.
> Requirements 1-23 are original. Requirements 24-28 were added 2025-12 for linked servers and security matrix.

---

## Server Documentation & Configuration

1. **Documentation frequency**: DB documentation should be gathered frequently (at least every 6 months):
    - Server name
    - Instance name 
    - IP address
    - Version (edition, build, SP, etc.)
    - Usernames/Logins in sysadmin, serveradmin, securityadmin groups
    - History of updates
    - History of revisions and important changes

2. **SQL Server version**: Using SQL Servers other than 2019+ is prohibited (with documented exceptions)

3. **Latest update**: Check if latest update has been installed using:
    - `ProductVersion`, `ProductLevel`, `Edition`, `EngineEdition` properties

4. **SA account**: The default 'sa' user should be BOTH disabled AND renamed (usually to "$@")

5. **Password requirements** for sysadmin/serveradmin/securityadmin members:
    - Follow complexity standards
    - Be non-empty
    - Not be the same as the username
    - Windows accounts should follow domain policy

6. **Service accounts**: Avoid virtual accounts for SQL services. All active SQL services should use domain/local accounts, NOT:
    - LocalService
    - NetworkService
    - LocalSystem

---

## Login & User Management

7. **Unused logins**: Should be disabled or removed (check every 6 months):
    - Logins not member of any role AND have no mapped database users
    - (Public role doesn't count as active membership)

8. **Least privilege**: Members of sysadmin/serveradmin/securityadmin should follow:
    - Least Privilege Principle
    - Need-to-Know Principle

9. **Grant option**: User accesses should NOT have "WITH GRANT" enabled

---

## Features & Configuration

10. **Disable unused features**: Disable unnecessary features like `xp_cmdshell`
    - (This list should be updated for new SQL Server features)

11. **Encryption backups**: If database encryption is enabled, maintain regular backups of encryption keys, logs, and status

12. **Triggers review**: Triggers at all levels (server, database) should be reviewed periodically

13. **Database users review**:
    - Orphaned users (users without logins) should be removed
    - Guest user should be disabled

14. **Instance naming**: No SQL instance should use the default instance name

15. **Test databases**: Test instances, databases, and unnecessary ones should be deleted/detached:
    - Check for common names: AdventureWorks, test, pubs, Northwind, etc.

16. **Ad Hoc queries**: Ad Hoc Distributed Queries feature should be disabled

17. **Protocols**: Disable unnecessary protocols. Usually only allow:
    - TCP/IP
    - Shared Memory

18. **Database Mail**: Database Mail XPs should be disabled (document exceptions)

19. **SQL Browser**: SQL Server Browser should be disabled (rare exceptions)

20. **Remote access**: Remote execution of stored procedures should be disabled

21. **Unnecessary features**: Disable unused SQL Server features:
    - Analysis Services
    - Reporting Services
    - Integration Services
    - (unless explicitly needed and documented)

22. **Login auditing**: Auditing of successful AND unsuccessful logins should be enabled

---

## Software-Specific (Application-Level)

23. **Connection strings**: Credentials/connection strings should be encrypted in applications

---

## Linked Servers

24. **Linked Server inventory**: Should be inventoried and reviewed periodically:
    - List all linked servers with remote server/product info
    - Document the purpose of each linked server
    - Track changes (additions/removals) over time
    - Security review: which accounts are mapped and with what permissions

25. **Linked Server security**: Mappings should follow least privilege:
    - Avoid using 'sa' or sysadmin for linked server connections
    - Remote logins should use appropriate credentials (no impersonation without approval)
    - Track which local logins map to which remote credentials

---

## Security Matrix Audit (Logins, Roles, Users, Groups, Mappings)

> **Note**: SQL Server has a complex security model with multiple overlapping concepts.
> The audit should capture a complete picture across multiple Excel sheets.

```
SQL Server Security Hierarchy:
┌─────────────────────────────────────────────────────────────────┐
│ SERVER LEVEL                                                    │
├─────────────────────────────────────────────────────────────────┤
│  Logins (Windows User, Windows Group, SQL Login, Certificate)  │
│     ↓ are members of                                            │
│  Server Roles (sysadmin, serveradmin, securityadmin, etc.)      │
│     ↓ have                                                      │
│  Server-level Permissions                                       │
└─────────────────────────────────────────────────────────────────┘
        ↓ mapped to
┌─────────────────────────────────────────────────────────────────┐
│ DATABASE LEVEL (per database)                                   │
├─────────────────────────────────────────────────────────────────┤
│  Users (mapped from Logins, or contained DB users)              │
│     ↓ are members of                                            │
│  Database Roles (db_owner, db_datareader, custom roles, etc.)   │
│     ↓ have                                                      │
│  Object-level Permissions (tables, views, procs, schemas)       │
└─────────────────────────────────────────────────────────────────┘
```

26. **Server-level security audit** should produce:
    - **Logins Sheet**: All logins with type (Windows User/Group, SQL, Certificate), status (enabled/disabled), default database, password policy flags, create/modify dates
    - **Server Roles Sheet**: All server roles (fixed + custom) with their members
    - **Login-to-Role Mapping**: Which logins belong to which server roles
    - Separate sections/filters by login type

27. **Database-level security audit** should produce (per database or consolidated):
    - **Database Users Sheet**: All users per database with mapped login, type, default schema, create date
    - **Database Roles Sheet**: All roles (fixed + custom) per database with members
    - **Orphaned Users**: Users without matching logins
    - **Permission Grants Sheet**: Explicit permissions (GRANT/DENY) on schemas, tables, views, procedures
    - **Role Membership Matrix**: Visual matrix of users × roles

28. **Security change tracking**:
    - Track additions/removals of logins, users, role memberships over time
    - Highlight new high-privilege grants (sysadmin, db_owner, etc.)
    - Compare current state vs previous audit for drift detection
