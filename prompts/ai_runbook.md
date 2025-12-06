# AI Runbook – AutoDBAudit

> **For AI assistants**: Quick reference to work on this repo without rediscovering context.

---

## Project Summary

**AutoDBAudit** is a self-contained, offline-capable SQL Server audit and remediation tool. It audits instances against 22+ security requirements, generates Excel reports, suggests T-SQL fixes, tracks actions/exceptions in SQLite, and orchestrates hotfix deployments across remote servers.

---

## Key Architectural Invariants

| Invariant | Detail |
|-----------|--------|
| **Layered structure** | `src/autodbaudit/{domain, application, infrastructure, interface, hotfix}` |
| **SQLite is canonical** | `output/history.db`; Excel is generated from it |
| **No ORM** | Use `sqlite3` with explicit SQL |
| **Excel via openpyxl** | No other Excel libraries |
| **Offline-first** | Must work on air-gapped Windows machines |
| **SQL 2008 R2 → 2022+** | Versioned queries in `queries/{sql2008,sql2019plus}/` |

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
| 1 | Code refactor into layers | 🔄 In progress |
| 2 | Domain models + SQLite store | ⏳ Pending |
| 3 | Excel reporting | ⏳ Pending |
| 4 | Real audit logic | ⏳ Pending |
| 5 | Hotfix orchestrator | ⏳ Pending |
| 6 | Remediation scripts | ⏳ Pending |
| 7 | CLI polish | ⏳ Pending |

---

## Key Files to Read First

| File | Purpose |
|------|---------|
| [`prompts/RjInit-PromptChain/init/architecture_snapshot.md`](RjInit-PromptChain/init/architecture_snapshot.md) | Concise architecture reference |
| [`prompts/RjInit-PromptChain/init/Project_Overview.md`](RjInit-PromptChain/init/Project_Overview.md) | Full project spec |
| [`prompts/RjInit-PromptChain/init/implementation_plan.md`](RjInit-PromptChain/init/implementation_plan.md) | Detailed phases & design |
| [`docs/sqlite_schema.md`](../docs/sqlite_schema.md) | Database schema |
| [`docs/excel_report_layout.md`](../docs/excel_report_layout.md) | Report structure |
| [`db-requirements.md`](../db-requirements.md) | 22 audit requirements |

---

## Quick Commands

```bash
# Activate venv
.\venv\Scripts\activate

# Install deps
pip install -r requirements.txt

# Run CLI (stub)
python main.py --audit --config config/audit_config.json --targets config/sql_targets.json

# Test imports
python test_setup.py
```

---

## Don't Waste Time On

- Excel/SQLite are stubs (Phase 2-3)
- Hotfix remote execution not built (Phase 5)
- Remediation scripts not built (Phase 6)

Focus on the current phase and extend incrementally.

---

*Last updated: 2025-12-06*
