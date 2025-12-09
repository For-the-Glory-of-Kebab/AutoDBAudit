# CLI Command Reference

> **Purpose**: Complete reference for all AutoDBAudit commands.

---

## Quick Reference

```bash
# Audit lifecycle
python main.py --audit                    # Initial audit
python main.py --generate-remediation     # Create TSQL scripts
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
| `--incremental` | Append to existing report |
| `--output DIR` | Output directory (default: output/) |
| `--verbose` | Enable debug logging |

**Output**:
- `output/sql_audit_YYYYMMDD_HHMMSS.xlsx`
- `output/audit_history.db`

---

### `--generate-remediation`

Generate TSQL remediation scripts.

```bash
python main.py --generate-remediation
```

**Reads from**: SQLite findings table
**Output**: `output/remediation_scripts/remediate_<server>_<instance>.sql`

Scripts contain:
- Commented-out TSQL fixes
- Manual intervention notes
- Entity keys for tracking

---

### `--sync`

Sync progress and log actions.

```bash
python main.py --sync [options]
```

| Option | Description |
|--------|-------------|
| `--targets FILE` | Target instances |
| `--excel FILE` | Excel to update with action log |

**What it does**:
1. Re-audits current state
2. Diffs against initial baseline
3. Logs fixed items with real timestamps
4. Marks potential exceptions
5. Updates Excel action sheet

---

### `--finalize`

Finalize audit and persist everything.

```bash
python main.py --finalize [options]
```

| Option | Description |
|--------|-------------|
| `--excel FILE` | Excel with annotations (required) |
| `--baseline-run N` | Baseline run ID (default: first) |

**What it does**:
1. Reads Notes/Reasons from Excel
2. Runs final audit snapshot
3. Persists all data to SQLite
4. Marks run as finalized

---

### `--apply-exceptions`

Read annotations from Excel (standalone).

```bash
python main.py --apply-exceptions [options]
```

| Option | Description |
|--------|-------------|
| `--excel FILE` | Excel file (default: latest) |

**Persists**: Notes, Reasons, Status Overrides → SQLite annotations table

---

### `--check-drivers`

List available ODBC drivers.

```bash
python main.py --check-drivers
```

**Output**: List of installed SQL Server ODBC drivers.

---

### `--validate-config`

Validate configuration files.

```bash
python main.py --validate-config
```

**Checks**:
- sql_targets.json syntax
- config/security_settings.json
- Credential encryption

---

## Configuration Files

### sql_targets.json

```json
{
  "targets": [
    {
      "server": "localhost",
      "instance": "SQLEXPRESS",
      "auth": "windows"
    },
    {
      "server": "prod-sql01",
      "instance": "MSSQLSERVER",
      "auth": "sql",
      "username": "audit_user",
      "password_encrypted": "..."
    }
  ]
}
```

### config/security_settings.json

```json
{
  "settings": {
    "xp_cmdshell": {"required": 0, "risk": "critical"},
    "clr enabled": {"required": 0, "risk": "high"},
    "cross db ownership chaining": {"required": 0, "risk": "medium"}
  }
}
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error |
| 130 | Interrupted (Ctrl+C) |

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `PYTHONPATH` | Must include `src/` directory |
| `AUDIT_LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING) |

---

## Typical Workflow

```bash
# Set up environment
export PYTHONPATH="./src"

# 1. Run initial audit
python main.py --audit --targets sql_targets.json

# 2. Generate remediation scripts
python main.py --generate-remediation

# 3. Fix issues (execute scripts in SSMS)

# 4. Sync progress (repeat as needed)
python main.py --sync

# 5. Edit Excel: add Notes/Reasons for exceptions

# 6. Finalize
python main.py --finalize --excel output/sql_audit_edited.xlsx
```

---

*Document Version: 1.0 | Last Updated: 2025-12-09*
