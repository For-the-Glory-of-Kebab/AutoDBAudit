# AutoDBAudit User Guide

**Audience**: Database administrators, IT security teams, compliance officers
**Purpose**: Complete guide for conducting SQL Server security audits using AutoDBAudit
**Last Updated**: 2025-12-30

---

## Table of Contents

* [Overview](#overview)
* [Quick Start Guide](#quick-start-guide)
* [Complete Audit Workflow](#complete-audit-workflow)
* [Command Reference](#command-reference)
* [Configuration Management](#configuration-management)
* [Excel Report Interface](#excel-report-interface)
* [Remediation Workflows](#remediation-workflows)
* [Exception Management](#exception-management)
* [Multi-Audit Management](#multi-audit-management)
* [Troubleshooting](#troubleshooting)
* [Best Practices](#best-practices)
* [Advanced Usage](#advanced-usage)

---

## Overview

### What is AutoDBAudit?

AutoDBAudit is a comprehensive SQL Server security auditing and remediation tool that:

* **Audits** SQL Server configurations against security best practices
* **Generates** intelligent remediation scripts for identified issues
* **Tracks** exceptions and justifications for compliance requirements
* **Maintains** persistent audit history across multiple audit cycles
* **Produces** Excel reports for manual review and regulatory compliance

### Key Features

* **Offline-Capable**: No internet connection required
* **Self-Contained**: Single executable with all dependencies
* **Multi-Server**: Audit multiple SQL Server instances simultaneously
* **State-Aware**: Tracks changes between audit cycles
* **Smart Remediation**: Generates safe, reviewable fix scripts
* **Exception Tracking**: Document and justify deviations from standards

### Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   SQL Servers   │───▶│   AutoDBAudit   │───▶│   Excel Report  │
│                 │    │                 │    │                 │
│ • Configurations │    │ • Audit Engine  │    │ • Findings     │
│ • Permissions   │    │ • Sync Engine   │    │ • Exceptions    │
│ • Security      │    │ • Remediation   │    │ • Status        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   SQLite DB     │
                       │                 │
                       │ • Audit History │
                       │ • Annotations   │
                       │ • State         │
                       └─────────────────┘
```

---

## Quick Start Guide

### Prerequisites Checklist

- [ ] Windows environment with administrative access
- [ ] Python 3.11+ installed
- [ ] Access to target SQL Server instances
- [ ] Appropriate permissions on target servers
- [ ] Microsoft ODBC Driver for SQL Server installed

### 5-Minute Setup

1. **Extract and Setup**:
   ```bash
   # Extract AutoDBAudit to a folder
   # Open command prompt as Administrator
   cd C:\Path\To\AutoDBAudit

   # Create virtual environment
   python -m venv autodbaudit_env
   .\autodbaudit_env\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Configure Targets**:
   ```bash
   # Copy example configuration
   copy config\sql_targets.example.json config\sql_targets.json

   # Edit sql_targets.json with your server details
   notepad config\sql_targets.json
   ```

3. **Configure Credentials** (if using SQL authentication):
   ```bash
   # Copy example credentials
   copy credentials\credentials.example.json credentials\credentials.json

   # Edit with your credentials
   notepad credentials\credentials.json
   ```

4. **Run First Audit**:
   ```bash
   # Set Python path
   set PYTHONPATH=%CD%\src

   # Run audit
   python main.py audit --new --name "Initial Audit"
   ```

5. **Review Results**:
   - Open `output\audit_[timestamp]\report.xlsx`
   - Review findings and status

---

## Complete Audit Workflow

### Phase 1: Preparation

#### 1.1 Environment Setup
```bash
# Verify Python environment
python --version  # Should be 3.11+
pip --version     # Should be 23.0+

# Create and activate virtual environment
python -m venv autodbaudit_env
.\autodbaudit_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 1.2 PowerShell Remoting Setup (Required)
```bash
# Prepare target servers for PowerShell remoting
python main.py prepare --targets config\sql_targets.json
```

#### 1.3 Configuration Validation
```bash
# Test connections to all targets
python main.py util --test-connections

# Validate configuration files
python main.py util --validate-config
```

### Phase 2: Initial Audit

#### 2.1 Run New Audit
```bash
# Create new audit with descriptive name
python main.py audit --new --name "Q4 2024 Security Audit"

# Or use default naming
python main.py audit --new
```

#### 2.2 Review Initial Results
- Open Excel report: `output\audit_[timestamp]\report.xlsx`
- Review findings by category:
  - **Critical**: Immediate action required
  - **High**: Important security issues
  - **Medium**: Best practice violations
  - **Low**: Optimization opportunities
  - **Info**: Informational findings

### Phase 3: Remediation Planning

#### 3.1 Generate Remediation Scripts
```bash
# Generate remediation scripts for current audit
python main.py remediate --generate

# Scripts are created in: output\audit_[timestamp]\remediation\
```

#### 3.2 Review Generated Scripts
**Script Categories**:
- `auto_fix.sql`: Safe automatic fixes
- `manual_review.sql`: Requires human approval
- `destructive.sql`: Potentially dangerous operations
- `rollback.sql`: Undo scripts for safety

**Review Process**:
1. Examine each script for safety
2. Check comments for impact assessment
3. Validate prerequisites

#### 3.3 Test Remediation (Dry Run)
```bash
# Test remediation without making changes
python main.py remediate --apply --dry-run

# Review dry-run output for potential issues
```

### Phase 4: Remediation Execution

#### 4.1 Apply Safe Fixes
```bash
# Apply only automatic safe fixes
python main.py remediate --apply --category auto
```

#### 4.2 Apply Manual Fixes
```bash
# Apply fixes requiring review
python main.py remediate --apply --category manual

# Apply all fixes (use with caution)
python main.py remediate --apply --category all
```

#### 4.3 Rollback if Needed
```bash
# Rollback recent changes
python main.py remediate --rollback --last
```

### Phase 5: Sync and Update

#### 5.1 Sync After Changes
```bash
# Update audit status after manual changes
python main.py sync

# Sync specific audit
python main.py sync --audit-id [audit_id]
```

#### 5.2 Add Exceptions
Edit the Excel report to add justifications for accepted risks:
- Open `report.xlsx`
- Add notes in the "Annotations" column
- Save the file

#### 5.3 Update with Exceptions
```bash
# Import exception annotations from Excel
python main.py sync --excel output\audit_[timestamp]\report.xlsx
```

### Phase 6: Finalization and Reporting

#### 6.1 Check Final Status
```bash
# View audit dashboard
python main.py finalize --status

# Check specific audit
python main.py finalize --status --audit-id [audit_id]
```

#### 6.2 Generate Final Report
```bash
# Finalize with updated Excel (includes exceptions)
python main.py finalize --excel output\audit_[timestamp]\report.xlsx
```

#### 6.3 Export for Compliance
```bash
# Export to different formats if needed
python main.py finalize --export pdf
python main.py finalize --export json
```

---

## Command Reference

### Audit Commands

#### `audit --new`
Create a new audit cycle.
```bash
python main.py audit --new --name "Audit Name" --description "Description"
```

**Options**:
- `--name`: Descriptive name for the audit
- `--description`: Detailed description
- `--targets`: Specific target file (default: config/sql_targets.json)

#### `audit --continue`
Continue an existing audit.
```bash
python main.py audit --continue --audit-id [id]
```

#### `audit --list`
List all audits.
```bash
python main.py audit --list
```

### Sync Commands

#### `sync`
Synchronize audit state with current server configurations.
```bash
python main.py sync --audit-id [id] --excel [file.xlsx]
```

**Options**:
- `--audit-id`: Specific audit to sync
- `--excel`: Import annotations from Excel file
- `--force`: Force sync even if no changes detected

### Remediation Commands

#### `remediate --generate`
Generate remediation scripts.
```bash
python main.py remediate --generate --audit-id [id] --aggressiveness [level]
```

**Options**:
- `--audit-id`: Target audit
- `--aggressiveness`: Safety level (conservative, moderate, aggressive)

#### `remediate --apply`
Apply remediation scripts.
```bash
python main.py remediate --apply --category [category] --dry-run
```

**Options**:
- `--category`: Script category (auto, manual, destructive, all)
- `--dry-run`: Preview changes without applying
- `--force`: Skip confirmation prompts

#### `remediate --rollback`
Rollback applied changes.
```bash
python main.py remediate --rollback --last --to-point [timestamp]
```

### Finalize Commands

#### `finalize --status`
Show audit completion status.
```bash
python main.py finalize --status --audit-id [id] --detailed
```

#### `finalize --excel`
Finalize audit with Excel annotations.
```bash
python main.py finalize --excel [file.xlsx] --audit-id [id]
```

### Utility Commands

#### `util --test-connections`
Test connectivity to all targets.
```bash
python main.py util --test-connections --verbose
```

#### `util --validate-config`
Validate configuration files.
```bash
python main.py util --validate-config
```

#### `util --diagnostics`
Run diagnostic checks.
```bash
python main.py util --diagnostics --full
```

### Prepare Commands

#### `prepare`
Configure PowerShell remoting on targets.
```bash
python main.py prepare --targets [config.json] --force
```

**Options**:
- `--targets`: Target configuration file
- `--force`: Reconfigure even if already set up

---

## Configuration Management

### Target Configuration

**File**: `config/sql_targets.json`

**Structure**:
```json
{
  "targets": [
    {
      "id": "prod-sql-01",
      "name": "Production SQL Server 01",
      "server": "sql-prod-01.company.com",
      "instance": null,
      "port": 1433,
      "auth": "integrated",
      "connect_timeout": 30,
      "tags": ["production", "critical"],
      "enabled": true
    }
  ],
  "global_settings": {
    "timeout_seconds": 30,
    "encrypt_connection": true,
    "trust_server_certificate": true
  }
}
```

**Authentication Types**:
- `"integrated"`: Windows Authentication (preferred)
- `"sql"`: SQL Server Authentication

### Credential Management

**File**: `credentials/credentials.json`

**Structure**:
```json
{
  "sql_credentials": {
    "audit_user": {
      "username": "audit_service",
      "password": "encrypted_or_plaintext"
    }
  },
  "windows_credentials": {
    "domain_admin": {
      "username": "DOMAIN\\admin_user",
      "password": "secure_password"
    }
  }
}
```

**Security Best Practices**:
- Use Windows Authentication when possible
- Store credentials securely (encrypt if plaintext)
- Use service accounts with minimal required permissions
- Rotate credentials regularly

---

## Excel Report Interface

### Report Structure

**Sheets**:
1. **Summary**: Overall audit status and statistics
2. **Findings**: Detailed list of all findings
3. **Servers**: Server-specific information
4. **Timeline**: Audit history and changes
5. **Annotations**: Exception justifications

### Finding Status Values

| Status | Color | Meaning | Action Required |
|--------|-------|---------|----------------|
| 🔴 Critical | Red | Immediate security risk | Fix immediately |
| 🟠 High | Orange | Important security issue | Fix soon |
| 🟡 Medium | Yellow | Best practice violation | Review and fix |
| 🟢 Low | Green | Optimization opportunity | Optional |
| 🔵 Info | Blue | Informational | No action |
| ✅ Fixed | Green | Issue resolved | None |
| 📝 Exception | Purple | Accepted risk with justification | Document only |

### Working with Excel

#### Adding Exceptions
1. Open the Excel report
2. Navigate to the "Annotations" column
3. Add justification text for accepted findings
4. Save the file
5. Run `sync --excel [file.xlsx]` to import annotations

#### Manual Edits
- **Safe**: Adding annotations and justifications
- **Caution**: Modifying finding details may cause sync issues
- **Avoid**: Changing status values directly (use sync command)

---

## Remediation Workflows

### Aggressiveness Levels

#### Conservative (Default)
- Only applies completely safe fixes
- Requires manual review for risky operations
- Generates detailed rollback scripts

#### Moderate
- Applies most security fixes automatically
- Flags potentially disruptive changes for review
- Balances security and stability

#### Aggressive
- Applies all recommended fixes
- May cause service disruption
- Requires comprehensive testing

### Script Categories

#### Auto-Fix Scripts
**Safe operations that can be automated**:
- Enable audit settings
- Fix permission issues
- Update configuration values
- Create missing objects

#### Manual Review Scripts
**Operations requiring human approval**:
- Disable services
- Change authentication modes
- Modify system configurations
- Destructive operations

#### Rollback Scripts
**Generated automatically for safety**:
- Reverse applied changes
- Restore previous configurations
- Emergency recovery options

### Execution Workflow

1. **Generate**: Create scripts based on findings
2. **Review**: Examine scripts for safety and impact
3. **Test**: Run dry-run to validate changes
4. **Apply**: Execute scripts in safe order
5. **Verify**: Confirm fixes worked as expected
6. **Document**: Record changes and justifications

---

## Exception Management

### When to Use Exceptions

**Appropriate for exceptions**:
- Business requirements conflict with security standards
- Legacy application compatibility issues
- Risk acceptance with proper justification
- Temporary measures with remediation plans

**Not appropriate for exceptions**:
- Critical security vulnerabilities
- Regulatory compliance requirements
- Easily fixable issues
- Lack of resources (should be prioritized)

### Adding Exceptions

#### Method 1: Excel Interface
1. Open audit report Excel file
2. Locate finding to except
3. Add detailed justification in "Annotations" column
4. Include:
   - Business reason
   - Risk assessment
   - Mitigation measures
   - Review date
   - Owner contact

#### Method 2: Command Line
```bash
# Import exceptions from updated Excel
python main.py sync --excel report_with_exceptions.xlsx
```

### Exception Tracking

**Exception Fields**:
- **Finding ID**: Unique identifier
- **Justification**: Detailed explanation
- **Owner**: Responsible person/department
- **Review Date**: When to reassess
- **Risk Level**: Accepted risk assessment

**Regular Reviews**:
- Monthly review of all exceptions
- Annual risk reassessment
- Change management integration

---

## Multi-Audit Management

### Audit Lifecycle

```
New Audit ──▶ Active ──▶ Remediation ──▶ Finalized
    │            │            │               │
    │            │            │               │
    └────────────┼────────────┼───────────────┘
                 ▼            ▼               ▼
              Superseded    Superseded      Archived
```

### Managing Multiple Audits

#### Creating Audit Series
```bash
# Quarterly audit series
python main.py audit --new --name "Q1 2024 Security Audit"
python main.py audit --new --name "Q2 2024 Security Audit"
```

#### Comparing Audits
```bash
# View audit comparison
python main.py finalize --compare --audit-ids 1,2,3
```

#### Audit Archival
```bash
# Archive completed audits
python main.py util --archive-audits --older-than 90days
```

### State Tracking

**Finding States**:
- **NEW**: First time discovered
- **EXISTING**: Previously identified
- **FIXED**: Resolved since last audit
- **REGRESSION**: Fixed but reappeared
- **EXCEPTION**: Accepted risk

---

## Troubleshooting

### Common Issues

#### Connection Problems

**ODBC Driver Issues**:
```bash
# Check installed drivers
python -c "import pyodbc; print(pyodbc.drivers())"

# Install Microsoft ODBC Driver 18
# Download from: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
```

**Network Connectivity**:
```bash
# Test basic connectivity
ping target-server

# Test SQL Server port
telnet target-server 1433
```

**Authentication Failures**:
- Verify credentials in `credentials.json`
- Check SQL Server authentication mode
- Validate domain membership

#### PowerShell Remoting Issues

**WinRM Not Configured**:
```powershell
# Enable WinRM
Enable-PSRemoting -Force

# Add to TrustedHosts
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
```

**Certificate Problems**:
```powershell
# Use HTTP instead of HTTPS for testing
Set-Item WSMan:\localhost\Client\AllowUnencrypted -Value $true
```

#### Permission Issues

**SQL Server Permissions**:
```sql
-- Grant required permissions
GRANT VIEW SERVER STATE TO [audit_user];
GRANT VIEW ANY DEFINITION TO [audit_user];
```

**File System Permissions**:
- Ensure write access to `output/` directory
- Check permissions on configuration files

### Diagnostic Commands

#### Full System Diagnostics
```bash
# Run comprehensive diagnostics
python main.py util --diagnostics --full --output diagnostics.log
```

#### Connection Testing
```bash
# Test all target connections
python main.py util --test-connections --verbose --log connections.log
```

#### Configuration Validation
```bash
# Validate all configuration files
python main.py util --validate-config --strict
```

### Log Analysis

**Log Locations**:
- Application logs: `output/logs/`
- PowerShell logs: `output/ps_logs/`
- SQL logs: `output/sql_logs/`

**Common Error Patterns**:
- `Connection timeout`: Network or firewall issues
- `Login failed`: Authentication problems
- `Permission denied`: Insufficient SQL permissions
- `WinRM error`: PowerShell remoting configuration

### Getting Help

**Built-in Help**:
```bash
# General help
python main.py --help

# Command-specific help
python main.py audit --help
python main.py remediate --help
```

**Support Resources**:
- [System Requirements](getting-started/requirements.md)
- [CLI Reference](cli/reference.md)
- [Troubleshooting Guide](deployment/troubleshooting.md)

---

## Best Practices

### Audit Planning

#### Pre-Audit Preparation
- Schedule audits during maintenance windows
- Notify stakeholders of upcoming audits
- Prepare exception justifications in advance
- Backup critical systems

#### During Audit
- Review findings promptly
- Prioritize critical and high-severity issues
- Document business justifications for exceptions
- Test remediation scripts in non-production first

#### Post-Audit
- Implement approved fixes
- Update documentation
- Schedule follow-up audits
- Review exception validity

### Security Considerations

#### Credential Security
- Use Windows Authentication when possible
- Store credentials encrypted
- Rotate credentials regularly
- Limit credential access to authorized personnel

#### Network Security
- Use encrypted connections (SSL/TLS)
- Restrict network access to necessary systems
- Monitor audit activity
- Implement least-privilege access

### Operational Best Practices

#### Environment Management
- Use separate environments for testing
- Maintain configuration backups
- Document custom settings
- Version control configuration files

#### Change Management
- Test changes in development first
- Implement gradual rollouts
- Maintain rollback capabilities
- Document all changes

---

## Advanced Usage

### Custom Scripts and Automation

#### Integration with CI/CD
```bash
# Automated audit in CI pipeline
python main.py audit --new --name "CI Audit $(date)" --quiet
python main.py remediate --generate --aggressiveness conservative
python main.py finalize --status --exit-on-issues
```

#### Scheduled Audits
```powershell
# PowerShell scheduled task
$action = New-ScheduledTaskAction -Execute "python.exe" -Argument "main.py audit --new --name 'Scheduled Audit'"
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 4 -DaysOfWeek Monday -At 2am
Register-ScheduledTask -TaskName "AutoDBAudit" -Action $action -Trigger $trigger -User "SYSTEM"
```

### Advanced Configuration

#### Custom Target Groups
```json
{
  "target_groups": {
    "production": ["prod-sql-01", "prod-sql-02"],
    "development": ["dev-sql-01"],
    "dr": ["dr-sql-01"]
  }
}
```

#### Conditional Logic
```bash
# Audit only production servers
python main.py audit --new --targets config/prod_targets.json

# Skip disabled targets
python main.py audit --new --skip-disabled
```

### Performance Optimization

#### Large-Scale Audits
- Use parallel processing for multiple servers
- Configure appropriate timeouts
- Optimize SQL queries for large databases
- Use incremental sync when possible

#### Resource Management
- Monitor memory usage for large audits
- Configure appropriate thread pools
- Use SSD storage for better performance
- Archive old audit data regularly

### Integration Patterns

#### SIEM Integration
```bash
# Export findings to SIEM format
python main.py finalize --export json --format siem
```

#### Reporting Integration
```bash
# Generate compliance reports
python main.py finalize --report compliance --format pdf
```

---

*Complete user guide reviewed: 2025-12-30 | AutoDBAudit v1.0.0*