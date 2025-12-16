# AI Runbook – AutoDBAudit

> **For AI assistants**: Quick reference to work on this repo without rediscovering context.
> **Last Updated**: 2025-12-11

---

## Project Summary

**AutoDBAudit** is a self-contained, offline-capable SQL Server audit and remediation tool. It audits instances against 28+ security requirements, generates Excel reports with dropdown validation, suggests T-SQL fixes, tracks actions/exceptions in SQLite, and (eventually) orchestrates hotfix deployments.

**Design Goal**: A person with ZERO SQL experience should be able to run audits, apply fixes, and deliver compliance results.

---

## Key Architectural Invariants

| Invariant | Detail |
|-----------|--------|
| **Layered structure** | `src/autodbaudit/{domain, application, infrastructure, interface, hotfix}` |
| **SQLite is canonical** | `output/audit_history.db`; Excel is generated from it |
| **No ORM** | Use `sqlite3` with explicit SQL |
| **Excel via openpyxl** | No other Excel libraries |
| **Offline-first** | Must work on air-gapped Windows machines |
| **SQL 2008 R2 → 2025+** | Versioned queries via `query_provider.py` |

---

## Hard Rules for Agents

1. **Do NOT modify** `1-Report-and-Setup/` — legacy PowerShell reference only
2. **Do NOT change** `db-requirements.md` semantics without explicit instruction
3. **Extend** the layered package structure; never reintroduce flat `core/` or `utils/`
4. **Use** SQLite + openpyxl; no ORM or alternate Excel engine
5. **Keep domain layer pure** — no file/network I/O there
6. **Sync docs** — keep `docs/` folder updated with any significant changes
7. **Pretend directory is** `D:\Raja-Initiative` for the main development machine

### ⚠️ CRITICAL: Command Execution Rules

**See full documentation:** `.agent/workflows/run-python.md`

**Patterns that TRIGGER confirmation prompts:**
- Semicolons: `cmd1; cmd2`
- Environment vars: `$env:VAR="x"; cmd`
- Chained: `cmd1 && cmd2`
- Pipe to file: `cmd | Out-File x.txt`
- File writes: `Copy-Item`, `Move-Item`, `Remove-Item`, `New-Item`

**Patterns that AUTO-RUN:**
- Simple single commands: `python main.py --audit`
- Read-only: `Get-Content`, `dir`, `type`, `cat`
- Helper scripts: `.\run.ps1 --audit`

**Mitigation strategies:**
1. Use `.\run.ps1` wrapper instead of `$env:PYTHONPATH=...`
2. Have user activate venv once: `.\venv\Scripts\Activate.ps1`
3. Split compound commands into separate tool calls
4. Use `write_to_file` / `replace_file_content` tools instead of shell writes
5. For file I/O (move/copy/delete), use tool functions, not PowerShell

**User setup (once per session):**
```powershell
cd c:\Users\sickp\source\SQLAuditProject\AutoDBAudit
.\venv\Scripts\Activate.ps1
```

---

## Current Implementation Status

| Component | Status |
|-----------|--------|
| **Audit + Excel** | ✅ Working - 20+ sheets (inc. Role Matrix, Permissions) |
| **Modular Collectors** | ✅ Working - Refactored into `application/collectors/` |
| **Modular Remediation** | ✅ Working - Refactored into `application/remediation/` |
| **SQLite Storage** | ✅ Working - findings, annotations, action_log |
| **Remediation Scripts** | ✅ Working - 4-category + rollback + Aggressiveness Levels |
| **Script Executor** | ✅ Working - with dry-run, credential protection |
| **Sync/Finalize** | ✅ Working - Full E2E verification |
| **Hotfix Deployment** | ⏳ Stubs only - NotImplementedError |

---

## Key Files to Read First

| File | Purpose |
|------|---------|
| [`docs/SESSION_HANDOFF_DEV_SWITCH.md`](../docs/SESSION_HANDOFF_DEV_SWITCH.md) | **START HERE** - Machine Handoff Context |
| [`docs/PROJECT_STATUS.md`](../docs/PROJECT_STATUS.md) | **Comprehensive** current state |
| [`docs/EXCEL_COLUMNS.md`](../docs/EXCEL_COLUMNS.md) | **Strict Schema** for all reports |
| [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) | Codebase architecture with diagrams |
| [`db-requirements.md`](../db-requirements.md) | 28 audit requirements |

---

## What's Working Now

- ✅ **CLI** - All commands wired in `cli.py` and `src/main.py`.
- ✅ **Excel Package** - Modular logic in `infrastructure/excel/`.
- ✅ **20+ Sheets** - All populated, including Matrix and Permissions.
- ✅ **Query Provider** - SQL 2008-2025+ compatible.
- ✅ **Refactoring** - Full modularization of Collectors and Remediation completed.

## What's Still Pending

- ⏳ `--deploy-hotfixes` (stubs exist, raises NotImplementedError)
- ⏳ `Inventory Population` (raw tables `logins`, `server_info` etc. are empty by design; using `findings`)

---

*Last updated: 2025-12-16*
