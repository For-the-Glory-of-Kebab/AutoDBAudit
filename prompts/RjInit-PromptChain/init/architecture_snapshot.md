# AutoDBAudit – Architecture Snapshot

> **Quick reference for humans and AI agents resuming work on this project.**

---

## What AutoDBAudit Does

A self-contained, offline-capable SQL Server audit and remediation tool:

1. **Audit** SQL instances (2008 R2 → 2022+) against 22+ security requirements
2. **Generate** professional Excel reports with trends, exceptions, action logs
3. **Suggest** T-SQL remediation scripts (user reviews/uncomments before applying)
4. **Track** actions and exceptions in persistent SQLite history
5. **Orchestrate** SQL Server hotfix/CU deployments across many servers remotely

---

## Package Layout (`src/autodbaudit/`)

```
autodbaudit/
├── domain/          # Requirement metadata, result models, exceptions, actions
├── application/     # Audit service, remediation generator, history service, hotfix orchestrator
├── infrastructure/  # pyodbc connector, versioned query loader, sqlite store, openpyxl writer, remote exec
├── interface/       # CLI (argparse → later Typer/Rich)
└── hotfix/          # Hotfix planner, executor, resume logic
```

| Layer           | Responsibility |
|-----------------|----------------|
| **domain**      | Pure data models & business rules; no I/O |
| **infrastructure** | All external I/O: SQL, files, Excel, remote commands |
| **application** | Use-case orchestration; calls domain + infra |
| **interface**   | CLI parsing, user prompts, entry points |
| **hotfix**      | Specialised orchestrator for patching SQL Servers remotely |

---

## Key Technology Choices

| Concern | Choice | Notes |
|---------|--------|-------|
| SQL connectivity | `pyodbc` | Supports all SQL Server versions via ODBC drivers |
| History store | `sqlite3` (stdlib) | No ORM; explicit SQL for simplicity |
| Excel reports | `openpyxl` | Pure Python; styling, charts, conditional formatting |
| Credentials | Windows DPAPI (`pywin32`) | User-scoped encryption; offline-safe |
| Deployment | PyInstaller `--onefile` | Single exe + bundled queries/config |

---

## Important Invariants

- **`db-requirements.md`** is the source-of-truth for audit rules.
- **`1-Report-and-Setup/`** is legacy PowerShell reference—read-only, do not modify.
- **Versioned queries** live in `queries/{sql2008,sql2019plus}/`; tool auto-selects by detected version.
- **SQLite DB** (`output/history.db`) is the canonical store; Excel is generated *from* it.
- **Hotfix orchestrator** runs installers on *remote* servers via PowerShell Remoting, not just locally.

---

## Guidelines for Future Agents

1. **Extend the layered structure** (`domain`, `application`, `infrastructure`, `interface`, `hotfix`).  
   Do **not** reintroduce flat `core/` or `utils/` modules.
2. **Keep domain layer pure**—no file/network I/O there.
3. **Prefer explicit over magic**: stdlib `sqlite3` over ORMs; straightforward argparse over heavy frameworks (until Phase 7).
4. **Do not change requirement semantics** in `db-requirements.md` without explicit user instruction.
5. **Treat this document as authoritative** when in doubt; older prompts (1-init.txt, etc.) are historical context only.

---

## Phase Roadmap (High-Level)

| Phase | Goal |
|-------|------|
| 0 | Docs & prompts aligned (this file) |
| 1 | Refactor code into `autodbaudit` layered structure |
| 2 | Domain models + SQLite history store |
| 3 | Excel reporting via openpyxl |
| 4 | Real audit logic with versioned queries |
| 5 | Hotfix planner + remote executor |
| 6 | Remediation script generation |
| 7 | CLI polish (Typer/Rich) |

---

*Last updated: 2025-12-06*
