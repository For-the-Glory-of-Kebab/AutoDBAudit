# CLI Command Reference

**Scope**: This document details every command available in the **AutoDBAudit** CLI, including **Functional Expectations**, **Resiliency Mechanisms**, and **Error Handling**.

**Source Code**: `src/autodbaudit/interface/cli.py`

## Global Arguments
*   `--verbose`, `-v`: Enable verbose (DEBUG) logging. **Use this for troubleshooting.**
*   `--log-file [PATH]`: Write logs to a specific file. Useful for automated cron jobs.

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

**Status**: Currently **BROKEN** - See `docs/sync/prepare.md` for detailed analysis of issues and required fixes.

| Argument | Type | Description |
| :--- | :--- | :--- |
| `--status` | Flag | Show current access status for all targets. |
| `--revert` | Flag | Revert changes (disconnect/cleanup). |
| `--mark-accessible [ID]` | String | Manually mark a target as accessible. |
| `--targets [FILE]` | String | Target config file (default: `sql_targets.json`). |
| `--yes` | Flag | Skip confirmation prompts. |

### The "Trusted Host" & Credential Requirement

**Critical Failure Mode**: When targets are specified by **IP Address** (not hostname/FQDN), Windows defaults to blocking authentication (Kerberos failure).

**Robust Strategy**:

1. **TrustedHosts Update**: The tool must configure `WSMan:\localhost\Client\TrustedHosts`.
   * *Command*: `Set-Item WSMan:\localhost\Client\TrustedHosts -Value '{IP_ADDRESS_LIST}' -Concatenate`
   * *Scope*: Client-side (the machine running the audit).
2. **Explicit Credentials**:
   * When using IP addresses, `Invoke-Command` cannot infer credentials from the current session context reliably.
   * *Requirement*: The CLI must accept `--credentials` (encrypted in `secrets.json`) and pass a generic `PSCredential` object explicitly to the remoting call.
3. **Multi-Layered Connection Attempt**:
   * **Layer 1 (Standard)**: Attempt `Invoke-Command -ComputerName [Target]`. (Works for Domain/FQDN).
   * **Layer 2 (IP Fallback)**: If Layer 1 fails and target is an IP:
     * Prompt user (or Auto-Fix) to add IP to `TrustedHosts`.
     * Retry with `-Credential` object explicitly.

### Requirements

* **WMI/RPC**: Checks connectivity logic used by the audit collectors.
* **Agentless**: Does *not* install software. Uses standard Windows protocols.

---

## 6. `util`

**Purpose**: Tooling and Setup.

* `--check-drivers`: Verification of ODBC Driver 17/18 for SQL Server.
* `--validate-config`: Syntax check for `sql_targets.json`.
* `--setup-credentials`: Interactive prompt to encrypt credentials into `secrets.json`.

