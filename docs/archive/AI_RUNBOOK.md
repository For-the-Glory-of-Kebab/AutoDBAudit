# AI Runbook – AutoDBAudit

> **For AI assistants**: Quick reference to work on this repo without rediscovering context.
> **Last Updated**: 2025-12-17

---

## Project Summary

**AutoDBAudit** is an offline-capable SQL Server audit and remediation tool. It audits instances against 28+ security requirements (see `db-requirements.md`), generates Excel reports with dropdown validation, suggests T-SQL fixes, tracks actions/exceptions in SQLite, and (eventually) orchestrates hotfix deployments.

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

### ⚠️ CRITICAL: Command Execution Rules

**See full documentation:** `.agent/workflows/run-python.md`

**Auto-run safe commands:**
- Simple single commands: `python main.py --audit`
- Read-only: `Get-Content`, `dir`, `type`, `cat`
- Helper scripts: `.\run.ps1 --audit`

**User setup (once per session):**
```powershell
cd c:\Users\sickp\source\SQLAuditProject\AutoDBAudit
.\venv\Scripts\Activate.ps1
```

---

## Current Implementation Status

| Component | Status |
|-----------|--------|
| **Audit + Excel** | ✅ Working - 17 sheets |
| **Annotation Sync** | ✅ Working - All 17 sheets in config |
| **SQLite Storage** | ✅ Working - findings, annotations, action_log |
| **Remediation Scripts** | ✅ Working - 4-category + rollback |
| **Sync Command** | ✅ Working - Fixed infinite loop & action log |
| **Finalize Command** | ⚠️ Partial - Basic implementation |
| **Hotfix Deployment** | ⏳ Stubs only |

---

## Key Files to Read First

| File | Purpose |
|------|---------|
| [`docs/PROJECT_STATUS.md`](PROJECT_STATUS.md) | **Current state** (read first) |
| [`docs/TODO.md`](TODO.md) | Task tracker |
| [`db-requirements.md`](../db-requirements.md) | 28 audit requirements |
| [`docs/EXCEL_COLUMNS.md`](EXCEL_COLUMNS.md) | **Strict Schema** for all reports |
| [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) | Codebase architecture with diagrams |

---

## Critical Code Locations

| Feature | File |
|---------|------|
| Sheet annotation config | `src/autodbaudit/application/annotation_sync.py:27-197` |
| Sync logic | `src/autodbaudit/application/sync_service.py` |
| Excel sheet modules | `src/autodbaudit/infrastructure/excel/*.py` |
| SQL queries | `src/autodbaudit/infrastructure/sql/query_provider.py` |
| SQLite schema | `src/autodbaudit/infrastructure/sqlite/schema.py` |

---

*Last updated: 2025-12-17*
