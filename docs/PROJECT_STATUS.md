# Project Status

> **Last Updated**: 2025-12-14 (Health Audit)

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
| `--finalize` | ✅ **Implemented** (Dec 14) | Archives report, locks state, syncs annotations |
| `--finalize-status` | ✅ **Implemented** | Pre-flight checks |
| `--apply-exceptions` | ✅ **Working** | Reads Excel notes to SQLite |
| `--status` | ✅ **Working** | Dashboard |

### ⏳ Future / Planned

| Command | Status | Notes |
|---------|--------|-------|
| `--deploy-hotfixes` | ⏳ **Stub only** | NotImplementedError (entire module) |
| `Inventory Population`| ⏳ **Planned** | Populating `logins`, `server_info` tables |

---

## 🔴 Known Dead Code

> **Action Required**: Archive or delete before production

| File/Module | Lines | Status | Notes |
|-------------|-------|--------|-------|
| `application/history_service.py` | 175 | 100% DEAD | All methods `NotImplementedError` |
| `hotfix/` (5 files) | ~400 | 100% STUB | Designed but never implemented |

---

## Completed Phases

### Phase 18: Exception Logic & Role Matrix Fix (Dec 14)
-   ✅ **Database Roles Deduplication**: `seen_memberships` set prevents duplicate entries
-   ✅ **Exception Logic Refinement**: Only log exceptions for FAIL items (⏳ indicator)
-   ✅ **Role Matrix Per-Database**: Reverted to per-database design for audit compliance
-   ✅ **Actions Sheet Cleanup**: Removed unnecessary "Assigned To" column

### Phase 17: Remediation Script Audit Settings Fix (Dec 14)
-   ✅ **Login Auditing Fix**: Script was commented out - now generates properly
-   ✅ **has_audit_finding Flag**: Detects audit_settings findings
-   ✅ **Rollback Method**: Added `_rollback_disable_login_auditing()`

### Phase 16: Exception Logging & Visual Indicators (Dec 14)
-   ✅ **ACTION_COLUMN**: Added ⏳ indicator to all discrepancy sheets
-   ✅ **Exception-to-Action Logging**: Justifications logged as "Exception Documented"
-   ✅ **Visual Indicator Change**: ⏳→✅ when justification added during sync
-   ✅ **Fonts.INFO**: Added blue info styling for documented exceptions

### Phase 15: Actions Sheet as Changelog (Dec 14)
-   ✅ **Change Tracking**: Actions sheet now tracks CHANGES (Fixed/Regressed/New)
-   ✅ **Date Persistence**: Detected Date preserved across syncs

### Phase 14: Sheet Column Standardization (Dec 14)
-   ✅ **Discrepancy Sheets**: Justification + Notes columns
-   ✅ **Info-Only Sheets**: Notes column only

### Phase 13: Annotation Sync (Dec 14)
-   ✅ **Bidirectional Sync**: Excel ↔ SQLite annotations
-   ✅ **Stable Entity Keys**: Reliable round-trip syncing

### Phase 12: Finalization & Sync Hardening (Dec 14)
-   ✅ **FinalizeService**: Created robust finalize workflow
-   ✅ **Sync Hardening**: Blocks sync on finalized runs
-   ✅ **--finalize-status**: Pre-flight readiness check
-   ✅ **--force**: Bypass flag for open findings
-   ✅ **Annotation Sync**: Finalize imports Excel annotations to DB

### Phase 11: E2E Validation (Dec 14)
-   ✅ **Simulation Runner**: `run_simulation.py` with apply/revert modes
-   ✅ **Version Detection**: Auto-selects 2008 vs 2019+ scripts
-   ✅ **Interactive Mode**: Target selection with formatted display

### Phase 10: Precision & Audit Trail (Dec 13)
-   ✅ **Instance Identification**: Resolved "Default Instance" ambiguity using explicit Port targeting (e.g., `(Default:1434)`).
-   ✅ **Late Arrival**: Sync now correctly identifies and logs servers that come online after the baseline.
-   ✅ **Action Sheet Logic**: Refactored to "Audit Trail" mode (History-based, Manual Edit Preservation).
-   ✅ **Config Remediation**: Fixed "Remote Access" script to properly cleanly toggle configurations.

### Phase 9: Debugging & Stabilization
-   ✅ **Fix**: SA Account Remediation missing on SQL 2008 (Fixed via `principal_id` check)
-   ✅ **Verified**: "DEFAULT" Instance Names confirmed correct in DB/Config
-   ✅ **Hotfix**: SQL 2008 Transaction Errors (Enabled `autocommit`)

### Phase 8: User Requests (Refinement)
-   ✅ **Feature**: Implemented `--aggressiveness` levels for remediation Scripts
    -   Level 1 (Default): Commented checks (Safe)
    -   Level 2 (Constructive): Uncomment privilege revocation
    -   Level 3 (Brutal): Uncomment disable/drop (except self-lockout)
-   ✅ **CLI**: Added `--aggressiveness` flag
-   ✅ **Safety**: Implemented Universal Lockout Prevention for connecting user

---

*Document Version: 4.0 | Phases 16-18 Update*


