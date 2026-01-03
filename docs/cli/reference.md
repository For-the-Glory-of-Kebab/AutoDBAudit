# CLI Command Reference

**Scope**: This document details every command available in the **AutoDBAudit** CLI, including **Functional Expectations**, **Resiliency Mechanisms**, and **Error Handling**.

**Source Code**: `src/autodbaudit/interface/cli.py`

## CLI Behavior Standards

### Help Display

- **Automatic Help**: Commands invoked without required parameters show an error with guidance to use `--help`
- **Help Synonyms**: `--help` displays help information (implementation note: `-h` may not be available in all contexts)
- **Contextual Help**: Each command level provides relevant help for its specific functionality

### Command Invocation

- **Required Parameters**: Commands without required arguments show help automatically
- **Optional Parameters**: Commands with optional parameters execute with defaults when help is not requested
- **Error Handling**: Invalid parameters show usage information alongside error messages

---

## Global Arguments

- `--verbose`, `-v`: Enable verbose (DEBUG) logging. **Use this for troubleshooting.**
- `--log-file [PATH]`: Write logs to a specific file. Useful for automated cron jobs.

---

## 1. `audit`
**Purpose**: Run a security audit scan against SQL targets.

| Argument | Type | Description |
| :--- | :--- | :--- |
| `--new` | Flag | Start a fresh audit cycle (creates new Audit ID). |
| `--name [NAME]` | String | Name for the new audit (used with `--new`). |
| `--id [ID]` | Int | Resume an existing audit by ID. |
| `--targets [FILE]` | String | Target list JSON (default: `sql_targets.json`). |
| `--organization [NAME]` | String | Organization name for the report cover. |
| `--list` | Flag | List all existing audits and their status. |

### Functional Expectations
*   **Parallelism**: Utilizes a Thread Pool to scan targets concurrently. Scope: Server-Isolated.
*   **Output**:
    1.  **SQLite**: Stores raw JSON results in `audit_history.db`.
    2.  **Excel**: Generates `output/Audit_Latest.xlsx` (unless skipped).
*   **Timeouts**: Default SQL connection timeout is **30 seconds**. If a server hangs, the thread will abort but **other servers continue**.

### Reporting & Statistics (Console Output)
The CLI must produce a **Meaningful, Readable** summary at the end of every run.
1.  **Global Stats**:
    *   **Baseline Diff**: Changes vs Run ID 1 (Fixed/Regression/New).
    *   **Sync Diff**: Changes vs *Previous* Run (What changed *just now*?).
2.  **Per-Sheet Breakdown**:
    *   A visual table showing the health of each sheet (Instances, Logins, Config, etc.).
    *   Columns: `Active Issues (FAIL)`, `Exceptions (Waived)`, `Regressions`, `New Findings`.
    *   *Goal*: Immediate visual identification of problem areas (e.g., "Why does the 'Config' sheet have 50 regressions?").

### Resiliency & Error Handling
*   **Partial Failure**: If 5/10 servers are reachable, the audit **succeeds** with partial data. Unreachable servers are logged as `SKIPPED` in the database.
*   **Excel Lock**: If `Audit_Latest.xlsx` is open, the CLI will **abort immediately** with a clear error message. It determines this *before* running the scan to save time.
*   **Crash Recovery**: All results are written to SQLite transactionally. If the CLI crashes, the data for completed servers is saved. You can resume with `--id [ID]`.

---

## 2. `sync`
**Purpose**: The "Heartbeat". Synchronizes User Inputs (Excel) with Live Reality (SQL).

| Argument | Type | Description |
| :--- | :--- | :--- |
| `--audit-id [ID]` | Int | The Audit ID to sync (defaults to latest in-progress). |
| `--targets [FILE]` | String | Target list JSON (default: `sql_targets.json`). |

### Functional Expectations
1.  **Ingest**: Reads `Audit_Latest.xlsx`. Parses *Justifications*, *Notes*, *Review Status*. Map by UUID.
2.  **Re-Verify**: Runs a **Fresh Audit** (same logic as `audit` command).
3.  **Diff**: Compares [Fresh Audit] vs [Last Snapshot].
4.  **Log**: Writes "Fixed", "Regression", "Exception" events to the Action Log.
5.  **Regenerate**: Overwrites `Audit_Latest.xlsx` with merged data.

### Statistics Requirements
Identical to `audit`, but with a focus on **User Actions**:
*   "You added X notes."
*   "Y issues were auto-fixed."
*   "Z issues regressed."
*   **Visual Diff**: A clear summary of what changed in the *Action Log* explicitly.

### Resiliency & Error Handling
*   **Excel Lock**: **Critical Block**. If Excel is open, `sync` **must fail fast**.
*   **Data Preservation**: User inputs from Excel are saved to DB *before* any scan happens. If the scan hangs or crashes, your notes are safe.
*   **Missing UUIDs**: If rows were deleted manually in Excel, the sync handles this gracefully (logs a warning, doesn't crash).
*   **Network Flaps**: If a server was present in Baseline but effectively vanishes (network error), it is **NOT** marked as "Fixed". It is marked as `UNREACHABLE` to unnecessary false positive fixes.

---

## 3. `remediate`
**Purpose**: Generate or apply remediation scripts.

| Argument | Type | Description |
| :--- | :--- | :--- |
| `--generate` | Flag | Generate scripts based on current findings. |
| `--apply` | Flag | Execute generated scripts against targets. |
| `--aggressiveness [1-3]` | Int | Fix intensity (1=Safe, 2=Std, 3=Nuclear). Default: 1. |
| `--audit-id [ID]` | Int | Specific audit context. |
| `--scripts [PATH]` | String | Folder containing scripts to apply (for `--apply`). |
| `--dry-run` | Flag | Simulate actions without executing. |
| `--rollback` | Flag | Execute rollback scripts (folder mode only). |
| `--parallel` | Flag | Execute `apply` in parallel across servers (Default: True). |

### Functional Expectations
*   **CLI Application**: The CLI can *execute* the scripts it generates (`--apply`). It handles the connection logic, parallelism, and output logging.
*   **Reversion**: The CLI can *revert* changes utilizing the `--rollback` flag and the generated rollback scripts.
*   **Idempotency**: Scripts check state before running (`IF EXISTS ...`).
*   **Exception Awareness**: Checks the `annotations` table. If a finding has a valid justification, it is **EXCLUDED** from remediation scripts automatically.
*   **Hybrid Execution**:
    *   **T-SQL**: Executed via ODBC.
    *   **PowerShell**: Executed via `Invoke-Command` (PSRemote).

### Safety Mechanisms
*   **Aggressiveness Levels**:
    *   **1 (Safe)**: Only generates comments (`-- EXEC sp_configure...`). Zero risk.
    *   **2 (Standard)**: Enables low-risk fixes (e.g., Guest User). Comments out high risk.
    *   **3 (Active)**: Enables all modifications.
*   **Rollback**: Every `apply` run generates a corresponding rollback script where possible.

---

## 4. `finalize`
**Purpose**: Mark an audit as "Complete" and lock it.

| Argument | Type | Description |
| :--- | :--- | :--- |
| `--audit-id [ID]` | Int | The Audit ID. |
| `--baseline-run [ID]` | Int | Specific run ID to finalize (defaults to latest). |
| `--force` | Flag | Bypass checking for outstanding Fails. |
| `--status` | Flag | Check readiness only. |
| `--apply-exceptions` | Flag | Apply Excel exceptions before finalizing. |
| `--excel [FILE]` | String | Excel file for exceptions. |
| `--persian` | Flag | Use Persian calendar for dates. |

### Expectations

* **Immutable**: Once finalized, an audit cannot be synced or remediated.
* **Final Output**: Generates a timestamped `Final_Report_YYYYMMDD.xlsx` containing the definitive state.
* **Closure**: Prints a final summary of compliance and outstanding risks.

---

## 4b. `definalize`
**Purpose**: Revert a finalized audit back to in-progress state.

| Argument | Type | Description |
| :--- | :--- | :--- |
| `--audit-id [ID]` | Int | The Audit ID to revert (required). |

### Definalize Expectations

* **Reversible**: Allows modification of previously finalized audits.
* **State Reset**: Changes audit status from "finalized" back to "in_progress".
* **Data Preservation**: All historical data and runs are preserved.
* **Re-sync Capability**: Allows running sync and remediation again.

---

## 5. `prepare`
**Purpose**: Manage remote access (PSRemote/WMI) for targets. **Prerequisite for full audits.**

**Status**: Implemented with server consolidation, 5-layer PS remoting with automated setup + manual fallbacks, and revert support.

| Subcommand | Purpose | Arguments |
| :--- | :--- | :--- |
| `apply` | Apply PS remoting setup to targets | Optional `--targets`, `--config`, `--credentials`, `--parallel`, `--timeout`, `--dry-run` |
| `revert` | Revert PS remoting changes | Optional `--targets`, `--config`, `--credentials`, `--parallel`, `--timeout`, `--dry-run`, `--force` |
| `status` | Show recorded connection status for all servers | `--format` (table/json), `--filter` (successful/failed/all) |

### `prepare apply` - Apply PS Remoting Setup

**Default Behavior**: When no arguments provided, applies PS remoting setup to ALL enabled targets from `sql_targets.json`.

| Argument | Type | Description |
| :--- | :--- | :--- |
| `--targets` | Optional[List[str]] | Specific target server names. **If omitted, uses all enabled targets** |
| `--config` | String | Path to audit configuration file (default: `audit_config.json`) |
| `--credentials` | String | Path to credentials file (default: uses `os_credential_file` from each target) |
| `--parallel/--sequential` | Flag | Process servers in parallel (default: parallel) |
| `--timeout` | Int | Timeout in seconds per server (default: 300) |
| `--dry-run` | Flag | Show what would be done without executing |

**Server Consolidation**: Multiple SQL instances on same server = 1 PS remoting operation.

**Behavior**: Uses the 5-layer strategy in `PSRemotingConnectionManager` (direct attempts → client config → target config → fallbacks → manual override). Successful profiles are persisted to `psremoting_profiles`; manual scripts and troubleshooting reports are emitted when automated setup fails.

**Localhost**: When target is localhost/127.0.0.1, the CLI enables WinRM/firewall/registry settings locally before attempting remoting for easy dev verification.

**Examples**:

```bash
# Apply to all enabled targets (default behavior)
autodbaudit prepare apply

# Apply to specific servers only
autodbaudit prepare apply --targets sql-prod-01 sql-prod-02

# Dry run to see what would happen
autodbaudit prepare apply --dry-run
```

### `prepare revert` - Revert PS Remoting Changes

**Default Behavior**: When no arguments provided, reverts PS remoting setup on ALL enabled targets.

| Argument | Type | Description |
| :--- | :--- | :--- |
| `--targets` | Optional[List[str]] | Specific target server names. **If omitted, uses all enabled targets** |
| `--config` | String | Path to audit configuration file |
| `--credentials` | String | Path to credentials file |
| `--parallel/--sequential` | Flag | Process servers in parallel (default: parallel) |
| `--timeout` | Int | Timeout in seconds per server (default: 300) |
| `--dry-run` | Flag | Show what would be reverted without executing |
| `--force` | Flag | Skip confirmation prompts |

**Behavior**: Generates and executes revert scripts that stop/disable WinRM, remove WinRM firewall rules, and clean TrustedHosts entries for each server. Dry-run returns the scripts without executing.

**Examples**:

```bash
# Revert all enabled targets
autodbaudit prepare revert

# Revert specific servers
autodbaudit prepare revert --targets sql-dev-01

# Force revert without confirmation
autodbaudit prepare revert --force
```

### `prepare status` - Show Connection Status Report

**Purpose**: Display the recorded PS remoting connection status and availability for all servers.

| Argument | Type | Description |
| :--- | :--- | :--- |
| `--format` | String | Output format: `table` (default), `json`, `csv` |
| `--filter` | String | Filter results: `all` (default), `successful`, `failed`, `manual` |

**Displays**:

- Server hostname/IP
- Connection method used (PowerShell Remoting, SSH, WMI, etc.)
- Authentication method (Kerberos, NTLM, Negotiate, etc.)
- Last successful connection timestamp
- Associated SQL targets on that server
- Status (Successful, Failed, Manual Override Required)

**Examples**:

```bash
# Show all server statuses in table format
autodbaudit prepare status

# Show only failed connections in JSON format
autodbaudit prepare status --filter failed --format json
```

---

## 6. `util`

**Purpose**: Tooling and Setup.

- `--check-drivers`: Verification of ODBC Driver 17/18 for SQL Server.
- `--validate-config`: Syntax check for `sql_targets.json`.
- `--setup-credentials`: Interactive prompt to encrypt credentials into `secrets.json`.

