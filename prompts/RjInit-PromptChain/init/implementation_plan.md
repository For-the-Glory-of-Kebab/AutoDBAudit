# AutoDBAudit - Implementation Action Plan

> [!IMPORTANT]
> **Living Document**: This plan will evolve as implementation reveals better patterns. Adapt as needed.

---

## Technology Stack (Battle-Tested Choices)

### Core Language & Runtime

- **Python 3.11+** (latest stable)
  - Mature, excellent SQL/Excel libraries
  - Superior project structure vs PowerShell
  - PyInstaller well-supported
  - **Why not 3.12+**: Some libraries may lag in compatibility

### Critical Libraries

#### 1. Database Connectivity

**`pyodbc` 5.x** ✅ **VALIDATED**

- Native ODBC support, works with SQL Server 2008 R2 through 2022+
- Supports all Windows ODBC drivers (including legacy SQL Server Native Client)
- **ODBC Driver Requirement**: Microsoft ODBC Driver 17/18 for SQL Server
  - Pre-installed on most Windows Server editions
  - Fallback: SQL Server Native Client (shipped with SQL Server installs)
  - We'll bundle ODBC Driver 18 installer for edge cases

**Connection String Pattern**:

```python
# Modern (preferred)
DRIVER={ODBC Driver 18 for SQL Server};SERVER=...

# Fallback for older systems
DRIVER={SQL Server Native Client 11.0};SERVER=...

# Last resort (always available on Windows)
DRIVER={SQL Server};SERVER=...
```

#### 2. Excel Generation

**`openpyxl` 3.1+** ✅ **VALIDATED for advanced features**

- Pure Python (no Excel installation needed)
- **Confirmed capabilities**:
  - ✅ Icon sets (✅ ❌ ⚠️) via `IconSetRule`
  - ✅ Conditional formatting (color scales, data bars)
  - ✅ Charts (bar, line, pie, etc.)
  - ✅ Cell merging, formatting, borders
  - ✅ Rich styling (colors, fonts, alignment)

**Alternative considered**: `xlsxwriter` - rejected (no read capability, can't update existing files)

#### 3. Credential Encryption

**`pywin32` (Windows DPAPI)** ✅ **VALIDATED for offline use**

- Built into Windows (no external dependencies)
- User-scoped encryption via `CryptProtectData`/`CryptUnprotectData`
- **Perfect for offline**: No key management, tied to Windows user account
- Encrypted credentials only decryptable by same user on same machine

**Usage Pattern**:

```python
import win32crypt
encrypted = win32crypt.CryptProtectData(password_bytes, 'AutoDBAudit', None, None, None, 0)
decrypted = win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1]
```

#### 4. Deployment

**PyInstaller 6.x** ✅ **VALIDATED for single-exe Windows builds**

- Industry standard for Python → .exe
- **Best Practice Confirmed**: Use virtual environment with ONLY required packages
- **`--onefile`** mode: Single .exe (40-60 MB typical)
- Bundles Python interpreter + all dependencies

**Build Command** (initial):

```bash
pyinstaller --onefile --console \
  --add-data "queries;queries" \
  --add-data "config;config" \
  --icon=icon.ico \
  --name AutoDBAudit \
  main.py
```

### Supporting Libraries

- **`json`**: Configuration (stdlib, no install)
- **`argparse`**: CLI interface (stdlib)
- **`logging`**: Structured logging (stdlib)
- **`pathlib`**: Path handling (stdlib)
- **`datetime`**: Timestamps (stdlib)

---

## Architecture Design

### Module Breakdown

```
src/
├── core/
│   ├── __init__.py
│   ├── config_loader.py        # Load/validate JSON configs
│   ├── sql_connector.py        # Connection management, version detection
│   ├── query_executor.py       # Execute queries, handle results
│   ├── audit_engine.py         # Main orchestration
│   └── excel_generator.py      # Excel formatting/generation
├── remediation/
│   ├── __init__.py
│   ├── discrepancy_analyzer.py # Compare results vs requirements
│   ├── script_generator.py     # Generate T-SQL fix scripts
│   └── action_tracker.py       # Log actions taken
├── utils/
│   ├── __init__.py
│   ├── credential_manager.py   # DPAPI encryption/decryption
│   ├── version_detector.py     # SQL version → query selection
│   └── logger.py               # Logging configuration
└── hotfix/                     # PHASE 3 (optional)
    ├── __init__.py
    └── deployment_manager.py
```

### Key Design Decisions

#### 1. SQL Version Detection Strategy

**Approach**: Query `SERVERPROPERTY` on connection, select query variant

```python
def detect_sql_version(connection):
    version = execute_scalar(connection, "SELECT SERVERPROPERTY('ProductMajorVersion')")
    # Returns: '10' = 2008/2008R2, '11' = 2012, '13' = 2016, '14' = 2017, '15' = 2019, etc.
    
    if int(version) <= 10:
        return 'sql2008'  # Use legacy queries
    elif int(version) <= 13:
        return 'sql2016'  # Intermediate
    else:
        return 'sql2017'  # Modern syntax
```

**Query Organization** (Initial - may evolve):

```
queries/
├── sql2008/   # SQL Server 2008 R2 compatible
│   ├── instance_info.sql
│   ├── server_logins.sql
│   └── ...
├── sql2016/   # SQL Server 2012-2016
│   └── ... (similar structure)
└── sql2017/   # SQL Server 2017+ (modern)
    └── ... (similar structure)
```

**Alternative (may pivot to)**: Single query files with version-conditional logic embedded as comments

#### 2. Configuration Schema (INITIAL - will evolve)

**`config/sql_targets.json`**:

```json
{
  "targets": [
    {
      "id": "prod-sql1",
      "server": "192.168.1.10",
      "instance": "SQLPROD",
      "port": null,
      "auth": "sql",
      "username": "sa",
      "credential_file": "credentials/prod-sql1.enc",
      "connect_timeout": 30,
      "tags": ["production", "critical"]
    }
  ]
}
```

**`config/audit_config.json`**:

```json
{
  "organization": "Acme Corporation",
  "audit_year": 2025,
  "audit_date": "2025-12-15",
  "output": {
    "directory": "./output",
    "filename_pattern": "{organization}_SQL_Audit_{date}.xlsx",
    "include_charts": true,
    "verbosity": "detailed"
  },
  "requirements": {
    "minimum_sql_version": "2019",
    "allow_sa_enabled": false,
    "allow_default_instance": false,
    "allowed_test_databases": [],
    "password_complexity": true
  },
  "remediation": {
    "generate_scripts": true,
    "script_format": "sectioned",
    "include_rollback": true
  }
}
```

> **NOTE**: These schemas WILL evolve. Expect settings to migrate between files as we discover per-server vs global needs.

#### 3. **Remediation Workflow (Individual Fix Scripts)** ✨ **CRITICAL**

**Goal**: Generate individual T-SQL script files, user edits (comments out exceptions), tool detects what was applied

**Output Structure**:

```
output/
├── remediation_scripts/
│   ├── 01_Req04_Disable_SA_Account.sql
│   ├── 02_Req06_Fix_Service_Accounts.sql
│   ├── 03_Req07_Remove_Unused_Login_john_doe.sql
│   ├── 04_Req07_Remove_Unused_Login_test_user.sql
│   ├── 05_Req10_Disable_xp_cmdshell.sql
│   ├── 06_Req15_Remove_Test_DB_AdventureWorks.sql
│   ├── 07_Req16_Disable_AdHoc_Queries.sql
│   └── ... (one file per discrepancy)
└── Acme_SQL_Audit_2025-12-15.xlsx
```

**Script Format** (each file):

```sql
-- ============================================
-- AutoDBAudit Remediation Script
-- Generated: 2025-12-15 10:30:00
-- Server: PROD-SQL1\SQLPROD
-- Requirement: Req 4 - SA Account Must Be Disabled and Renamed
-- ============================================
-- CURRENT STATE:
--   SA account is ENABLED
--   SA account name has NOT been renamed
--
-- RECOMMENDED ACTION:
--   1. Disable SA login
--   2. Rename to '$@'
--
-- RISK LEVEL: CRITICAL
--
-- INSTRUCTIONS:
--   1. Review the script carefully
--   2. If you agree with the fix, UNCOMMENT the lines below
--   3. If this is an intentional exception, LEAVE COMMENTED
--   4. Run: AutoDBAudit.exe --apply-remediation
-- ============================================

USE master;
GO

-- UNCOMMENT BELOW TO APPLY FIX:
-- ALTER LOGIN [sa] DISABLE;
-- ALTER LOGIN [sa] WITH NAME = [$@];
-- PRINT 'AUTODB_ACTION_TAKEN: Disabled and renamed SA account';

GO
```

**Comment-Aware Execution Strategy**:

1. **User workflow**:
   - Review generated scripts in `output/remediation_scripts/`
   - For each script: decide to apply or skip
   - **To skip** (exception): Leave commented out
   - **To apply**: Uncomment the fix lines

2. **Tool detection** (`action_tracker.py`):
   - Parse each `.sql` file
   - Check if `ALTER LOGIN` or action statements are commented
   - **If commented**: Mark as `EXCEPTION - User Skipped`
   - **If uncommented**: Execute script, log as `ACTION TAKEN`
   - Look for `AUTODB_ACTION_TAKEN:` markers in output

3. **Execution**:

   ```bash
   # Per-script execution with rollback on failure
   AutoDBAudit.exe --apply-remediation --scripts output/remediation_scripts/
   ```

**Action Log Output** (`output/action_log.json`):

```json
{
  "audit_date": "2025-12-15",
  "execution_timestamp": "2025-12-15T14:30:00",
  "actions": [
    {
      "script": "01_Req04_Disable_SA_Account.sql",
      "server": "PROD-SQL1",
      "requirement": "Req04",
      "status": "APPLIED",
      "message": "Disabled and renamed SA account"
    },
    {
      "script": "03_Req07_Remove_Unused_Login_john_doe.sql",
      "server": "PROD-SQL1",
      "requirement": "Req07",
      "status": "EXCEPTION",
      "message": "User chose not to apply (left commented)"
    },
    {
      "script": "06_Req15_Remove_Test_DB_AdventureWorks.sql",
      "server": "PROD-SQL1",
      "requirement": "Req15",
      "status": "FAILED",
      "message": "Database in use, could not drop",
      "error": "Cannot drop database 'AdventureWorks' because it is currently in use."
    }
  ],
  "summary": {
    "total_scripts": 12,
    "applied": 8,
    "exceptions": 3,
    "failed": 1
  }
}
```

#### 4. **Incremental Audit History (Year-Over-Year)** ✨ **CRITICAL**

**Goal**: Same Excel workbook appended over years, tracking changes and progress

**Approach**: Multi-year workbook structure

**Sheet Organization** (Incremental Mode):

1. **Audit Summary** - Overview of all audits (NEW)
2. **2025 Cover** - This year's audit cover
3. **2025 Compliance** - This year's compliance status
4. **2025 Discrepancies** - This year's findings
5. **2025 ActionLog** - Actions taken in 2025
6. **2024 Cover** - Previous year (PRESERVED)
7. **2024 Compliance** - Previous year (PRESERVED)
8. **2024 Discrepancies** - Previous year (PRESERVED)
9. **2024 ActionLog** - Previous year (PRESERVED)
10. ... (continuing back in time)
11. **ServerHistory** - Server added/removed timeline (NEW)
12. **RequirementTrends** - Compliance % over time by requirement (NEW)

**Audit Summary Sheet** (tracks progression):

| Audit Date | Org Name | Servers Audited | Total Violations | Critical | Warnings | Actions Taken | Exceptions | Overall Compliance % |
|------------|----------|-----------------|------------------|----------|----------|---------------|------------|---------------------|
| 2025-12-15 | Acme     | 6               | 15               | 3        | 12       | 12            | 3          | 87%                 |
| 2024-12-20 | Acme     | 5               | 22               | 8        | 14       | 18            | 4          | 76%                 |
| 2024-06-15 | Acme     | 5               | 28               | 10       | 18       | 0             | 0          | 68%                 |

**ServerHistory Sheet**:

| Change Date | Server Name     | Event Type | Notes                        |
|-------------|-----------------|------------|------------------------------|
| 2025-06-01  | PROD-SQL6       | ADDED      | New production server        |
| 2024-11-20  | TEST-SQL2       | REMOVED    | Decommissioned test server   |
| 2024-01-15  | PROD-SQL1       | ADDED      | Initial audit                |

**RequirementTrends Sheet**:

| Requirement | Description       | 2023 | 2024 | 2025 | Trend   |
|-------------|-------------------|------|------|------|---------|  
| Req04       | SA Account        | ❌   | ⚠️   | ✅   | ⬆️ Fixed |
| Req06       | Service Accounts  | ⚠️   | ⚠️   | ⚠️   | ➡️ Same  |
| Req15       | Test Databases    | ❌   | ❌   | ❌   | ⬇️ Worse |

**Implementation**:

```python
def append_to_audit_workbook(previous_workbook_path, new_audit_data):
    # Load existing workbook
    wb = openpyxl.load_workbook(previous_workbook_path)
    
    # Add new year's sheets
    current_year = new_audit_data['audit_year']
    wb.create_sheet(f"{current_year} Cover", 1)  # Insert at position 1
    wb.create_sheet(f"{current_year} Compliance", 2)
    wb.create_sheet(f"{current_year} Discrepancies", 3)
    
    # Update Audit Summary sheet (prepend new row)
    if 'Audit Summary' not in wb.sheetnames:
        wb.create_sheet('Audit Summary', 0)
    summary_sheet = wb['Audit Summary']
    summary_sheet.insert_rows(2)  # Insert after header
    # ... populate with new data
    
    # Update ServerHistory if servers changed
    # ... detect added/removed servers, append rows
    
    # Regenerate RequirementTrends chart
    # ... 
    
    wb.save(f"{org_name}_SQL_Audit_History.xlsx")
```

**CLI Usage**:

```bash
# First audit (creates new workbook)
AutoDBAudit.exe --audit --config config/audit_config.json

# Next year (appends to existing)
AutoDBAudit.exe --audit --config config/audit_config.json \
  --append-to output/Acme_SQL_Audit_History.xlsx
```

#### 5. **Hotfix Deployment Module** ✨ **CRITICAL**

**Goal**: Centralized SQL Server patch deployment with fail-recovery

**Hotfix Configuration** (`config/hotfix_mapping.json`):

```json
{
  "hotfixes": {
    "2022": {
      "edition": "SQL Server 2022",
      "files": [
        {
          "file": "hotfixes/SQLServer2022-KB5031908-x64.exe",
          "description": "CU10 for SQL Server 2022",
          "order": 1,
          "required": true
        }
      ]
    },
    "2019": {
      "edition": "SQL Server 2019",
      "files": [
        {
          "file": "hotfixes/SQLServer2019-KB5029378-x64.exe",
          "description": "CU22 for SQL Server 2019",
          "order": 1,
          "required": true
        }
      ]
    },
    "2016": {
      "edition": "SQL Server 2016",
      "files": [
        {
          "file": "hotfixes/SQLServer2016-SP3-KB5003279-x64.exe",
          "description": "Service Pack 3",
          "order": 1,
          "required": true
        },
        {
          "file": "hotfixes/SQLServer2016-KB5029186-x64.exe",
          "description": "CU17 for SP3",
          "order": 2,
          "required": false
        }
      ]
    },
    "2008R2": {
      "edition": "SQL Server 2008 R2",
      "files": [
        {
          "file": "hotfixes/SQLServer2008R2-SP3-KB2979597-x64.exe",
          "description": "Service Pack 3 (FINAL - NO LONGER SUPPORTED)",
          "order": 1,
          "required": true,
          "warning": "SQL Server 2008 R2 is out of support. Upgrade recommended."
        }
      ]
    }
  }
}
```

**Deployment State Tracking** (`output/hotfix_deployment_state.json`):

```json
{
  "last_run": "2025-12-15T16:00:00",
  "servers": [
    {
      "server": "PROD-SQL1",
      "version": "2019",
      "current_build": "15.0.4298.1",
      "target_build": "15.0.4322.2",
      "status": "SUCCESS",
      "files_applied": [
        {
          "file": "SQLServer2019-KB5029378-x64.exe",
          "status": "SUCCESS",
          "timestamp": "2025-12-15T16:15:00"
        }
      ],
      "requires_restart": true
    },
    {
      "server": "PROD-SQL2",
      "version": "2016",
      "current_build": "13.0.6300.2",
      "target_build": "13.0.6435.1",
      "status": "PARTIAL_FAILURE",
      "files_applied": [
        {
          "file": "SQLServer2016-SP3-KB5003279-x64.exe",
          "status": "SUCCESS",
          "timestamp": "2025-12-15T16:20:00"
        },
        {
          "file": "SQLServer2016-KB5029186-x64.exe",
          "status": "FAILED",
          "error": "Setup failed: The instance MSSQLSERVER is currently in use.",
          "timestamp": "2025-12-15T16:45:00"
        }
      ],
      "retry_recommended": true
    },
    {
      "server": "TEST-SQL1",
      "version": "2022",
      "status": "PENDING",
      "reason": "Previous run was cancelled"
    }
  ]
}
```

**Deployment Workflow**:

1. **Pre-flight checks**:
   - Detect SQL Server version on each target
   - Check disk space (hotfix size × 2)
   - Verify no active connections (or warn)
   - Check Windows Update service status

2. **Execution** (per server):

   ```python
   for server in targets:
       version = detect_version(server)
       hotfixes = load_hotfix_mapping()[version]
       
       for hotfix_file in sorted(hotfixes, key=lambda x: x['order']):
           try:
               copy_to_server(server, hotfix_file['file'])
               result = execute_remote_installer(server, hotfix_file)
               log_result(server, hotfix_file, "SUCCESS")
               update_state(server, hotfix_file, "SUCCESS")
           except Exception as e:
               log_result(server, hotfix_file, "FAILED", str(e))
               update_state(server, hotfix_file, "FAILED")
               if hotfix_file['required']:
                   break  # Skip remaining hotfixes for this server
   ```

3. **Retry Failed Servers**:

   ```bash
   # Auto-detects failed servers from state file
   AutoDBAudit.exe --deploy-hotfixes --retry-failed
   
   # Retry specific server
   AutoDBAudit.exe --deploy-hotfixes --server PROD-SQL2 --resume
   ```

4. **Real-time Progress**:

   ```
   [2025-12-15 16:00:00] Starting hotfix deployment for 6 servers...
   [2025-12-15 16:00:05] PROD-SQL1: Detected SQL Server 2019 (15.0.4298.1)
   [2025-12-15 16:00:10] PROD-SQL1: Copying SQLServer2019-KB5029378-x64.exe (450 MB)
   [2025-12-15 16:02:30] PROD-SQL1: File copied successfully
   [2025-12-15 16:02:35] PROD-SQL1: Executing installer...
   [2025-12-15 16:15:22] PROD-SQL1: ✅ SUCCESS - Hotfix applied (CU22)
   [2025-12-15 16:15:25] PROD-SQL1: ⚠️  Server restart required
   
   [2025-12-15 16:15:30] PROD-SQL2: Detected SQL Server 2016 (13.0.6300.2)
   [2025-12-15 16:15:35] PROD-SQL2: Copying SQLServer2016-SP3-KB5003279-x64.exe (520 MB)
   [2025-12-15 16:18:10] PROD-SQL2: File copied successfully
   [2025-12-15 16:18:15] PROD-SQL2: Executing installer...
   [2025-12-15 16:30:42] PROD-SQL2: ✅ SUCCESS - SP3 applied
   [2025-12-15 16:30:50] PROD-SQL2: Copying SQLServer2016-KB5029186-x64.exe (380 MB)
   [2025-12-15 16:33:20] PROD-SQL2: File copied successfully
   [2025-12-15 16:33:25] PROD-SQL2: Executing installer...
   [2025-12-15 16:45:10] PROD-SQL2: ❌ FAILED - CU17 failed to install
   [2025-12-15 16:45:10] PROD-SQL2: Error: The instance MSSQLSERVER is currently in use.
   [2025-12-15 16:45:12] PROD-SQL2: ℹ️  Retry recommended after stopping SQL services
   
   [2025-12-15 16:45:15] USER CANCELLED (Ctrl+C)
   [2025-12-15 16:45:16] Deployment paused. State saved to hotfix_deployment_state.json
   [2025-12-15 16:45:16] Remaining servers: TEST-SQL1, DEV-SQL1, DEV-SQL2
   [2025-12-15 16:45:16] To resume: AutoDBAudit.exe --deploy-hotfixes --resume
   ```

**Hotfix Report Generation** (`output/hotfix_deployment_report.xlsx`):

| Server    | Version | Pre-Build   | Post-Build  | Status          | Files Applied | Requires Restart | Notes                     |
|-----------|---------|-------------|-------------|-----------------|---------------|------------------|---------------------------|
| PROD-SQL1 | 2019    | 15.0.4298.1 | 15.0.4322.2 | ✅ SUCCESS      | CU22          | Yes              |                           |
| PROD-SQL2 | 2016    | 13.0.6300.2 | 13.0.6419.1 | ⚠️ PARTIAL      | SP3           | Yes              | CU17 failed (in use)      |
| TEST-SQL1 | 2022    | 16.0.4085.2 | 16.0.4085.2 | ⏸️ PENDING      | None          | No               | Not started (cancelled)   |

**Append to Audit Workbook**:

- Add new sheet: **"2025 Hotfix Deployment"**
- Include in **ActionLog** summary
- Update **InstanceInfo** with new build numbers

#### 6. Excel Report Structure (Revised)

**Sheet Organization** (after all features):

1. **Audit Summary** - Multi-year overview (if incremental)
2. **{Year} Cover** - This year's audit cover
3. **{Year} Compliance Summary** - Compliance % per requirement, icons ✅❌⚠️
4. **{Year} Discrepancies** - ALL violations found
5. **{Year} ActionLog** - Actions taken this audit
6. **{Year} Hotfix Deployment** - Patch deployment results
7. **InstanceInfo** - Server details
8. **ServerLogins** - Login inventory
9. **PasswordPolicy** - Req 5 compliance
10. **ServiceAccounts** - Req 6 compliance
11. **UnusedLogins** - Req 7 findings
12. **ServerRoles** - Req 8 (sysadmin members)
13. **DatabaseUsers** - Per-database users
14. **DisabledFeatures** - Req 10, 16, 18, 19, 20, 21 status
15. **ProtocolStatus** - Req 17
16. **TriggerInventory** - Req 12
17. **TestDatabases** - Req 15 findings
18. **ServerHistory** - Server lifecycle (added/removed)
19. **RequirementTrends** - Compliance over time (chart)
20. **Previous Years...** (if incremental)

**Enhanced Formatting**:

- Icon sets for compliance status
- Color-coded severity (red = critical, yellow = warning, green = ok)
- Charts: Compliance pie chart, violations by category bar chart, trend lines
- Server separators within data sheets
- Merged cells for readability

---

## Development Roadmap

### Phase 0: Foundation & Setup (2-3 hours)

**Goal**: Environment setup, skeleton project structure

**Tasks**:

- [ ] Create Python virtual environment
- [ ] Install core dependencies (`pip install pyodbc openpyxl pywin32`)
- [ ] Create project directory structure
- [ ] Initialize Git repository
- [ ] Copy legacy SQL queries to new `queries/` structure
- [ ] Create configuration templates
- [ ] Set up logging framework

**Deliverable**: Empty skeleton that runs without errors

---

### Phase 1: MVP - Audit Only (1-2 days)

**Goal**: Generate basic audit report (no remediation yet)

#### 1.1: Core Infrastructure

- [ ] Implement `config_loader.py` - Load JSON configs
- [ ] Implement `credential_manager.py` - DPAPI encrypt/decrypt
- [ ] Implement `sql_connector.py`:
  - [ ] Build connection strings
  - [ ] Test connectivity
  - [ ] Version detection
- [ ] Implement `logger.py` - Structured logging

**Validation**: Can connect to test SQL Server, detect version

#### 1.2: Query Execution

- [ ] Convert 1-2 legacy queries to SQL 2008 compatible format
- [ ] Implement `version_detector.py` - Select query path by version
- [ ] Implement `query_executor.py`:
  - [ ] Execute query
  - [ ] Convert results to Python dicts
  - [ ] Tag with server name, timestamp
- [ ] Test on SQL 2008 R2, 2019+

**Validation**: Successfully run queries against multiple SQL versions

#### 1.3: Excel Generation (Basic)

- [ ] Implement `excel_generator.py`:
  - [ ] Create workbook
  - [ ] Add sheets
  - [ ] Write data rows
  - [ ] Basic formatting (headers, borders, column widths)
  - [ ] Freeze panes, auto-filter
- [ ] Test multi-server report

**Validation**: Generate Excel file with data from 2+ servers

#### 1.4: Audit Engine Orchestration

- [ ] Implement `audit_engine.py`:
  - [ ] Load configs
  - [ ] Connect to all targets
  - [ ] Execute all queries
  - [ ] Aggregate results
  - [ ] Generate Excel
- [ ] Add CLI interface (`main.py`)
  - [ ] `--audit` mode
  - [ ] `--config` path
- [ ] Add error handling (connection failures, query errors)

**Validation**: End-to-end audit from command line

**MVP Complete**: `AutoDBAudit.exe --audit --config config/audit_config.json`

---

### Phase 2: Remediation & Analysis (1-2 days)

**Goal**: Analyze discrepancies, generate fix scripts

#### 2.1: Discrepancy Analysis

- [ ] Define requirement rules in code/config
- [ ] Implement `discrepancy_analyzer.py`:
  - [ ] Check SA account status (Req 4)
  - [ ] Check service accounts (Req 6)
  - [ ] Check unused logins (Req 7)
  - [ ] Check disabled features (Req 10, 16-21)
  - [ ] Check test databases (Req 15)
- [ ] Add **Discrepancies** sheet to Excel
- [ ] Color-code violations

**Validation**: Discrepancies correctly identified

#### 2.2: Script Generation

- [ ] Implement `script_generator.py`:
  - [ ] Generate T-SQL for SA rename/disable
  - [ ] Generate scripts for service account changes
  - [ ] Generate unused login cleanup
  - [ ] Generate feature disable scripts
  - [ ] Section scripts by requirement
  - [ ] Comment out by default (user must uncomment)
- [ ] Output to `output/remediation_scripts/` directory
- [ ] Include headers with explanations

**Validation**: Scripts generated, can be executed manually

#### 2.3: Action Tracking

- [ ] Implement `action_tracker.py`:
  - [ ] Log script executions
  - [ ] Log exceptions (user skipped)
  - [ ] Timestamp all actions
- [ ] Add `--apply-remediation` mode (executes scripts)
- [ ] Generate action log JSON/CSV
- [ ] Add **ActionLog** sheet to report

**Validation**: Track which scripts were run, which were skipped

#### 2.4: Report Update Mode

- [ ] Add `--update-report` mode
- [ ] Load previous Excel report
- [ ] Re-run audit
- [ ] Compare old vs new
- [ ] Mark items as:
  - `RESOLVED` (was violation, now compliant)
  - `EXCEPTION` (was violation, still is, user documented exception)
  - `NEW VIOLATION` (newly discovered)
- [ ] Preserve history

**Validation**: Update existing report after running remediation

**Phase 2 Complete**: Full audit → remediation → action tracking cycle

---

### Phase 3: Polish & Hotfix Module (Optional, 1 day)

**Goal**: Advanced Excel formatting, hotfix deployment

#### 3.1: Advanced Excel Features

- [ ] Icon sets (✅ ❌ ⚠️)
- [ ] Conditional formatting rules
- [ ] Compliance summary chart (pie chart)
- [ ] Violations by category chart (bar chart)
- [ ] Cover sheet with org branding
- [ ] Color-coded severity throughout

#### 3.2: Hotfix Deployment (Separate Module)

- [ ] Implement `hotfix/deployment_manager.py`
- [ ] Remote command execution (PSRemoting/WMI)
- [ ] Pre-flight checks (disk space, services)
- [ ] Hotfix installation
- [ ] Real-time progress logging
- [ ] Deployment report

**Scope Note**: This may become a separate tool if complexity grows

---

## Build & Deployment Process

### Development Build

```bash
# In virtual environment
python main.py --audit --config config/audit_config.json
```

### Production Build (Self-Contained Executable)

**Step 1: Create clean virtual environment**

```bash
python -m venv venv_build
venv_build\Scripts\activate
pip install pyodbc openpyxl pywin32 pyinstaller
```

**Step 2: Build with PyInstaller**

```bash
pyinstaller AutoDBAudit.spec
```

**`AutoDBAudit.spec`** (build configuration):

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('queries', 'queries'),
        ('config', 'config'),
    ],
    hiddenimports=['pyodbc', 'openpyxl', 'win32crypt'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AutoDBAudit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress executable
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Console application
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'  # Optional
)
```

**Step 3: Create deployment package**

```
AutoDBAudit_Deployment/
├── AutoDBAudit.exe                   # Main executable
├── config/
│   ├── sql_targets.example.json     # User must customize
│   ├── audit_config.example.json    # User must customize
│   └── README.txt                   # Instructions
├── drivers/
│   └── msodbcsql_18.msi             # ODBC Driver installer (optional)
├── RUN_AUDIT.bat                    # Convenience launcher
└── docs/
    ├── Quick_Start.pdf
    └── Configuration_Guide.pdf
```

**`RUN_AUDIT.bat`**:

```batch
@echo off
echo AutoDBAudit - SQL Server Security Audit Tool
echo.

REM Check for config files
if not exist "config\sql_targets.json" (
    echo ERROR: config\sql_targets.json not found!
    echo Please copy sql_targets.example.json to sql_targets.json and customize.
    pause
    exit /b 1
)

if not exist "config\audit_config.json" (
    echo ERROR: config\audit_config.json not found!
    echo Please copy audit_config.example.json to audit_config.json and customize.
    pause
    exit /b 1
)

echo Running audit...
AutoDBAudit.exe --audit --config config\audit_config.json

echo.
echo Audit complete. Check the output\ directory for reports.
pause
```

---

## Critical Decision Points & Risks

### 1. SQL 2008 R2 Query Compatibility

**Risk**: Modern queries may fail on SQL 2008 R2
**Mitigation**:

- Test EVERY query on SQL 2008 R2 instance
- Avoid: `STRING_AGG`, `TRY_CAST`, `CONCAT_WS`, newer DMVs
- Use XML PATH for string aggregation
- Check `SERVERPROPERTY('ProductMajorVersion')` before using version-specific features

**Validation Plan**: Set up SQL Server 2008 R2 Docker container for testing

### 2. ODBC Driver Availability

**Risk**: Target machine may lack ODBC driver
**Mitigation**:

- Include ODBC Driver 18 installer in deployment package
- Implement driver detection on startup
- Provide clear error message with installation instructions
- Fallback to older drivers ({SQL Server Native Client}, {SQL Server})

**Pre-flight Check**:

```python
def check_odbc_drivers():
    import pyodbc
    drivers = pyodbc.drivers()
    preferred = ['ODBC Driver 18 for SQL Server', 'ODBC Driver 17 for SQL Server']
    fallback = ['SQL Server Native Client 11.0', 'SQL Server']
    
    for driver in preferred:
        if driver in drivers:
            return driver
    for driver in fallback:
        if driver in drivers:
            return driver
    
    raise RuntimeError("No SQL Server ODBC driver found. Please install ODBC Driver 18.")
```

### 3. Credential Security

**Risk**: Credentials stored insecurely or lost between runs
**Mitigation**:

- Use Windows DPAPI (encrypted, tied to user)
- Never store plaintext passwords in JSON
- Support interactive credential prompting
- Credentials stored in separate `.enc` files (not in main config)

**Credential Flow**:

1. User runs tool first time
2. Tool prompts for SQL passwords
3. Passwords encrypted via DPAPI → saved to `credentials/*.enc`
4. Subsequent runs: auto-load from `.enc` files
5. If decryption fails (different user/machine): prompt again

### 4. Excel File Size & Performance

**Risk**: Large multi-server audits may create huge Excel files
**Mitigation**:

- Benchmark with 10+ servers
- If too large: Consider splitting into multiple workbooks
- Use openpyxl efficiently (write-only mode for large datasets)
- May need to pivot from `--onefile` to `--onedir` if bundle size exceeds 100MB

### 5. PyInstaller Antivirus False Positives

**Risk**: Some antivirus software flags PyInstaller executables
**Mitigation**:

- Code-sign the executable (optional, requires certificate)
- Provide hash (SHA256) in documentation
- Test on Windows Defender
- Document expected behavior for IT teams

---

## Testing Strategy

### Unit Testing (Optional for MVP, recommended for Phase 2+)

- Test SQL version detection
- Test query result parsing
- Test DPAPI encryption/decryption
- Test Excel generation edge cases

### Integration Testing (Critical)

1. **SQL Version Compatibility**:
   - Test on SQL Server 2008 R2 (Docker or VM)
   - Test on SQL Server 2019
   - Test on SQL Server 2022
   - Verify all queries execute without errors

2. **Multi-Server Scenarios**:
   - Test with 1 server
   - Test with 5+ servers
   - Test mixed authentication (Windows + SQL)
   - Test connection failures (unreachable servers)

3. **Offline Deployment**:
   - Build .exe on dev machine
   - Copy to air-gapped VM (fresh Windows install)
   - Run without internet
   - Verify ODBC driver detection
   - Verify credential prompting

4. **Report Quality**:
   - Open generated Excel in Microsoft Excel (not just LibreOffice)
   - Verify formatting (colors, borders, icons)
   - Verify charts render correctly
   - Test on Excel 2016, 2019, Microsoft 365

### Acceptance Testing

- Complete audit of 3+ SQL Server instances
- Generate remediation scripts
- Execute scripts (in test environment)
- Update report to show resolved items
- Verify action log accuracy

---

## Development Environment Setup

### Prerequisites

- Windows 10/11 or Windows Server 2016+
- Python 3.11+
- Git
- Visual Studio Code (or PyCharm)
- Access to SQL Server 2008 R2 and 2019+ instances (for testing)

### Initial Setup Commands

```bash
# Clone repository
git clone <repo-url>
cd AutoDBAudit

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import pyodbc, openpyxl, win32crypt; print('All dependencies OK')"
```

**`requirements.txt`**:

```
pyodbc>=5.0.0
openpyxl>=3.1.0
pywin32>=306
```

**Development Dependencies** (optional):

```
pytest>=7.4.0
black>=23.0.0  # Code formatter
flake8>=6.0.0  # Linter
```

---

## CLI Interface (Initial Design)

```bash
# Run full audit
AutoDBAudit.exe --audit --config config/audit_config.json

# Run audit with custom SQL targets
AutoDBAudit.exe --audit --config config/audit_config.json --targets config/sql_targets_prod.json

# Generate remediation scripts (no execution)
AutoDBAudit.exe --remediate --config config/audit_config.json --dry-run

# Apply remediation scripts
AutoDBAudit.exe --remediate --config config/audit_config.json --apply

# Update existing report after fixes
AutoDBAudit.exe --update-report --previous output/Acme_SQL_Audit_2025-12-01.xlsx

# Check ODBC drivers
AutoDBAudit.exe --check-drivers

# Encrypt credentials interactively
AutoDBAudit.exe --setup-credentials --targets config/sql_targets.json

# Deploy hotfixes (Phase 3)
AutoDBAudit.exe --deploy-hotfixes --targets config/sql_targets.json --hotfix-dir C:\hotfixes
```

---

## Success Metrics

### MVP (Phase 1)

✅ Connects to SQL Server 2008 R2, 2019+  
✅ Executes all 17+ queries  
✅ Generates Excel report with 15+ sheets  
✅ Single .exe under 60 MB  
✅ Works offline (no internet required)  
✅ Total execution time < 5 minutes for 5 servers  

### Phase 2

✅ Identifies discrepancies across all 22 requirements  
✅ Generates remediation scripts  
✅ Tracks actions taken  
✅ Updates existing reports  

### Phase 3

✅ Advanced Excel formatting (icons, charts)  
✅ Professional-looking output  
✅ Optional hotfix deployment  

### Ultimate Success

✅ Deploy to 3+ organizations successfully  
✅ Zero errors on offline deployment  
✅ Reports accepted by auditors without modification  
✅ Saves 8+ hours of manual work per audit  

---

## Next Steps

1. **Immediate**: Create Phase 0 skeleton
2. **Day 1**: Implement Phase 1.1-1.2 (connectivity + query execution)
3. **Day 2**: Implement Phase 1.3-1.4 (Excel generation + orchestration)
4. **Day 3**: Test MVP end-to-end, fix bugs
5. **Day 4**: Begin Phase 2 (remediation)

**Ready to start? Let's build Phase 0!** 🚀
