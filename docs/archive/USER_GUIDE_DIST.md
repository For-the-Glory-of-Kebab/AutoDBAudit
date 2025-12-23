# AutoDBAudit - User Guide

**AutoDBAudit** is a self-contained SQL Server security audit tool. 

## Getting Started

1.  Unzip `AutoDBAudit_FieldKit_v1.0.0.zip`.
2.  Open the folder.
3.  (Optional) Edit configuration files in the `config/` folder.

## How to Run

Open a Command Prompt or PowerShell in this directory.

### Basic Connectivity Check
Verify you can run the tool and see its version:

```powershell
.\AutoDBAudit.exe --version
```

### 1. Configure Targets
Edit `config/sql_targets.json` to list the SQL Server instances you want to audit.

### 2. Run an Audit
To audit a specific server by name (as defined in `sql_targets.json`):

```powershell
.\AutoDBAudit.exe --audit --name "ProdDB"
```

To audit **all enabled targets**:

```powershell
.\AutoDBAudit.exe --audit
```

### 3. View Results
Results are saved to the `output/` folder (created automatically if it doesn't exist).

---

## Common Commands

| Action | Command |
| :--- | :--- |
| **Check Connectivity** | `.\AutoDBAudit.exe --audit --dry-run` |
| **List Drivers** | `.\AutoDBAudit.exe --check-drivers` |
| **Sync/Remediate** | `.\AutoDBAudit.exe --sync --target "ProdDB"` |
| **Help** | `.\AutoDBAudit.exe --help` |

## Troubleshooting

- **"Driver not found"**: Please install the ODBC driver located in `tools/odbc_driver_install/` (if provided) or download the "ODBC Driver 17 for SQL Server".
- **Permission Errors**: Ensure you are running the terminal as Administrator if you need to access system resources or if UAC is blocking execution.

## Advanced Configuration

For detailed security settings, edit `config/audit_config.json`.
For off-line PowerShell scripts modules, check `resources/powershell`.
