# Error Codes Reference

**Audience**: Developers, system administrators, automation scripts
**Purpose**: Complete reference for AutoDBAudit exit codes and error handling
**Last Updated**: 2025-12-30

---

## Table of Contents

* [Exit Code Overview](#exit-code-overview)
* [Success Codes](#success-codes)
* [Error Categories](#error-categories)
* [Command-Specific Errors](#command-specific-errors)
* [Troubleshooting by Exit Code](#troubleshooting-by-exit-code)
* [Logging and Diagnostics](#logging-and-diagnostics)
* [Error Recovery](#error-recovery)

---

## Exit Code Overview

AutoDBAudit uses standard Unix exit codes to indicate operation results. Exit codes follow these conventions:

* **0**: Success - Operation completed successfully
* **1**: General error - Operation failed due to an error
* **130**: User interruption - Operation cancelled by user (Ctrl+C)

All exit codes are documented and consistent across all commands.

---

## Success Codes

### Code 0: SUCCESS

**Meaning**: Operation completed successfully with no errors.

**When Returned**:
- Audit completed successfully
- Sync operation finished without issues
- Remediation scripts executed successfully
- Configuration validation passed
- All requested operations completed

**Example Output**:
```
✅ Audit completed successfully!
📊 Report: output\audit_2025-01-15_143022\report.xlsx
💾 Database: output\audit_history.db
```

---

## Error Categories

### Code 1: GENERAL_ERROR

**Meaning**: Operation failed due to an error condition.

**Common Causes**:
- Configuration file not found or invalid
- Database connection failures
- Permission denied errors
- File system errors
- Unexpected exceptions during execution

**Sub-categories** (logged in detail):
- Configuration errors
- Connection errors
- Permission errors
- File system errors
- Runtime exceptions

---

## Command-Specific Errors

### Audit Command Errors

#### Configuration Errors
```
❌ Configuration file not found: config/sql_targets.json
```
**Cause**: Target configuration file missing or inaccessible
**Solution**: Verify file exists and has correct permissions

#### Connection Errors
```
❌ Failed to connect to SQL Server: target-server
```
**Cause**: Network connectivity, authentication, or SQL Server issues
**Solution**: Check network, credentials, and SQL Server status

#### Permission Errors
```
❌ Insufficient permissions on target: target-server
```
**Cause**: Missing `VIEW SERVER STATE` or `VIEW ANY DEFINITION` permissions
**Solution**: Grant required permissions to audit user

### Sync Command Errors

#### Database Errors
```
❌ Could not open audit database: output/audit_history.db
```
**Cause**: Database file corrupted or inaccessible
**Solution**: Check file permissions, restore from backup if needed

#### Excel File Errors
```
❌ Could not read Excel file: report.xlsx
```
**Cause**: Excel file corrupted, missing, or inaccessible
**Solution**: Verify file integrity and permissions

### Remediation Command Errors

#### Script Execution Errors
```
❌ PowerShell script failed (exit code: 1)
```
**Cause**: Remediation script encountered an error
**Solution**: Review script output and fix underlying issue

#### Rollback Errors
```
❌ Rollback failed: Could not restore configuration
```
**Cause**: Rollback script failed or original state unknown
**Solution**: Manual intervention required

### Prepare Command Errors

#### WinRM Configuration Errors
```
❌ WinRM configuration failed on target: server-name
```
**Cause**: PowerShell remoting not properly configured
**Solution**: Run prepare command with administrative privileges

#### Authentication Errors
```
❌ Authentication failed for target: server-name
```
**Cause**: Invalid credentials or authentication method
**Solution**: Verify credentials and authentication configuration

### Utility Command Errors

#### ODBC Driver Errors
```
❌ Microsoft ODBC Driver for SQL Server not found
```
**Cause**: Required ODBC driver not installed
**Solution**: Install Microsoft ODBC Driver 18 or later

#### Validation Errors
```
❌ Configuration validation failed: Invalid JSON syntax
```
**Cause**: Configuration file contains syntax errors
**Solution**: Fix JSON syntax and validate file

---

## Troubleshooting by Exit Code

### Exit Code 1 Analysis

When AutoDBAudit returns exit code 1, follow this troubleshooting flow:

#### Step 1: Check Logs
```bash
# Check application logs
type output\logs\autodbaudit.log

# Check command-specific logs
type output\logs\audit_*.log
```

#### Step 2: Review Error Messages
- Look for specific error messages in console output
- Check for "❌" prefixed error lines
- Note any file paths, server names, or error codes mentioned

#### Step 3: Common Exit Code 1 Scenarios

**Configuration Issues**:
- Missing or invalid `sql_targets.json`
- Incorrect credential files
- Invalid audit configuration

**Connection Issues**:
- SQL Server not accessible
- Network connectivity problems
- Firewall blocking connections

**Permission Issues**:
- Insufficient SQL Server permissions
- File system permission denied
- Windows administrative rights required

**Resource Issues**:
- Insufficient disk space
- Memory constraints
- Database file locked

### Exit Code 130 Analysis

**Cause**: User cancelled operation with Ctrl+C or similar interrupt signal.

**Handling**:
- Operation was cleanly terminated
- No cleanup required (handled automatically)
- Can be restarted safely
- Check logs for partial completion status

---

## Logging and Diagnostics

### Log File Locations

**Main Application Log**:
```
output/logs/autodbaudit.log
```

**Command-Specific Logs**:
```
output/logs/audit_[timestamp].log
output/logs/sync_[timestamp].log
output/logs/remediate_[timestamp].log
```

**PowerShell Logs**:
```
output/ps_logs/
```

### Log Levels

| Level | Description | When Used |
|-------|-------------|-----------|
| `DEBUG` | Detailed diagnostic information | Development/troubleshooting |
| `INFO` | General operational messages | Normal operation |
| `WARNING` | Potential issues that don't stop execution | Non-critical issues |
| `ERROR` | Error conditions that cause failures | Operation failures |
| `CRITICAL` | Severe errors requiring immediate attention | System-level failures |

### Diagnostic Commands

#### Full System Diagnostics
```bash
python main.py util --diagnostics --full --output diagnostics.log
```

#### Connection Testing
```bash
python main.py util --test-connections --verbose --log connections.log
```

#### Configuration Validation
```bash
python main.py util --validate-config --strict
```

---

## Error Recovery

### Automatic Recovery

AutoDBAudit includes several automatic recovery mechanisms:

#### Stale Run Cleanup
- Automatically cleans up incomplete operations on startup
- Resumes interrupted audits where possible
- Prevents database corruption from crashes

#### Connection Retry Logic
- Retries failed connections with backoff
- Falls back to alternative authentication methods
- Continues with remaining targets if some fail

#### Transaction Safety
- Database operations use transactions
- Automatic rollback on failures
- Maintains data consistency

### Manual Recovery Procedures

#### After Failed Audit
```bash
# Check audit status
python main.py audit --list

# Resume incomplete audit
python main.py audit --id [audit_id]

# Or start fresh
python main.py audit --new --name "Recovery Audit"
```

#### After Failed Sync
```bash
# Retry sync operation
python main.py sync --audit-id [audit_id]

# Force sync if needed
python main.py sync --audit-id [audit_id] --force
```

#### After Failed Remediation
```bash
# Check remediation status
python main.py finalize --status

# Rollback if necessary
python main.py remediate --rollback --last

# Retry remediation
python main.py remediate --apply
```

### Data Recovery

#### Database Backup
AutoDBAudit automatically maintains database integrity, but for critical scenarios:

```bash
# Backup database before risky operations
copy output\audit_history.db output\audit_history.backup
```

#### Configuration Backup
```bash
# Backup configuration files
copy config\*.json config\backup\
```

### Prevention Best Practices

#### Pre-Flight Checks
```bash
# Always run validation before operations
python main.py util --validate-config
python main.py util --test-connections
```

#### Environment Preparation
```bash
# Ensure proper setup
python main.py prepare --targets config\sql_targets.json
```

#### Monitoring
- Monitor log files during operations
- Check exit codes in automation scripts
- Implement alerting for non-zero exit codes

---

## Error Code Reference Table

| Exit Code | Category | Description | Recovery Action |
|-----------|----------|-------------|----------------|
| 0 | Success | Operation completed successfully | None required |
| 1 | General Error | Operation failed - check logs for details | Review logs, fix issues, retry |
| 130 | User Interrupt | Operation cancelled by user | Safe to restart |

### Error Message Patterns

**Configuration Errors**:
- `❌ Configuration file not found`
- `❌ Configuration validation failed`
- `❌ Invalid JSON syntax`

**Connection Errors**:
- `❌ Failed to connect to SQL Server`
- `❌ Network timeout`
- `❌ Authentication failed`

**Permission Errors**:
- `❌ Insufficient permissions`
- `❌ Access denied`
- `❌ Permission denied`

**System Errors**:
- `❌ File not found`
- `❌ Disk full`
- `❌ Out of memory`

---

*Error codes reference reviewed: 2025-12-30 | AutoDBAudit v1.0.0*