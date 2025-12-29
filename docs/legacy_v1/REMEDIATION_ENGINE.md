# Remediation Engine

## Overview

Generates T-SQL and PowerShell remediation scripts from audit findings.
Scripts are exception-aware and use aggressiveness levels.

## Key Features

### 1. Individual INSERT Lines (Easy Commenting)
```sql
-- Each line can be commented independently
INSERT INTO @LoginsToFix (login_name) VALUES (N'user1');
-- INSERT INTO @LoginsToFix (login_name) VALUES (N'excepted_user');  -- Exceptionalized
INSERT INTO @LoginsToFix (login_name) VALUES (N'user3');
```

### 2. SQL 2008+ Compatible
- No multi-row VALUES constructor
- LOCAL FAST_FORWARD cursors
- No OFFSET/FETCH

### 3. Aggressiveness Levels

| Level | Exceptions | Connecting User | SA Account |
|-------|------------|-----------------|------------|
| 1 (Default) | Commented | Commented + DANGER | ACTIVE (unless conn user) |
| 2 | Commented | Commented + DANGER | ACTIVE |
| 3 | Active | Commented + DANGER | ACTIVE |

### 4. Connecting User Protection
Your audit login is NEVER auto-uncommented, even at level 3:
```sql
-- ⚠️🔴🔴🔴 EXTREME DANGER: AUDITADMIN 🔴🔴🔴⚠️
-- MODIFYING IT WILL LOCK YOU OUT IMMEDIATELY!
-- INSERT INTO @LoginsToFix VALUES (N'auditadmin', 'DISABLE');
```

## CLI Usage

```bash
python main.py remediate --generate                     # Level 1 (safe)
python main.py remediate --generate --aggressiveness 3  # Level 3
python main.py remediate --apply --dry-run              # Simulate
```

## Templates Location

```
src/autodbaudit/application/remediation/templates/
├── tsql/main_script.sql.j2
└── powershell/os_fixes.ps1.j2
```
