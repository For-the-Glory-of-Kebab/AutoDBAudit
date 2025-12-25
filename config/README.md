# Configuration Files

This directory contains configuration files for AutoDBAudit.

## File Types

| Extension | Purpose |
|-----------|---------|
| `.json` | Production config (gitignored) |
| `.jsonc` | Examples with inline comments |
| `.example.json` | Legacy examples (plain JSON) |

## Getting Started

1. Copy one of the example files:
   ```powershell
   Copy-Item audit_config.example.jsonc audit_config.json
   Copy-Item sql_targets.example.jsonc sql_targets.json
   ```

2. Edit the copied files to match your environment

3. For SQL Authentication, create a credentials file:
   ```powershell
   # Create credentials directory (gitignored)
   New-Item -ItemType Directory -Path credentials -Force
   Copy-Item credentials.example.jsonc credentials/prod.json
   ```

## Configuration Files

### audit_config.json

Main audit configuration:
- Organization name and audit date
- Security requirements (min SQL version, expected builds)
- Output file settings
- Remediation script options

### sql_targets.json

Target servers to audit:
- Connection details (server, instance, port)
- Authentication method (integrated/sql)
- Credential file references
- Tags for filtering

### credentials/*.json

Sensitive credentials (gitignored):
- SQL Authentication username/password
- OS credentials for WMI/PowerShell remoting

## Security Notes

> ⚠️ **Never commit real credentials to git!**

Files with actual credentials are gitignored:
- `audit_config.json`
- `sql_targets.json`
- `credentials/*.json`

Only example files (`.example.*`) are tracked in git.
