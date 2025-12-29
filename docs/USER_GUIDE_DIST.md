# AutoDBAudit - Field User Guide

## Introduction
AutoDBAudit is a portable, offline-capable SQL Server security auditing tool. It audits configuration, access, and security policies against industry standards.

## Quick Start
1.  **Configure**:
    *   Navigate to the `config` folder.
    *   Run `setup_config.bat` to generate `.json` files from `.jsonc` templates.
    *   Edit `sql_targets.json` to add your target servers.
    *   Edit `credentials.json` if using SQL authentication aliases.

2.  **Audit**:
    *   Open `AutoDBAudit.exe` (or use `Startup.bat`).
    *   Run a new audit: `autodbaudit audit --new --name "Q3 Audit"`
    *   Review the Excel report in `output/` folder.

3.  **Remediate**:
    *   Generate Fixes: `autodbaudit remediate --generate`
    *   Review Scripts: Check `output/audit_.../remediation/`
    *   Apply Fixes: `autodbaudit remediate --apply`

4.  **Sync**:
    *   After manual changes or remediation, update the report:
    *   `autodbaudit sync`

## Directory Structure
*   `AutoDBAudit.exe`: Main application.
*   `config/`: Configuration files.
*   `output/`: Audit reports, logs, and databases.
*   `resources/`: Support files.
*   `scripts/`: PowerShell helper scripts.
*   `tools/`: Portable utilities (Terminal, Editor).

## Troubleshooting
*   **Connection Failed**: Check `sql_targets.json`, firewall, and ensure `TargetServer` IPs are reachable.
*   **License/Access**: Ensure the account running the tool has `VIEW SERVER STATE` and `VIEW ANY DEFINITION` on targets.

---
*For support contact: Security Team*
