# AutoDBAudit - Comprehensive Project Overview

## Executive Summary

**AutoDBAudit** is a self-contained, offline-capable SQL Server audit and remediation tool designed for security compliance assessments in enterprise environments. The tool generates comprehensive, well-formatted Excel reports based on 22+ security and compliance requirements, analyzes discrepancies, generates remediation scripts, and tracks actions taken.

## Living Specification Notice

> [!IMPORTANT] > **This document is a living specification, not a rigid contract.**
>
> All schemas, structures, configurations, and architectural decisions described herein are **initial proposals** designed to evolve through collaborative development. As implementation progresses:
>
> - **Configuration schemas** (SqlTargets.json, audit_config.json) will mature based on real-world needs
> - **Settings and flags** may migrate between configs or be added/removed entirely
> - **Module boundaries** and project structure may shift as patterns emerge
> - **Both human insight and AI suggestions** should drive continuous improvement
> - **Flexibility trumps adherence** - if a better approach emerges, we pivot
>
> Throughout development, decisions should be guided by:
>
> - Practical implementation experience ("this would work better if...")
> - User feedback and evolving requirements
> - Discovery of better patterns or architectures
> - Balance between agility and maintainability
>
> **When in doubt**: Adapt and document reasoning rather than force-fit to this specification.

## Critical Context

### Target Environment Constraints

- **No Internet Access**: The tool must function completely offline on air-gapped Windows machines
- **Zero Dependencies Assumed**: Cannot rely on any pre-installed software except Windows OS
- **SQL Server Version Range**: Primary target is SQL Server 2019+, but **MUST support SQL Server 2008 R2** for legacy systems
- **Self-Contained Deployment**: Everything needed must be bundled in the deployment package

### Legacy Implementation

This project builds upon an existing PowerShell-based proof-of-concept located in the `1-Report-and-Setup/` directory. The legacy implementation serves as a **reference and validation baseline** but will **NOT** be used directly in the new system.

---

## Database Security Requirements (`db-requirements.md`)

The tool audits SQL Server instances against these 22+ security and compliance requirements:

### Documentation & Version Control (Req. 1-3)

1. **Server Documentation** (Every 6 months minimum):

   - Server name, instance name, IP address
   - Version details (edition, build, service pack)
   - Usernames in critical server roles (sysadmin, serveradmin, securityadmin)
   - Update history
   - Change log of important actions/events

2. **Version Compliance**:

   - Prohibit SQL Server versions older than 2019 (with documented exceptions)
   - **Special Case**: One legacy application uses SQL Server 2008 R2 - must be supported

3. **Patch Management**:
   - Verify latest cumulative updates installed
   - Check ProductVersion, ProductLevel, Edition, EngineEdition

### Authentication & Access Control (Req. 4-9)

4. **SA Account Hardening**:

   - Must be disabled AND renamed (typically to "$@")

5. **Password Policy**:

   - For members of sysadmin, serveradmin, securityadmin groups:
     - Complex passwords required
     - Non-empty passwords
     - Password ≠ Username
     - Windows accounts follow domain policy

6. **Service Account Requirements**:

   - SQL Server services must NOT use:
     - LocalService
     - NetworkService
     - LocalSystem
   - Must use domain/local accounts for observability and logging

7. **Unused Login Cleanup**:

   - Identify logins not in any server role (except public)
   - Identify logins with no mapped database users
   - Recommend disabling or removal

8. **Least Privilege Review**:

   - Periodic review of sysadmin, serveradmin, securityadmin members
   - Ensure adherence to Least Privilege and Need-to-Know principles

9. **Grant Permissions**:
   - "With Grant" option should be disabled for all users

### Feature Security (Req. 10-21)

10. **xp_cmdshell**: Must be disabled (includes novel dangerous features in newer versions)
11. **Encryption Backup**: If TDE/encryption enabled, verify regular backups of keys and certificates
12. **Trigger Review**: Periodic review of triggers (server-level, database-level)
13. **Orphaned Users**:
    - Identify users without logins
    - Verify guest user is disabled
14. **Default Instance Name**: No SQL instance should use default instance name
15. **Test Database Cleanup**:
    - Detect test/sample databases (AdventureWorks, Northwind, pubs, etc.)
    - Recommend deletion or detachment (with documentation)
16. **Ad Hoc Queries**: Must be strictly disabled
17. **Protocol Configuration**:
    - Disable unnecessary protocols (Shared Memory and TCP/IP usually sufficient)
    - Named Pipes, VIA, etc. should be disabled
18. **Database Mail XPs**: Should be disabled (unless well documented)
19. **SQL Server Browser**: Should be disabled in most cases (rare exceptions)
20. **Remote Access**: Remote SP execution should be disabled (almost no exceptions)
21. **Unnecessary Services**:
    - Analysis Services, Reporting Services, Integration Services
    - Should be disabled unless explicitly needed and documented
22. **Login Auditing**: Audit both successful and failed login attempts

### Application Security (Req. 23)

23. **Connection String Security**: Credentials should be encrypted (may not be checked in DB-only audit)

---

## Legacy Implementation Analysis

### Structure

Located in `1-Report-and-Setup/` directory:

```
1-Report-and-Setup/
├── main/
│   ├── collect-sql-inventory.ps1       # Main orchestrator (~483 lines)
│   ├── SqlInventory.Targets.psm1       # Target management module (~321 lines)
│   ├── SqlTargets.json                 # Configuration file
│   ├── jsonschema.json                 # Validation schema
│   └── queries/                        # 17 SQL query files
│       ├── InstanceInfo.sql
│       ├── ServerLogins.sql
│       ├── Databases.sql
│       ├── RoleMatrix.sql
│       ├── DbUserLoginMatrix.sql
│       ├── DbUserLoginRoleMatrix.sql
│       ├── DbUsers.sql
│       ├── DbRoles.sql
│       ├── DbTriggers.sql
│       ├── ServerTriggers.sql
│       ├── ServerPermissions.sql
│       ├── JobsAndSchedules.sql
│       ├── JobHistory.sql
│       ├── LinkedServers.sql
│       ├── ProtocolStatus.sql
│       ├── TcpListeners.sql
│       └── Services.sql
```

### Key Features of Legacy Implementation

#### 1. Target Configuration (`SqlTargets.json`)

```json
[
  {
    "Server": "localhost",
    "Instance": "InTheEnd",
    "Port": null,
    "Auth": "Sql",
    "SqlUser": "sa",
    "SecretPath": null,
    "Encrypt": false,
    "TrustServerCertificate": true,
    "ConnectTimeout": 15,
    "ApplicationName": "SqlInventory"
  }
]
```

**Features**:

- Multiple target SQL servers
- Flexible authentication (Integrated/SQL Auth)
- Credential management via SecretPath (encrypted PowerShell credentials)
- Port and instance name support
- Connection string customization

#### 2. Target Management Module (`SqlInventory.Targets.psm1`)

- JSON parsing and normalization
- Credential loading from encrypted files
- Interactive credential prompting
- Connection validation with retry logic
- Deduplication support

#### 3. Data Collection (`collect-sql-inventory.ps1`)

**Core Workflow**:

1. Load and validate targets from JSON
2. Connect to each SQL instance
3. Execute all `.sql` files in `queries/` folder
4. Tag results with Target name and CollectedAt timestamp
5. Aggregate into sheet collections

**Connection Strategy**:

- Attempts multiple connection protocols (lpc, np, tcp) for local connections
- Fallback mechanism for connectivity
- Supports both Windows and SQL authentication

#### 4. Excel Generation

**Features Implemented**:

- **Multi-sheet workbook** with ordered tabs
- **Summary sheet** with metadata (timestamp, host, instance count)
- **Server separators**: Visual dividers between different SQL instances
- **Cell merging**: Repeating values merged vertically for readability
- **Conditional formatting**:
  - Job status (green for Succeeded, red for Failed)
  - Role membership (sysadmin, serveradmin, etc.)
- **Styling**:
  - Header row: Bold, dark blue background, white text, frozen panes
  - Alternating row colors for readability
  - Separator rows: Gray background, italic text
  - Auto-fit columns
  - Auto-filter enabled
  - Date formatting for timestamp columns
  - Text wrapping for description/definition columns

**Sheet Order**:

1. Summary
2. InstanceInfo
3. Databases
4. ServerLogins
5. RoleMatrix
6. ServerPermissions
7. DbUserLoginMatrix
8. DbUserLoginRoleMatrix
9. DbUsers
10. DbRoles
11. DbTriggers
12. ServerTriggers
13. JobsAndSchedules
14. JobHistory
15. LinkedServers
16. ProtocolStatus
17. TcpListeners
18. Services

### Limitations of Legacy Implementation

1. **One-Time Use**: Generates reports but no remediation
2. **No Discrepancy Analysis**: Manual review required
3. **No Script Generation**: No automated fix scripts
4. **No Action Tracking**: No audit trail of changes
5. **Limited Reusability**: Tailored for specific use case
6. **PowerShell Scaling Issues**: Difficult to structure as a maintainable project
7. **No SQL Version Handling**: Modern syntax may fail on SQL Server 2008 R2
8. **No Hotfix Management**: Manual patching required

### SQL Compatibility Issues

Several queries use **SQL Server 2016+ syntax** that will FAIL on SQL Server 2008 R2:

**Example from `InstanceInfo.sql`**:

```sql
-- STRING_AGG introduced in SQL Server 2017
SELECT STRING_AGG(CAST(port AS varchar(10)), ',') ...
```

**Example from `DbUserLoginRoleMatrix.sql`**:

```sql
-- sys.database_principals columns may differ in 2008 R2
-- TRY_CAST introduced in SQL Server 2012
```

**Critical**: New implementation MUST detect SQL version and use compatible query variants.

---

## Project Goals & Priorities

### Mission Statement

Transform the one-off PowerShell proof-of-concept into a **reusable, production-grade audit and remediation tool** that can be deployed to any organization's offline SQL Server environment with zero setup beyond configuration file editing.

### Primary Goals (In Priority Order)

#### 1. **Agility** (Priority #1) 🚀

- Rapid development and iteration
- Quick adaptation to changing requirements
- Fast deployment to target organizations
- Prefer "good enough now" over "perfect later"

#### 2. **Self-Containment** (Critical Requirement) 🔒

- **Single deployment package** that works on any Windows machine
- No internet access required during execution
- All dependencies bundled or pre-validated
- Include setup for any required system components (ODBC drivers, etc.)

#### 3. **Readability & Maintainability** 📖

- Clean, well-documented code
- Easy for future developers to understand
- Configuration via simple JSON files
- Modular design for component updates

#### 4. **Adaptability** 🔧

- Easy to add/remove audit requirements
- Simple SQL query modifications
- Flexible output formatting

### Explicit Non-Goals

- ❌ Enterprise-scale architecture
- ❌ Microservices or distributed systems
- ❌ Performance optimization beyond "fast enough"
- ❌ UI/UX polish (command-line tool is acceptable)
- ❌ Sophisticated error recovery (fail-fast is acceptable)

---

## New Capabilities Required

### 1. Multi-Organization Configurability

> **Note**: Configuration schema will evolve. The below represents an initial proposal.

**Initially Proposed: Two Configuration Files**

#### `sql_targets.json` (per organization)

- List of SQL servers to audit
- Credentials (encrypted or prompted)
- Connection parameters
- **May evolve to include**: Per-server overrides, database-level settings, environment tags, etc.

#### `audit_config.json` (per organization/audit) - **Initial Schema**

```json
{
  "OrganizationName": "Acme Corp",
  "AuditYear": 2025,
  "AuditDate": "2025-12-02",
  "Verbosity": "detailed",
  "OutputFormat": "excel",
  "IncludeRemediation": true,
  "Settings": {
    "AllowTestDatabases": false,
    "RequireComplexPasswords": true,
    "MinimumSqlVersion": "2019"
    // NOTE: Settings will expand as requirements emerge
    // May move some to sql_targets.json for per-server granularity
  }
}
```

> **Evolution Points**:
>
> - Some settings might need to be **per-server** (move to SqlTargets.json)
> - May need **per-database** overrides for specific exceptions
> - Additional flags will emerge during implementation
> - Schema versioning may be needed for backward compatibility

### 2. Discrepancy Analysis

- Compare audit results against requirements
- Flag violations (e.g., "sa account not disabled")
- Categorize by severity (critical, warning, info)
- Support for **documented exceptions** (e.g., specific test DBs allowed)

### 3. Remediation Script Generation

- Generate T-SQL scripts to fix identified issues
- **Sectioned and commented** so exceptions can be commented out
- Example:

```sql
-- ============================================
-- Requirement 4: Disable and Rename SA Account
-- ============================================
-- Current State: sa account is ENABLED and not renamed
-- Action: Disable and rename to $@

-- UNCOMMENT BELOW TO APPLY:
-- ALTER LOGIN [sa] DISABLE;
-- ALTER LOGIN [sa] WITH NAME = [$@];
```

### 4. Action Tracking & Reporting

- Log which remediation scripts were executed
- Record exceptions (items that were NOT fixed by choice)
- Generate "Important Actions Taken" report
- Integrate action report into audit documentation

### 5. Report Update Capability

- **Mode 1**: Generate new audit report
- **Mode 2**: Update existing report after remediation
  - Mark fixed items as "RESOLVED"
  - Mark skipped items as "EXCEPTION - Not Fixed"
  - Preserve original findings
  - Add new "Status" and "Action Taken" columns

### 6. Enhanced Excel Formatting

Beyond legacy implementation:

- **Icons**: ✅ ❌ ⚠️ in status columns
- **Color-coded severity**: Red (critical), yellow (warning), green (compliant)
- **Collapsible sections** or grouped rows
- **Rich text** in cells where applicable
- **Chart summaries** (compliance percentage, violations by category)
- **Sheet naming** with organization name

### 7. SQL Version Compatibility

- **Detect SQL Server version** on connection
- Use **version-specific query variants**:
  - SQL 2008 R2 queries (no STRING_AGG, TRY_CAST, etc.)
  - SQL 2012-2016 queries (intermediate features)
  - SQL 2017+ queries (modern syntax)
- Graceful degradation: if feature not available, note in report

---

## Hotfix Deployment Module (Separate/Optional)

### Purpose

Automate patching of multiple SQL Server instances from a central location.

### Requirements

- **Input**: List of SQL servers, path to .msi/.exe hotfix files
- **Execution**: Remote installation via PSRemoting or WMI
- **Logging**:
  - Real-time progress updates
  - Success/failure per server
  - Detailed error messages
- **Safety**:
  - Pre-flight checks (disk space, service status)
  - Rollback capability if possible
  - Backup recommendations

### Integration

- Can be **standalone module** or invoked from main tool
- Separate command: `AutoDBAudit.exe --deploy-hotfixes`
- Generates its own report of deployment results

---

## Repository Structure (Initial Proposal)

> **Note**: Structure will evolve as project matures. Don't be constrained by this layout.

```
AutoDBAudit/                          # Root directory (current: d:\Raja-Initiative)
├── 1-Report-and-Setup/                # LEGACY - PowerShell impl (reference only, DO NOT MODIFY)
│   ├── main/
│   │   ├── collect-sql-inventory.ps1
│   │   ├── SqlInventory.Targets.psm1
│   │   ├── SqlTargets.json
│   │   └── queries/
│   └── ... (other legacy files)
├── db-requirements.md                 # Requirements specification (22 rules)
├── config/                            # Configuration templates (NEW)
│   ├── sql_targets.example.json      # Schema may evolve
│   └── audit_config.example.json     # Schema may evolve
├── queries/                           # SQL query files (NEW - organization may change)
│   ├── 2008/                          # SQL Server 2008 R2 compatible
│   ├── 2012/                          # SQL Server 2012-2016
│   └── 2017/                          # SQL Server 2017+
│       # May reorganize by: requirement, category, or unified with version flags
├── src/                               # Python source code (NEW - modules may shift)
│   ├── core/
│   ├── remediation/
│   └── hotfix/
├── output/                            # Generated reports and scripts (NEW)
├── docs/                              # Additional documentation (NEW)
└── build/                             # Build scripts for standalone .exe (NEW)
```

**Evolution Guidelines**:

- Refactor module boundaries as patterns emerge
- Add new directories as needs arise (e.g., `tests/`, `templates/`, `schemas/`)
- Query organization may shift based on maintenance burden

---

## Technical Constraints & Considerations

### SQL Server 2008 R2 Compatibility

**Avoid These SQL Features**:

- `STRING_AGG()` (2017+)
- `TRY_CAST()`, `TRY_CONVERT()` (2012+)
- `CONCAT_WS()` (2017+)
- `FORMATMESSAGE()` enhancements (varies)
- Certain DMVs/system views added in later versions

**Use Instead**:

- XML PATH for string concatenation
- Traditional `CAST()` with `CASE` for error handling
- Manual string building
- Check `SERVERPROPERTY('ProductMajorVersion')` before using DMVs

### Offline Deployment Challenges

1. **ODBC Driver**:

   - Most Windows installations have some SQL Server driver
   - Bundle Microsoft ODBC Driver 17 for SQL Server installer as fallback
   - Include detection script

2. **Python Runtime**:

   - PyInstaller bundles Python interpreter
   - No Python installation required on target

3. **Excel Dependencies**:

   - Use `openpyxl` (pure Python, no Excel installation needed)
   - Generates `.xlsx` files that can be opened later

4. **Credentials**:
   - Encrypted credential files (Windows DPAPI)
   - Interactive prompts during first run
   - No plaintext passwords in config files

---

## Success Criteria

### Minimum Viable Product (MVP)

- ✅ Self-contained executable
- ✅ Multi-server audit from JSON config
- ✅ Excel report with all 22 requirement checks
- ✅ SQL 2008 R2 through 2019+ compatibility
- ✅ Discrepancy identification
- ✅ Basic remediation script generation

### Phase 2 Enhancements

- ✅ Action tracking and reporting
- ✅ Report update mode
- ✅ Advanced Excel formatting (icons, charts)
- ✅ Exception management
- ✅ Hotfix deployment module

### Ultimate Success

- Can be deployed to **any organization** with SQL Server environment
- Requires only **editing two JSON files** to configure
- Generates **audit-ready, well-formatted reports** in under 5 minutes
- Saves hours of manual work per audit cycle

---

## Design Principles

1. **Convention over Configuration**: Sensible defaults, minimal setup
2. **Fail Early, Fail Clearly**: Don't hide errors, report them prominently
3. **Pragmatic Simplicity**: Simple solutions over clever ones
4. **Offline-First**: Never assume network connectivity
5. **Version Awareness**: Detect capabilities, don't assume
6. **Human-Readable Output**: Reports should be immediately understandable
7. **Adapt When Better Alternatives Emerge**: Don't be bound by initial design if a superior approach is discovered
8. **Document Evolution**: When pivoting from this spec, document why (even briefly)

### Collaborative Development Approach

> [!TIP] > **Decision-Making During Implementation**
>
> As development progresses, either party (human or AI) may propose improvements:
>
> **Human might say**:
>
> - "Let's add a `--dry-run` flag here"
> - "These two settings should be per-server, not global"
> - "Can we split this sheet into two for better readability?"
> - "The remediation scripts should include rollback steps"
>
> **AI might suggest**:
>
> - "This configuration would be cleaner as YAML instead of JSON"
> - "We could consolidate these three modules into one for simplicity"
> - "Pattern X would make this more maintainable long-term"
> - "This approach has a security/compatibility issue, here's an alternative"
>
> **When these happen**: Discuss briefly, make a pragmatic choice prioritizing agility, and move forward. The specification adapts to fit reality, not the other way around.

---

## End Notes

This document serves as the **definitive reference** for the AutoDBAudit project. The legacy PowerShell implementation in `1-Report-and-Setup/` provides proof that the core concept works and serves as a validation baseline. The new Python-based implementation will exceed the legacy version in every dimension while maintaining the same core audit philosophy.

**Next Step**: Create detailed implementation plan with technology choices, architecture design, and development roadmap.
