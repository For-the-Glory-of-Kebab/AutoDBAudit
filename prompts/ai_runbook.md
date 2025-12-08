# AI Runbook – AutoDBAudit

> **For AI assistants**: Quick reference to work on this repo without rediscovering context.

---

## Project Summary

**AutoDBAudit** is a self-contained, offline-capable SQL Server audit and remediation tool. It audits instances against 28+ security requirements, generates Excel reports with dropdown validation, suggests T-SQL fixes, tracks actions/exceptions in SQLite, and orchestrates hotfix deployments across remote servers.

---

## Key Architectural Invariants

| Invariant | Detail |
|-----------|--------|
| **Layered structure** | `src/autodbaudit/{domain, application, infrastructure, interface, hotfix}` |
| **SQLite is canonical** | `output/history.db`; Excel is generated from it |
| **No ORM** | Use `sqlite3` with explicit SQL |
| **Excel via openpyxl** | No other Excel libraries |
| **Offline-first** | Must work on air-gapped Windows machines |
| **SQL 2008 R2 → 2022+** | Versioned queries via `query_provider.py` |

---

## Hard Rules for Agents

1. **Do NOT modify** `1-Report-and-Setup/` — legacy PowerShell reference only
2. **Do NOT change** `db-requirements.md` semantics without explicit instruction
3. **Extend** the layered package structure; never reintroduce flat `core/` or `utils/`
4. **Use** SQLite + openpyxl; no ORM or alternate Excel engine
5. **Keep domain layer pure** — no file/network I/O there

---

## Phase Map

| Phase | Goal | Status |
|-------|------|--------|
| 0 | Docs & prompts aligned | ✅ Done |
| 1 | Code refactor into layers | ✅ Done |
| 2 | Domain models + SQLite store | ✅ Done (schema) |
| 3 | Excel reporting | ✅ Done (16 sheets, dropdowns, grouping) |
| 4 | CLI integration | 🔄 In progress |
| 5 | Hotfix orchestrator | ⏳ Pending |
| 6 | Remediation scripts | ⏳ Pending |
| 7 | CLI polish | ⏳ Pending |

---

## Key Files to Read First

| File | Purpose |
|------|---------|
| [`docs/excel_report_layout.md`](../docs/excel_report_layout.md) | **Complete** Excel sheet documentation |
| [`docs/PROJECT_STATUS.md`](../docs/PROJECT_STATUS.md) | Current implementation status |
| [`docs/sqlite_schema.md`](../docs/sqlite_schema.md) | Database schema |
| [`db-requirements.md`](../db-requirements.md) | 28 audit requirements |
| [`docs/TODO.md`](../docs/TODO.md) | Task tracker |

---

## Quick Commands

```bash
# Activate venv
.\venv\Scripts\activate

# Install deps
pip install -r requirements.txt

# Test multi-instance Excel generation
$env:PYTHONPATH="d:\Raja-Initiative\src"
python test_multi_instance.py

# Test imports
python test_setup.py
```

---

## What's Working Now

- ✅ **Excel Package** - 20 modular files in `infrastructure/excel/`
- ✅ **16 Sheets** - All with headers, conditional formatting, dropdowns
- ✅ **Query Provider** - SQL 2008-2022+ compatible
- ✅ **SqlConnector** - Version detection, auth handling
- ✅ **Server/Instance Grouping** - Color rotation, merged cells

## What's Still Stub/Pending

- ⏳ SQLite history store not integrated in audit flow
- ⏳ CLI doesn't use new ExcelReportWriter yet
- ⏳ Hotfix remote execution not built
- ⏳ Remediation scripts not built

Focus on CLI integration next.

---

*Last updated: 2025-12-08*
