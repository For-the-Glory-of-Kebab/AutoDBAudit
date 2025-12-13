# Project Status

> **Last Updated**: 2025-12-12 (Gap Analysis Complete)

## Overview

**AutoDBAudit** is a SQL Server Security Audit Tool designed so that a person with ZERO SQL experience can conduct audits, fix issues, and deliver compliance results.

---

## Current Architecture Decisions

### 1. Database Model: "Results-Based Persistence"
Our SQLite database currently focuses on **Compliance Results** (`findings` table) rather than **Raw Inventory** (`logins` table).
-   **Findings Table**: The "Source of Truth" for valid/invalid checks. Populated by the Python engine.
-   **Inventory Tables** (`logins`, `server_info`, etc.): Exists in schema (V2) but currently **UNUSED (Empty)**.
    -   *Decision*: We are proceeding with E2E testing using `findings` as the primary data source. Populating raw inventory is a future enhancement.

### 2. Audit Run Types
We use a **Single Table Inheritance** model in `audit_runs`:
-   `run_type='audit'`: Baseline / Full Audit.
-   `run_type='sync'`: Verification Run (Child of an Audit).
-   **Linking**: The `action_log` table links Sync events back to the original Audit ID.

### 3. Gap Closure (Dec 2025)
-   **Permissions**: We now explicitly audit GRANT/DENY permissions (Req #28).
-   **Security Matrix**: We now generate a visual Role Matrix (Req #27).

### 4. Action Sheet Strategy: "Deep Audit Trail"
The Action Sheet is strictly a **Diff Log**.
-   **Change Tracking**: Only lists items when their status changes (Fail->Fixed, Pass->Fail).
-   **Date Persistence**: DB holds "First Detected" date. Excel manual edits (Notes, dates) override DB on Sync.
-   **Goal**: Provide a permanent history of remediation efforts, not just a current "To-Do" snapshot.

---

## Implementation State

### ✅ Fully Working Commands

| Command | Status | Notes |
|---------|--------|-------|
| `--audit --new --name "..."` | ✅ **Working** | Creates new audit (Baseline) |
| `--audit` | ✅ **Working** | Continues latest audit |
| `--generate-remediation` | ✅ **Working** | Generates scripts with Icons & Headers |
| `--sync` | ✅ **Working** | Progress tracking, Timestamps, & Version Drift Detection |
| `--finalize` | ✅ **Ready for Test** | Persists final state |
| `--apply-exceptions` | ✅ **Working** | Reads Excel notes to SQLite |
| `--status` | ✅ **Working** | Dashboard |

### ⏳ Future / Planned

| Command | Status | Notes |
|---------|--------|-------|
| `--deploy-hotfixes` | ⏳ **Stub only** | NotImplementedError |
| `Inventory Population`| ⏳ **Planned** | Populating `logins`, `server_info` tables |

---

## E2E Testing Workflow

We have defined a "0 to 100" Manual E2E Test (See `docs/E2E_TESTING_GUIDE.md`):
1.  **Baseline Audit**: Establish initial state (`ids 1-100`).
2.  **Simulate Updates**: Downgrade DB version record to test "Upgrade Detection".
3.  **Remediate**: Apply fixes (Simulated or Real).
4.  **Sync**: Verify fixes and version changes.
5.  **Finalize**: Close the loop.

---

## Directory Structure & Key Files

```
AutoDBAudit/
├── main.py                          # Entry point
├── config/                          # Configuration
│   └── sql_targets.json             # Target instances
├── output/                          # Generated outputs
│   ├── audit_report_latest.xlsx     # ✅ The "Working Copy" for Excel Notes
│   ├── audit_history.db             # ✅ SQLite Source of Truth
│   └── remediation_scripts/         # Generated TSQL
├── src/autodbaudit/
│   ├── infrastructure/sqlite/
│   │   ├── schema.py                # Schema V2 (Inventory + Findings)
│   │   └── store.py                 # Schema V1 (Core Tables)
│   └── application/
│       ├── sync_service.py          # Diffing Logic
│       └── remediation_service.py   # Script Generation
└── docs/
    ├── PROJECT_STATUS.md            # This file
    ├── E2E_TESTING_GUIDE.md         # 🧪 Manual Testing Cheatsheet
    └── ...
```

---

## Known Issues / Tasks (Phase 4)

1.  **Excel Lifecycle**: Need to clarify if we keep one "Working Copy" vs snapshotting every Sync. currently overrides `audit_report_latest.xlsx`.
2.  **Unjustified Items**: Excel needs better highlighting for items with NO Fix and NO Note.
3.  **Reversion Logic**: Handling cases where a Fixed item breaks again (Pass -> Fail).

## Completed Phases (Session 8)

### Phase 8: User Requests (Refinement)
-   ✅ **Feature**: Implemented `--aggressiveness` levels for remediation Scripts
    -   Level 1 (Default): Commented checks (Safe)
    -   Level 2 (Constructive): Uncomment privilege revocation
    -   Level 3 (Brutal): Uncomment disable/drop (except self-lockout)
-   ✅ **CLI**: Added `--aggressiveness` flag
-   ✅ **Safety**: Implemented Universal Lockout Prevention for connecting user

### Phase 9: Debugging & Stabilization
-   ✅ **Fix**: SA Account Remediation missing on SQL 2008 (Fixed via `principal_id` check)
-   ✅ **Verified**: "DEFAULT" Instance Names confirmed correct in DB/Config
-   ✅ **Hotfix**: SQL 2008 Transaction Errors (Enabled `autocommit`)

### Phase 10: Precision & Audit Trail (Dec 13)
-   ✅ **Instance Identification**: Resolved "Default Instance" ambiguity using explicit Port targeting (e.g., `(Default:1434)`).
-   ✅ **Late Arrival**: Sync now correctly identifies and logs servers that come online after the baseline.
-   ✅ **Action Sheet Logic**: Refactored to "Audit Trail" mode (History-based, Manual Edit Preservation).
-   ✅ **Config Remediation**: Fixed "Remote Access" script to properly cleanly toggle configurations.

---

*Document Version: 2.1 | E2E Phase Update*
