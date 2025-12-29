# Access Preparation & Remediation Module Implementation Plan

## Executive Summary

Two new modules for AutoDBAudit:
1. **Access Preparation** (`--prepare`): Non-destructively enables remote access
2. **Remediation Engine** (`--remediate`): Generates and applies T-SQL fix scripts

---

## Decisions (Confirmed)

| Question | Decision |
|----------|----------|
| **Jinja2** | ✅ YES - with extensive tests before use |
| **pywinrm** | ✅ YES - add any libs needed for access |
| **UI Confirmation** | `--yes` for auto-confirm, `--force` for finalize warnings |
| **Rollback Storage** | Both DB AND .sql files (kept in sync) |

---

### A1. Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Non-destructive** | Record original state before any changes |
| **Revertible** | Every change logged for `--revert` command |
| **Exhaustive** | Try all methods to gain access |
| **Documented** | Store access status in DB for sync/remediation |
| **Overridable** | User can manually mark targets as accessible |
| **Platform-aware** | Separate paths for Windows vs Linux (Docker) |

### A2. Command Interface

```powershell
# Prepare all targets (detect OS, try WinRM, record state)
autodbaudit --prepare

# Prepare specific targets
autodbaudit --prepare --targets prod-sql dev-sql

# Check preparation status
autodbaudit --prepare --status

# Revert all access changes to original state
autodbaudit --prepare --revert

# Force mark a target as accessible (manual override)
autodbaudit --prepare --mark-accessible prod-sql
```

### A3. Access Preparation Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    --prepare Command                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Load targets from sql_targets.json                       │
│  2. Detect OS for each target (Windows vs Linux)             │
│  3. Record original state snapshot                           │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
┌───────────────────────┐           ┌───────────────────────┐
│   Windows Target      │           │   Linux Target        │
│   ─────────────────   │           │   ─────────────────   │
│ 1. Test WinRM         │           │ 1. Test SSH (future)  │
│ 2. If failed:         │           │ 2. Mark as SQL-only   │
│    a. Check firewall  │           │ 3. Document in DB     │
│    b. Check WinRM svc │           └───────────────────────┘
│    c. Check GPO       │
│    d. Check TrustedH  │
│    e. Enable each     │
│ 3. Verify access      │
│ 4. Store in DB        │
└───────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Output: access_status table in audit_history.db             │
│  ─────────────────────────────────────────────────────────   │
│  | target_id | os_type | access_method | status | original | │
│  | prod-sql  | windows | winrm         | ready  | {...}    | │
│  | dev-sql   | linux   | sql_only      | ready  | null     | │
│  | test-sql  | windows | winrm         | failed | {...}    | │
└─────────────────────────────────────────────────────────────┘
```

### A4. Windows WinRM Preparation Steps

Each step is **logged** with original value for revert:

| Step | Check | Fix if Failed | Registry/Service Key |
|------|-------|---------------|---------------------|
| 1 | WinRM Service running | `Set-Service WinRM -StartupType Automatic; Start-Service WinRM` | `HKLM\SYSTEM\CurrentControlSet\Services\WinRM` |
| 2 | WinRM Listener exists | `winrm quickconfig -quiet` | `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\WSMAN` |
| 3 | Firewall rule exists | `Enable-NetFirewallRule -Name WINRM-HTTP-In-TCP` | Windows Firewall store |
| 4 | TrustedHosts includes us | `Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*"` | `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\WSMAN\Client` |
| 5 | PS Remoting enabled | `Enable-PSRemoting -Force -SkipNetworkProfileCheck` | Multiple |
| 6 | Auth methods enabled | `Set-Item WSMan:\localhost\Service\Auth\Basic -Value $true` | WSMAN auth store |

### A5. State Snapshot Schema

```python
@dataclass
class TargetAccessState:
    target_id: str
    hostname: str
    os_type: Literal["windows", "linux", "unknown"]
    
    # Access status
    access_method: Literal["winrm", "ssh", "sql_only", "none"]
    access_status: Literal["ready", "partial", "failed", "manual"]
    access_error: str | None
    
    # Original state (for revert)
    original_snapshot: dict  # All settings before changes
    changes_made: list[dict]  # Each change logged
    
    # Timestamps
    prepared_at: datetime
    last_verified_at: datetime
```

### A6. Linux (Docker) Handling

For Linux targets:
- No WinRM available
- Mark as `sql_only` access method
- T-SQL remediation scripts work fine
- OS-level checks (services, etc.) marked as "unavailable"
- Future: Add SSH support

---

## Part B: Remediation Engine (`--remediate`)

### B1. Remediation Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  --remediate Command                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Load findings from last --sync                           │
│  2. Filter: FAIL/WARN items without exceptions               │
│  3. Check access_status for each target                      │
│  4. Generate remediation scripts                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Script Generation (per finding type)                        │
│  ─────────────────────────────────────────────────────────   │
│  SA Account:    ALTER LOGIN [sa] DISABLE;                    │
│  Weak Login:    ALTER LOGIN [x] WITH CHECK_POLICY=ON;        │
│  Config:        EXEC sp_configure 'xp_cmdshell', 0;          │
│  Linked Server: EXEC sp_dropserver @server='...';            │
│  etc.                                                        │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
┌───────────────────────┐           ┌───────────────────────┐
│   --remediate         │           │   --remediate --apply │
│   (default: files)    │           │   (execute on server) │
│   ─────────────────   │           │   ─────────────────   │
│ Generate .sql files:  │           │ Requires:             │
│ - fix_sa_account.sql  │           │ - --prepare complete  │
│ - fix_logins.sql      │           │ - Confirmation prompt │
│ - fix_configs.sql     │           │ - Rollback generated  │
│ - ROLLBACK_*.sql      │           │ Execute via pyodbc    │
└───────────────────────┘           └───────────────────────┘
```

### B2. Remediation Script Structure

```sql
-- ============================================================================
-- AutoDBAudit Remediation Script
-- Generated: 2025-12-25 20:00:00
-- Target: prod-sql\PROD
-- Category: SA Account
-- ============================================================================

-- Pre-check
IF NOT EXISTS (SELECT 1 FROM sys.sql_logins WHERE name='sa' AND is_disabled=0)
BEGIN
    PRINT 'SKIP: SA account already disabled';
    RETURN;
END

-- Remediation
ALTER LOGIN [sa] DISABLE;

-- Post-check
IF NOT EXISTS (SELECT 1 FROM sys.sql_logins WHERE name='sa' AND is_disabled=0)
    PRINT 'SUCCESS: SA account disabled';
ELSE
    PRINT 'FAILED: SA account still enabled';
```

### B3. Rollback Script Structure

```sql
-- ============================================================================
-- AutoDBAudit ROLLBACK Script
-- Generated: 2025-12-25 20:00:00
-- Original state captured before remediation
-- ============================================================================

-- Rollback SA Account
-- Original: sa was ENABLED
ALTER LOGIN [sa] ENABLE;
```

---

## Part C: Module Architecture

### C1. New Package Structure

```
src/autodbaudit/
├── application/
│   ├── access_preparation/     # NEW
│   │   ├── __init__.py
│   │   ├── service.py          # AccessPreparationService
│   │   ├── windows_access.py   # WinRM/Firewall/GPO logic
│   │   ├── linux_access.py     # SSH (future)
│   │   └── state_snapshot.py   # Original state capture
│   │
│   ├── remediation/            # NEW/REFACTOR
│   │   ├── __init__.py
│   │   ├── service.py          # RemediationService
│   │   ├── script_generator.py # T-SQL generation
│   │   ├── rollback_generator.py
│   │   └── templates/          # Script templates
│   │       ├── sa_account.sql.jinja
│   │       ├── logins.sql.jinja
│   │       ├── config.sql.jinja
│   │       └── ...
│   │
│   └── ...
│
├── infrastructure/
│   └── sqlite/
│       └── access_schema.py    # NEW: access_status table
```

### C2. Database Schema Additions

```sql
-- Access preparation status per target
CREATE TABLE IF NOT EXISTS access_status (
    id INTEGER PRIMARY KEY,
    target_id TEXT NOT NULL UNIQUE,
    hostname TEXT NOT NULL,
    os_type TEXT NOT NULL,  -- 'windows', 'linux', 'unknown'
    access_method TEXT NOT NULL,  -- 'winrm', 'ssh', 'sql_only', 'none'
    access_status TEXT NOT NULL,  -- 'ready', 'partial', 'failed', 'manual'
    access_error TEXT,
    original_snapshot TEXT,  -- JSON
    changes_made TEXT,  -- JSON array
    prepared_at TEXT NOT NULL,
    last_verified_at TEXT,
    manual_override INTEGER DEFAULT 0
);

-- Remediation history
CREATE TABLE IF NOT EXISTS remediation_runs (
    id INTEGER PRIMARY KEY,
    audit_run_id INTEGER REFERENCES audit_runs(id),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,  -- 'pending', 'applied', 'failed', 'rolled_back'
    findings_count INTEGER,
    applied_count INTEGER,
    failed_count INTEGER,
    scripts_path TEXT
);

-- Per-finding remediation status
CREATE TABLE IF NOT EXISTS remediation_items (
    id INTEGER PRIMARY KEY,
    remediation_run_id INTEGER REFERENCES remediation_runs(id),
    finding_key TEXT NOT NULL,
    script_content TEXT,
    rollback_content TEXT,
    status TEXT NOT NULL,  -- 'generated', 'applied', 'failed', 'skipped'
    error_message TEXT,
    applied_at TEXT
);
```

---

## Part D: Implementation Order

### Phase 1: Access Preparation (5-7 days)

1. [ ] Create `access_schema.py` with tables
2. [ ] Create `AccessPreparationService`
3. [ ] Implement OS detection (Windows vs Linux)
4. [ ] Implement WinRM preparation steps
5. [ ] Implement state snapshot capture
6. [ ] Implement `--revert` functionality
7. [ ] Add CLI commands (`--prepare`, `--prepare --status`, `--prepare --revert`)
8. [ ] Tests for access preparation

### Phase 2: Remediation Engine (5-7 days)

1. [ ] Create remediation schema
2. [ ] Create Jinja2 templates for each finding type
3. [ ] Create `RemediationService`
4. [ ] Implement script generation
5. [ ] Implement rollback generation
6. [ ] Add CLI commands (`--remediate`, `--remediate --apply`)
7. [ ] Integration with access_status
8. [ ] Tests for remediation

### Phase 3: Integration (2-3 days)

1. [ ] Integrate with `--sync` (check access_status)
2. [ ] Update CLI help and documentation
3. [ ] E2E tests with simulation scripts
4. [ ] Documentation updates

---

## Part E: Libraries & Tools

| Library | Purpose |
|---------|---------|
| `pywinrm` | WinRM client for Python |
| `jinja2` | Template engine for T-SQL scripts |
| `paramiko` | SSH client (future Linux support) |
| Built-in `subprocess` | PowerShell execution on local machine |

---

## Questions for User

1. **Jinja2**: OK to add for templated script generation?
2. **pywinrm**: OK to add for WinRM client operations?
3. **Execution model**: Should `--remediate --apply` require explicit confirmation each time, or allow `--yes` flag?
4. **Rollback storage**: Store in DB only, or also as .sql files?
