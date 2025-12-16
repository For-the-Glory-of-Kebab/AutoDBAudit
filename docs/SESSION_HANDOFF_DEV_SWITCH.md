# Session Handoff: Development Machine Switch

> **Date**: 2025-12-16
> **From**: Current Dev Session
> **To**: Fresh Machine (Tomorrow)

## 🚨 Immediate Action Required

If you have just pulled this repo on a new machine, **follow these steps strictly in order**.

---

## 1. Environment Setup

The project uses a standard Python virtual environment.

```powershell
# 1. Clone/Navigate to repo
cd c:\path\to\AutoDBAudit

# 2. Run Setup Script (Creates venv, installs dependencies)
#    This script handles strict dependency pinning.
.\setup_dev.ps1

# 3. Activate
.\venv\Scripts\Activate.ps1
```

## 2. Verification (Sanity Check)

Before doing any work, verify the "Golden State" left by the previous session.

```powershell
# 1. Run the build/verify script
#    This runs unit tests, linting, and a dry-run of the CLI
python tools/verify_refactor.py

# 2. Check the Status Dashboard
python src/main.py --status
```

**Expected Result**:
- `verify_refactor.py`: ✅ All checks pass.
- `--status`: Should show the last audit run (Run #2) from the previous machine as "Completed".

---

## 3. Project Context (Read This!)

We have just completed a massive **Modular Refactoring** and **E2E Regression Fix**.

### What changed?
1.  **Entry Point**: `main.py` is now in `src/main.py`. Do not look for it in root.
2.  **Collectors**: Monolithic `data_collector.py` is GONE. Logic is split into `src/autodbaudit/application/collectors/`.
3.  **Remediation**: `RemediationService` is refactored into `src/autodbaudit/application/remediation/`.
4.  **Excel Sheets**: We just fixed several empty sheets (Role Matrix, Permissions, Encryption). If you run an audit and see empty sheets, **something is broken**.

### The "Results-Based Persistence" Model
- **Findings Table**: The source of truth.
- **Inventory Tables** (`logins`, etc.): **EMPTY by design**. Do not panic if `SELECT * FROM logins` returns 0 rows. We only store *findings* right now.

---

## 4. Next Steps (The Backlog)

You are ready to pick up the **Long Running Job** mentioned by the user.

1.  **Inventory Population**: The raw inventory tables are empty. The user may want to start populating them for "Asset Management" features.
2.  **Hotfix Deployment**: The `--deploy-hotfixes` command is a stub. This is a likely candidate for the next major feature.

---

## 5. Documentation Map

- **Strict Schema**: [`docs/EXCEL_COLUMNS.md`](docs/EXCEL_COLUMNS.md) (Use this if modifying Excel reports)
- **Architecture**: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- **Status**: [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)

---

**System State**: CLEAN.
**Build Status**: PASSING.
**E2E Test**: PASSED (All sheets populated).
