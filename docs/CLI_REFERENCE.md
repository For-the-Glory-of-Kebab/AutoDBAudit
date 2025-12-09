# CLI Command Reference

> **Purpose**: Complete reference for all AutoDBAudit commands.

---

## Quick Reference

```bash
# Audit lifecycle
python main.py --audit                    # Initial audit
python main.py --generate-remediation     # Create smart TSQL scripts
python main.py --apply-remediation --dry-run  # Preview execution
python main.py --apply-remediation        # Execute scripts
python main.py --status                   # Dashboard
python main.py --sync                     # Track progress
python main.py --finalize                 # Persist to DB

# Utilities
python main.py --check-drivers            # List ODBC drivers
python main.py --validate-config          # Validate configs
python main.py --help                     # Show all options
```

---

## Commands

### `--audit`

Run security audit on SQL Server instances.

```bash
python main.py --audit [options]
```

| Option | Description |
|--------|-------------|
| `--targets FILE` | Target instances (default: sql_targets.json) |
| `--config FILE` | Audit config (default: audit_config.json) |
| `--organization` | Organization name for report |
| `--verbose` | Enable debug logging |

**Output**:
- `output/sql_audit_YYYYMMDD_HHMMSS.xlsx`
- `output/audit_history.db`

---

### `--generate-remediation`

Generate smart TSQL remediation scripts with 4 categories.

```bash
python main.py --generate-remediation
```

**Output**: `output/remediation_scripts/<server>_<instance>.sql`
**Also generates**: `<server>_<instance>_ROLLBACK.sql`

**Script Categories**:
| Category | Action | Examples |
|----------|--------|----------|
| AUTO-FIX | Executes | xp_cmdshell disable, orphan drop |
| CAUTION | Executes + logs | SA disable with password |
| REVIEW | Commented | High-privilege logins |
| INFO | Instructions | Backups, version upgrade |

---

### `--apply-remediation`

Execute remediation scripts against SQL Server.

```bash
python main.py --apply-remediation [options]
```

| Option | Description |
|--------|-------------|
| `--scripts PATH` | Folder or .sql file (default: output/remediation_scripts) |
| `--dry-run` | Preview what would execute |
| `--rollback` | Execute _ROLLBACK.sql scripts instead |

**Examples**:
```bash
# Dry run (preview only)
python main.py --apply-remediation --dry-run

# Execute all scripts
python main.py --apply-remediation

# Execute single script
python main.py --apply-remediation --scripts output/remediation_scripts/localhost_INTHEEND.sql

# Rollback
python main.py --apply-remediation --rollback
```

**Safety Features**:
- GO batch isolation (failures don't abort script)
- Credential protection (skips batches modifying connection login)
- Extensive logging for each batch

> ⚠️ **SA Protection**: If connecting as SA, SA remediation batches are SKIPPED.
> Use a different sysadmin account to apply SA changes.

---

### `--status`

Show audit dashboard with summary.

```bash
python main.py --status
```

**Output**:
- Latest run info
- Data counts (logins, databases, findings)
- Findings by status/type
- Action log summary

---

### `--sync`

Sync progress and log actions.

```bash
python main.py --sync [options]
```

| Option | Description |
|--------|-------------|
| `--targets FILE` | Target instances |

**What it does**:
1. Re-audits current state
2. Diffs against initial baseline
3. Logs fixed items with real timestamps
4. Marks potential exceptions

---

### `--finalize`

Finalize audit and persist everything.

```bash
python main.py --finalize [options]
```

| Option | Description |
|--------|-------------|
| `--excel FILE` | Excel with annotations |
| `--baseline-run N` | Baseline run ID (default: first) |

**What it does**:
1. Reads Notes/Reasons from Excel
2. Persists annotations to SQLite
3. Marks run as finalized

---

### `--apply-exceptions`

Read annotations from Excel (standalone).

```bash
python main.py --apply-exceptions --excel FILE
```

**Persists**: Notes, Reasons, Status Overrides → SQLite annotations table

---

### `--check-drivers`

List available ODBC drivers.

```bash
python main.py --check-drivers
```

---

### `--validate-config`

Validate configuration files.

```bash
python main.py --validate-config
```

---

## Configuration Files

### sql_targets.json

```json
{
  "targets": [
    {
      "name": "Production",
      "host": "prod-sql01",
      "instance": "MSSQLSERVER",
      "port": 1433,
      "windows_auth": true,
      "enabled": true
    },
    {
      "name": "Dev",
      "host": "dev-sql",
      "instance": "",
      "windows_auth": false,
      "username": "audit_user",
      "password": "secret",
      "enabled": true
    }
  ]
}
```

### audit_settings.json

```json
{
  "security_settings": {
    "xp_cmdshell": {"required": 0, "risk": "critical"},
    "clr enabled": {"required": 0, "risk": "high"}
  },
  "backup_requirements": {
    "max_days_without_full_backup": 7
  }
}
```

---

## Typical Workflow

```bash
# Set up environment
$env:PYTHONPATH="d:\Raja-Initiative\src"

# 1. Run initial audit
python main.py --audit

# 2. Generate remediation scripts
python main.py --generate-remediation

# 3. Preview changes
python main.py --apply-remediation --dry-run

# 4. Execute remediation
python main.py --apply-remediation

# 5. Check status
python main.py --status

# 6. If needed, rollback
python main.py --apply-remediation --rollback

# 7. Finalize
python main.py --finalize --excel output/sql_audit_edited.xlsx
```

---

*Document Version: 2.0 | Last Updated: 2025-12-09*
