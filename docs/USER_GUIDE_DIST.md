# AutoDBAudit - User Guide

**Version**: 2.1  
**Updated**: December 2024  
**Role**: Complete handbook for running audits, syncing progress, managing exceptions, and delivering final reports.

---

## 🚀 Quick Start

### 1. Setup
1. Unzip the distribution package to a folder (e.g., `C:\AutoDBAudit\`).
2. Edit `config/sql_targets.json` with your SQL Server targets.
3. Copy `config/audit_config.example.json` → `config/audit_config.json` and customize.
4. Open PowerShell (Administrator recommended for OS remediation).

### 2. Run Initial Audit
```powershell
.\AutoDBAudit.exe audit
```
**Output**: 
- `output/<OrgName>_SQL_Audit_<Date>.xlsx` - Interactive Excel report
- `output/audit_history.db` - SQLite database (source of truth)

### 3. Review & Document
1. Open the Excel report
2. Review each sheet for security findings
3. For exceptions, fill in:
   - **Review Status**: Select "Exception ✓" 
   - **Justification**: Explain why this is acceptable
   - **Notes**: Additional context

### 4. Sync Progress
```powershell
.\AutoDBAudit.exe sync --audit-id <ID>
```
This re-scans servers, compares against baseline, and updates the Excel with:
- ✅ Fixed items (moved to Actions sheet)
- ⚠️ Regressions (new FAILs)
- 📋 Exception status preserved

### 5. Finalize Audit
```powershell
.\AutoDBAudit.exe finalize --audit-id <ID>
```
Locks the audit and commits all annotations to permanent history.

---

## 📖 CLI Reference

### Core Commands

| Command | Description |
|---------|-------------|
| `audit` | Run full security scan on all configured targets |
| `sync --audit-id <ID>` | Re-scan and diff against baseline |
| `finalize --audit-id <ID>` | Lock audit and commit annotations |
| `definalize --audit-id <ID>` | Unlock a finalized audit for more edits |
| `status` | Show current audit status dashboard |

### Remediation Commands

| Command | Description |
|---------|-------------|
| `remediate --generate` | Generate T-SQL fix scripts |
| `remediate --apply --dry-run` | Preview what would change |
| `remediate --apply` | Execute remediation scripts |
| `remediate --rollback` | Undo last remediation batch |

### Utility Commands

| Command | Description |
|---------|-------------|
| `check-drivers` | Verify ODBC driver installation |
| `test-connection` | Test connectivity to targets |
| `--version` | Show tool version |
| `--help` | Show all available commands |

---

## 📊 Excel Report Sheets

| # | Sheet | Purpose | Key Columns |
|---|-------|---------|-------------|
| 1 | Cover | Summary with pass/fail/warn counts | Stats, Legend |
| 2 | Instances | SQL Server inventory | Version, Build, Status |
| 3 | SA Account | SA account security status | Enabled, NeedsAction |
| 4 | Server Logins | Login audit | Type, Disabled, Policy |
| 5 | Sensitive Roles | sysadmin/securityadmin members | Role, Risk Level |
| 6 | Configuration | sp_configure settings | Setting, Value, Risk |
| 7 | Services | SQL Server services | Account, StartMode |
| 8 | Client Protocols | Network protocol status | Enabled, Compliance |
| 9 | Databases | Database properties | Owner, Recovery, Trustworthy |
| 10 | Database Users | Per-database users | Type, DefaultSchema |
| 11 | Database Roles | Role memberships | Principal, Role, db_owner |
| 12 | Role Matrix | Visual matrix of permissions | Principal × Role grid |
| 13 | Permission Grants | Explicit GRANT/DENY | Scope, Permission, State |
| 14 | Orphaned Users | Users without logins | Database, UserName |
| 15 | Linked Servers | Linked server config | Provider, Security |
| 16 | Triggers | Server/database triggers | Type, Enabled |
| 17 | Backups | Backup status (Full/Diff/Log) | LastBackup, AgeDays |
| 18 | Audit Settings | Audit configuration | Enabled, Destination |
| 19 | Encryption | SMK/DMK/TDE status | KeyType, Algorithm |
| 20 | Actions | Remediation changelog | Change Type, Risk, Date |

---

## 🔧 Column Legend

### Status Columns
- **Review Status**: `✓ Reviewed` | `Exception ✓` | `⏳ Needs Review` | `✗ Rejected`
- **Justification**: Free text explaining why an exception is acceptable
- **Notes**: Additional context or documentation
- **Last Reviewed**: Date when row was last reviewed

### Action Indicator
- **⏳** = Needs attention / action required
- **—** = No action needed

### Risk Levels
- 🟢 **Low** = Informational
- 🟡 **Medium** = Should review
- 🔴 **High** = Requires action

---

## 🔄 Sync Workflow Detail

The `sync` command is the core of ongoing audit management:

1. **Re-scan**: Connects to all targets and collects fresh data
2. **Compare**: Diffs against the baseline (initial audit)
3. **Detect Changes**:
   - **Fixed**: FAIL → PASS (logged to Actions sheet)
   - **Regression**: PASS → FAIL (flagged as critical)
   - **New Issue**: Didn't exist before, now FAIL
   - **Exception Documented**: User added justification
   - **Exception Removed**: User cleared justification
4. **Preserve Annotations**: All Notes/Justifications are preserved
5. **Update Excel**: Regenerates report with current state

### CLI Stats Output
After sync, you'll see per-sheet breakdown:
```
📋 By Sheet:
  📋 Backups: 2 ⚠ active, 1 ✓ exc
  📋 SA Account: 1 ✓ fixed
  📋 Configuration: 3 ⚠ active, 2 ✓ ok
```

---

## ⚙️ Configuration Files

### sql_targets.json
```json
{
  "targets": [
    {
      "id": "prod-sql-01",
      "display_name": "Production DB Server",
      "server": "prod-sql-01.company.com",
      "port": 1433,
      "auth": "windows"
    },
    {
      "id": "dev-sql",
      "server": "localhost",
      "auth": "sql",
      "username": "audit_user",
      "password": "encrypted_password_here"
    }
  ]
}
```

### audit_config.json
```json
{
  "organization": "Your Company",
  "audit_year": 2025,
  "requirements": {
    "minimum_sql_version": "2019",
    "expected_builds": {
      "2025": "17.0.1000.7",
      "2022": "16.0.4165.4",
      "2019": "15.0.4415.2"
    }
  }
}
```

---

## ❓ Troubleshooting

| Issue | Solution |
|-------|----------|
| "Driver not found" | Install "ODBC Driver 17 for SQL Server" |
| "Login Failed" | Check credentials in sql_targets.json |
| "File Locked" | Close Excel before running sync/finalize |
| "Audit not found" | Run `status` to see available audit IDs |
| "Cannot connect" | Run `test-connection` to diagnose |

---

## 🇮🇷 Persian/RTL Reports

AutoDBAudit can generate Persian Excel reports alongside English ones.

### Generate Persian Report
```powershell
.\AutoDBAudit.exe finalize --audit-id <ID> --persian
```

**Output**:
- `AuditReport.xlsx` (English)
- `AuditReport_fa.xlsx` (Persian/RTL)

### Font Installation
For proper display, install the included Persian fonts:
1. Open `fonts/` folder in the Field Kit
2. Right-click each `.ttf` file → "Install for all users"
3. Restart Excel

**Included Fonts**:
- `IRTitr.ttf` - Headings
- `IRNazanin.ttf` - Content

### What Gets Translated
- Sheet names, column headers
- Dropdown values, status indicators
- Cover page text, section headers

### What Stays English
- Your notes and justifications
- Server names, technical values
- Database names, config values

---

## 🏗️ Building from Source

### Prerequisites
- Python 3.11+
- PyInstaller
- PowerShell 5.1+

### Build Steps
```powershell
# 1. Setup environment
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller

# 2. Run build script
cd packaging
.\build.ps1

# 3. Output
# dist/AutoDBAudit_FieldKit/  - Ready to deploy folder
# dist/AutoDBAudit_FieldKit_vX.X.zip - Distribution archive
```

### What Gets Bundled
- `AutoDBAudit.exe` - Main executable
- `config/` - Configuration templates
- `resources/` - Query templates
- `UserGuide.md` - This guide
- All required Python packages

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.1 | Dec 2024 | Persian/RTL dual-language reports, PSRemote pywinrm, i18n |
| 2.0 | Dec 2024 | New CLI structure, sync engine, exception tracking |
| 1.2 | Nov 2024 | Added remediation scripts |
| 1.0 | Oct 2024 | Initial release |

---

*For technical documentation, see the `docs/` folder in the source distribution.*
