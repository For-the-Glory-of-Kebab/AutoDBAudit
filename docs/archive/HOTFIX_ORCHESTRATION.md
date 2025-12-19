# Hotfix Orchestration

> **Audience**: Operators deploying SQL Server updates via AutoDBAudit, and developers extending the hotfix system.

---

## Overview

### What It Is

The hotfix subsystem is a **centralized SQL Server update orchestrator**. From a single audit PC, it:

1. **Plans** which cumulative updates each SQL Server instance needs
2. **Executes** installers on remote servers via PowerShell Remoting
3. **Logs** every step centrally in SQLite
4. **Supports** resume and retry of failed deployments

### What It Is NOT

- ❌ A simple local shortcut script
- ❌ A generic software deployment system (SCCM, Ansible, etc.)
- ❌ A Windows Update replacement
- ❌ An OS patching tool

It is purpose-built for SQL Server cumulative updates only.

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           HOTFIX WORKFLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│   │  AUDIT   │ →  │   PLAN   │ →  │ EXECUTE  │ →  │  VERIFY  │ →  LOG     │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘             │
│                                                                             │
│   Detect SQL       Compare to      Run updates     Re-check        Record  │
│   versions         mapping         remotely        versions        in DB   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Assumptions & Environment

### Audit PC Requirements

| Requirement | Detail |
|-------------|--------|
| Operating System | Windows 10/11 or Server 2016+ |
| PowerShell | 5.1+ with Remoting enabled |
| Network | Can reach all SQL Servers on WinRM port (5985/5986) |
| CU Executables | Available locally or via UNC share |
| Privileges | Domain account with admin rights on target SQL Servers |

### Target Server Requirements

| Requirement | Detail |
|-------------|--------|
| Domain-joined | Yes (for Kerberos-based remoting) |
| WinRM enabled | `Enable-PSRemoting -Force` on each target |
| Firewall | Port 5985 (HTTP) or 5986 (HTTPS) open |
| SQL Service account | Able to be restarted by the operator |

### Operator Privileges

The operator running AutoDBAudit hotfix commands must have:

- Local Administrator rights on target servers
- Permission to stop/start SQL Server services
- (Optional) Permission to reboot servers if CU requires it

---

## Configuration

### `config/hotfix_mapping.json`

This file maps SQL Server versions to required cumulative updates.

```json
{
  "schema_version": 1,
  "mappings": [
    {
      "version_family": "2022",
      "edition_filter": null,
      "min_build": "16.0.4085.0",
      "target_build": "16.0.4165.4",
      "description": "CU16 for SQL Server 2022",
      "files": [
        {
          "filename": "SQLServer2022-KB5048038-x64.exe",
          "path": "hotfixes/2022/",
          "order": 1,
          "required": true,
          "parameters": "/quiet /IAcceptSQLServerLicenseTerms /Action=Patch /AllInstances"
        }
      ],
      "requires_restart": true,
      "notes": "Apply during maintenance window"
    },
    {
      "version_family": "2019",
      "min_build": "15.0.4298.0",
      "target_build": "15.0.4395.2",
      "description": "CU30 for SQL Server 2019",
      "files": [
        {
          "filename": "SQLServer2019-KB5046859-x64.exe",
          "path": "hotfixes/2019/",
          "order": 1,
          "required": true,
          "parameters": "/quiet /IAcceptSQLServerLicenseTerms /Action=Patch /AllInstances"
        }
      ],
      "requires_restart": true
    },
    {
      "version_family": "2016",
      "min_build": "13.0.6300.0",
      "target_build": "13.0.6441.1",
      "description": "SP3 + CU17 for SQL Server 2016",
      "files": [
        {
          "filename": "SQLServer2016-SP3-KB5003279-x64.exe",
          "path": "hotfixes/2016/",
          "order": 1,
          "required": true,
          "parameters": "/quiet /IAcceptSQLServerLicenseTerms"
        },
        {
          "filename": "SQLServer2016-KB5029186-x64.exe",
          "path": "hotfixes/2016/",
          "order": 2,
          "required": false,
          "parameters": "/quiet /IAcceptSQLServerLicenseTerms /Action=Patch /AllInstances"
        }
      ],
      "requires_restart": true
    }
  ],
  "unsupported_versions": [
    {
      "version_family": "2008R2",
      "message": "SQL Server 2008 R2 is out of support. No CUs available."
    }
  ]
}
```

### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `version_family` | string | "2022", "2019", "2016", "2014", etc. |
| `edition_filter` | string? | Optional: "Standard", "Enterprise", etc. |
| `min_build` | string | Minimum build that needs this update |
| `target_build` | string | Build version after applying update |
| `files[]` | array | Ordered list of installers to run |
| `files[].path` | string | Relative or UNC path to the executable |
| `files[].order` | int | Execution sequence (1, 2, 3...) |
| `files[].required` | bool | If true, failure stops further steps |
| `files[].parameters` | string | CLI arguments for silent install |
| `requires_restart` | bool | Whether SQL/server restart is needed |

### CU Executable Storage

Executables can be stored:

1. **Locally on audit PC**: `C:\AutoDBAudit\hotfixes\2022\SQLServer2022-KB5048038-x64.exe`
2. **UNC share**: `\\fileserver\patches\sql\2022\SQLServer2022-KB5048038-x64.exe`

The executor copies files to target servers before running (or accesses via UNC if network allows).

### Target Server Identification

Targets come from:

1. **`config/sql_targets.json`**: Explicit list of servers
2. **Previous audits**: Servers in SQLite `servers` table with `is_active=1`

---

## Planning Phase

### How the Planner Works

```
For each active server/instance:
  1. Get current ProductVersion (from audit or direct query)
  2. Parse version_family (e.g., "15.0.x" → 2019)
  3. Look up in hotfix_mapping.json
  4. If current_build < target_build:
       → Create HotfixTarget with status=PENDING
       → Create HotfixStep(s) for each file in order
  5. If version is in unsupported_versions:
       → Log warning, skip this server
```

### Data Structures

**Implementation Status**: 🔄 Design intent (stubs exist)

```python
@dataclass
class HotfixTarget:
    id: int
    hotfix_run_id: int
    server_id: int
    pre_build: str
    post_build: str | None
    status: str  # pending, in_progress, success, partial, failed, skipped
    requires_restart: bool
    error_message: str | None

@dataclass
class HotfixStep:
    id: int
    hotfix_target_id: int
    step_order: int
    installer_file: str
    description: str
    status: str  # pending, running, success, failed
    started_at: datetime | None
    completed_at: datetime | None
    exit_code: int | None
    output: str | None
```

### Safeguards in Planning

| Safeguard | Behavior |
|-----------|----------|
| Unsupported version (2008 R2) | Logged with warning, not scheduled |
| Already at target build | Skipped, logged as "up to date" |
| Missing installer file | Plan fails early with clear error |
| Unknown version family | Logged as "no mapping available" |

---

## Execution Phase

### Remote Execution Method

**Implementation Status**: 🔄 Design intent (not yet implemented)

The executor uses **PowerShell Remoting** to run installers on target servers:

```powershell
# Conceptual flow (actual implementation may vary)
Invoke-Command -ComputerName $targetServer -ScriptBlock {
    param($installerPath, $parameters)
    Start-Process -FilePath $installerPath -ArgumentList $parameters -Wait -PassThru
} -ArgumentList $localPath, $params
```

### Concurrency Model

| Setting | Default | Description |
|---------|---------|-------------|
| `max_concurrent_servers` | 3 | Servers patched in parallel |
| `steps_per_server` | Sequential | Installers run one at a time on each server |

```
Worker 1: Server-A → Step1 → Step2 → Done
Worker 2: Server-B → Step1 → Step2 → Done
Worker 3: Server-C → Step1 → Step2 → Done
           ↓
Worker 1: Server-D → ...
```

### Command Line Construction

Command lines are built from the mapping file—no hardcoded paths:

```python
full_path = resolve_path(mapping.files[i].path, mapping.files[i].filename)
command = f'"{full_path}" {mapping.files[i].parameters}'
```

### Determining Success/Failure

| Method | Implementation |
|--------|----------------|
| **Exit code** | 0 = success, 3010 = reboot required, others = failure |
| **Post-check** | Re-query `SELECT SERVERPROPERTY('ProductVersion')` |
| **Timeout** | Configurable; default 30 minutes per step |

---

## History & Logging

### SQLite Tables

All hotfix operations are recorded in `output/history.db`:

| Table | Purpose |
|-------|---------|
| `hotfix_runs` | Each deployment session |
| `hotfix_targets` | Per-server status within a run |
| `hotfix_steps` | Individual installer executions |

See [`docs/sqlite_schema.md`](sqlite_schema.md) for full schema.

### Integration with Audit History

- `hotfix_targets.server_id` → FK to `servers.id`
- Results appear in Excel reports: **{Year} Hotfix Deployment** sheet
- Trend data shows patch status over time

### Log Verbosity

Console and file logs include:

- Timestamps for each operation
- Server/instance being patched
- Installer filename and exit code
- Error messages and stack traces on failure

---

## Safety Features

### Implemented / Planned Safeguards

| Feature | Status | Description |
|---------|--------|-------------|
| **Dry-run mode** | 🔄 Planned | `--hotfix-plan` shows what would happen |
| **Confirmation prompt** | 🔄 Planned | Requires `--yes` or interactive confirm for production |
| **Max concurrency** | 🔄 Planned | Limits parallel operations |
| **Resume mode** | 🔄 Planned | `--resume` continues from last failure |
| **Pre-flight checks** | 🔄 Planned | Disk space, connectivity, service status |

### Operator Best Practices

> [!WARNING]
> **Always test on non-production servers first!**

1. Run `--hotfix-plan` to review proposed changes
2. Test on dev/test environment
3. Schedule production deployments during maintenance window
4. Have rollback plan (backups, previous media)
5. Monitor after deployment for service stability

### Cluster Considerations

> [!CAUTION]
> **Cluster-aware rolling updates are NOT automatically handled.**

If patching Always On Availability Groups or FCIs:

- Operator must sequence nodes manually
- Use `--server` flag to target one node at a time
- Fail over before patching primary
- Verify replica health before proceeding

---

## CLI Usage

### Current / Planned Commands

**Implementation Status**: 🔄 Partially implemented (flags exist, logic pending)

```bash
# Show plan without executing
AutoDBAudit.exe --hotfix-plan --config config/audit_config.json

# Deploy hotfixes to all pending servers
AutoDBAudit.exe --deploy-hotfixes --config config/audit_config.json

# Deploy to specific server only
AutoDBAudit.exe --deploy-hotfixes --server PROD-SQL1

# Resume interrupted run
AutoDBAudit.exe --deploy-hotfixes --resume

# Retry only failed targets from last run
AutoDBAudit.exe --deploy-hotfixes --retry-failed

# Skip confirmation prompt
AutoDBAudit.exe --deploy-hotfixes --yes
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All targets succeeded |
| 1 | One or more targets failed |
| 2 | Configuration error |
| 3 | Connectivity error |
| 130 | User cancelled (Ctrl+C) |

---

## Out of Scope / Limitations

### Not Supported

| Feature | Reason |
|---------|--------|
| **Cluster-aware rolling** | Requires AG/FCI awareness; manual sequencing for now |
| **Installer rollback** | Beyond what SQL setup.exe provides natively |
| **OS patching** | This tool is SQL Server only |
| **Non-Windows SQL** | Linux SQL Server not in scope |

### Assumptions

| Topic | Assumption |
|-------|------------|
| **Maintenance window** | Operator is responsible for scheduling |
| **Reboots** | Tool reports "restart required"; operator decides when |
| **Backups** | Operator ensures backups exist before patching |
| **Service accounts** | Remoting identity has necessary privileges |

### Known Limitations

- No automatic node failover before patching
- No integration with WSUS/SCCM
- CU files must be pre-downloaded (offline deployment)
- Single audit PC as orchestrator (no distributed execution)

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| WinRM connection refused | Run `Enable-PSRemoting -Force` on target |
| Access denied | Ensure operator account is local admin on target |
| Installer hangs | Check if interactive mode; use `/quiet` flag |
| Exit code 3010 | Restart required; not a failure |
| File not found | Verify path in hotfix_mapping.json |

### Debug Mode

```bash
AutoDBAudit.exe --deploy-hotfixes --verbose --log-level DEBUG
```

Produces detailed logs in `output/logs/hotfix_YYYYMMDD_HHMMSS.log`.

---

## Summary

The hotfix orchestration system provides a centralized, auditable way to deploy SQL Server cumulative updates across an enterprise. It integrates with the audit workflow, logs to SQLite, and supports safe, resumable deployments.

**Current Implementation Status**: 🔄 Design complete; code stubs exist; full execution logic pending (Phase 5).

---

*Last updated: 2025-12-06*
