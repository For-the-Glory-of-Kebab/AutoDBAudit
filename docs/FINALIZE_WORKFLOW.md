# Diff-Based Finalize Workflow

> **Status**: Phase 2 In Progress  
> **Last Updated**: 2025-12-09

## Finding Categories

| Category | Remediation Type | Script? |
|----------|-----------------|---------|
| Login/Access | TSQL | ✅ Yes |
| Configuration | TSQL | ✅ Yes |
| Database Props | TSQL | ✅ Yes |
| Backups | Manual | ❌ No |
| Orphaned Users | Investigation | ⚠️ Partial |
| Linked Servers | Investigation | ⚠️ Partial |
| Version/Patches | External Tool | ❌ No |

## Progress

### ✅ Phase 1: Findings Storage - COMPLETE
- findings + finding_changes tables
- 9 finding types wired: SA, config, logins, databases, db_users, linked_servers, backups
- 142 findings stored per audit

### 🔄 Phase 2: Remediation Scripts - IN PROGRESS
- Create remediate_service.py
- Add --remediate CLI command
- Generate per-entity TSQL scripts

### 📋 Phase 3: Finalize Command
- --finalize re-audits and diffs
- Detects fixed vs excepted

### 📋 Phase 4: Exception Workflow
- Persist exceptions from Excel
