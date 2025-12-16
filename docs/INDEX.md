# Documentation Index

> **Last Updated**: 2025-12-11  
> **Single source of truth** for AutoDBAudit project documentation.

This folder contains all project documentation. README.md stays in the root as required.

---

## Current Documentation

### Core Reference
| File | Purpose | Audience |
|------|---------|----------|
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | Current implementation state, what works, what doesn't | Everyone |
| [TODO.md](TODO.md) | Task tracker and priorities | Developers |
| [AI_RUNBOOK.md](AI_RUNBOOK.md) | Quick reference for AI assistants | AI agents |
| [SESSION_HANDOFF_DEV_SWITCH.md](SESSION_HANDOFF_DEV_SWITCH.md) | **Critical Handoff Guide** (Read first on new machine) | Developers |

### Workflow & Usage
| File | Purpose | Audience |
|------|---------|----------|
| [AUDIT_WORKFLOW.md](AUDIT_WORKFLOW.md) | Complete audit lifecycle design | Operators, Developers |
| [CLI_REFERENCE.md](CLI_REFERENCE.md) | CLI command documentation | Operators |

### Technical Reference
| File | Purpose | Audience |
|------|---------|----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Codebase architecture with diagrams | Developers |
| [SCHEMA_REFERENCE.md](SCHEMA_REFERENCE.md) | SQLite schema documentation | Developers |
| [SCHEMA_ALIGNMENT_ANALYSIS.md](SCHEMA_ALIGNMENT_ANALYSIS.md) | Schema mismatch analysis and fixes | Developers |
| [EXCEL_REPORT_LAYOUT.md](EXCEL_REPORT_LAYOUT.md) | Excel sheet structure (General) | Developers |
| [EXCEL_COLUMNS.md](EXCEL_COLUMNS.md) | **Strict Schema** & Column Definitions | Developers |
| [HOTFIX_ORCHESTRATION.md](HOTFIX_ORCHESTRATION.md) | Hotfix deployment design (pending) | Developers |

### Archive
| Folder | Purpose |
|--------|---------|
| [archive/](archive/) | Historical planning docs, chat transcripts, outdated designs |

---

## Key Files Outside `/docs`

| File | Location | Purpose |
|------|----------|---------|
| `README.md` | Root | Quick start, project overview |
| `db-requirements.md` | Root | **28 security requirements (source of truth)** |
| `config/sql_targets.json` | `config/` | Target server configuration |
| `config/audit_config.json` | `config/` | Audit thresholds and settings |

---

## Naming Conventions

- **UPPERCASE.md** - Active documentation
- **archive/** - Historical documents, not current

---

## Keeping Docs Updated

| Document | When to Update |
|----------|----------------|
| `PROJECT_STATUS.md` | After any feature completion or major status change |
| `TODO.md` | When adding or completing tasks |
| `AI_RUNBOOK.md` | When architecture or key decisions change |
| `CLI_REFERENCE.md` | When CLI commands are added/modified |
| Other docs | When the relevant feature changes |

---

*Keep this index updated when adding or removing documentation.*
