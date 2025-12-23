# AutoDBAudit - User Guide

**Version**: 1.2
**Role**: Complete Handbook for running audits, remediating issues, and syncing progress.

## 🚀 Quick Start

### 1. Setup
1. Unzip the distribution package.
2. Edit `config/sql_targets.json` to list your SQL Server targets.
3. Open PowerShell as Administrator.

### 2. Run Audit
```powershell
.\AutoDBAudit.exe --audit
```
*Output*: `output/<AuditName>_Latest.xlsx`

### 3. Generate Fixes
```powershell
.\AutoDBAudit.exe --generate-remediation
```
*Output*: `output/remediation/v<NN>/` (SQL scripts)

### 4. Apply Remediation
Run the generated SQL scripts in SSMS or via CLI (limited support).

### 5. Sync Progress
```powershell
.\AutoDBAudit.exe --sync
```
*Output*: Updates Excel "Actions" sheet with fixed items.

---

## 📖 Detailed Workflow

### Phase 1: The Audit (`--audit`)
The audit phase connects to all targets, runs 20+ checks per server, and produces:
1.  **Baseline Database** (`audit_history.db`): The source of truth.
2.  **Excel Report**: Human-readable interactive report.

### Phase 2: Remediation (`--generate-remediation`)
AutoDBAudit analyzes the baseline findings and generates tailored T-SQL scripts.
*   **Safe**: Destructive commands are commented out.
*   **Context**: Scripts explain *why* a setting is being changed.
*   **Manual Steps**: Things like OS patches or backup configurations are listed as comments.

### Phase 3: Synchronization (`--sync`)
This is the "Magic" phase.
1.  Runs a fresh audit.
2.  Compares against the **Initial Baseline**.
3.  Detects:
    *   **Fixed Issues**: Logs them to the "Actions" sheet.
    *   **New Issues** (Regressions): Flags as FAIL.
    *   **Exceptions**: Persistent FAILs needing justification.

### Phase 4: Finalization (`--finalize`)
When the engagement is over:
1.  Fill out "Notes" and "Reasons" in the Excel file.
2.  Run `--finalize`.
3.  The system permanently records the final state and all justifications into the database history.

---

## 🔧 CLI Reference

| Command | Description |
| :--- | :--- |
| `--audit` | Run full security scan on targets. |
| `--sync` | Re-scan and diff against baseline. |
| `--generate-remediation` | Create T-SQL fix scripts. |
| `--finalize` | Commit Excel annotations to history. |
| `--check-drivers` | Verify ODBC driver installation. |
| `--version` | Show tool version. |
| `--dry-run` | Test connectivity without scanning. |

See `CLI.md` for advanced argument usage.

## ❓ Troubleshooting

*   **"Driver not found"**: Install "ODBC Driver 17 for SQL Server".
*   **"Login Failed"**: Check `sql_targets.json` credentials or Windows Auth permissions.
*   **"File Locked"**: Close the Excel report before running `--sync` or `--finalize`.
