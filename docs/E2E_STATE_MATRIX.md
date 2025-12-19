# E2E Test State Matrix

> **Date**: 2025-12-19 (Updated)  
> **Purpose**: Source of truth for exception/sync state transitions  
> **Synced from**: artifacts/implementation_plan.md

---

## Core Rule: Centralized Exception Logic

> [!IMPORTANT]
> All exception determination MUST use a **single source of truth**.
> - Logging to Action Sheet
> - CLI stats display
> - Excel document generation
> - Status indicator updates
> 
> **All use the same module** (`domain/state_machine.py` + `application/stats_service.py`)

---

## Exception Definition (CANONICAL)

A row is **exceptioned** if and only if:

```
is_exception = is_discrepant(status) AND (
    has_justification OR 
    review_status == "Exception"
)
```

Where:
- `is_discrepant(status)` = status in ("FAIL", "WARN")
- `has_justification` = justification field is non-empty after trim

---

## Status Auto-Population Rule

| Row Status | User Action | System Behavior |
|------------|-------------|-----------------|
| FAIL/WARN | User adds justification only | Auto-set status to "Exception" on next sync |
| FAIL/WARN | User sets "Exception" dropdown | Keep as is |
| PASS | User adds justification | **Keep as note** (no status change) |
| PASS | User sets "Exception" dropdown | **Silently ignore** (no false "removed" log!) |

> [!CAUTION]
> Do **NOT** clear status on PASS rows that have "Exception" dropdown!
> Simply ignore it during document generation. Clearing would cause false "EXCEPTION_REMOVED" logs.

---

## What Happens on Document Regeneration

When we generate the next Excel document:

| Current DB Status | Has Justification | Review Status in DB | Output to Excel |
|-------------------|-------------------|---------------------|-----------------|
| FAIL | Yes | - | Status="Exception", ✓ indicator |
| FAIL | Yes | "Exception" | Status="Exception", ✓ indicator |
| FAIL | No | "Exception" | Status="Exception", ✓ indicator |
| FAIL | No | - | Status="", ⏳ indicator |
| PASS | Yes | - | Note kept, no status, no indicator |
| PASS | Any | "Exception" | **Ignore exception status**, keep note if any |

---

## All Sync-to-Sync Transitions

| # | Previous State | Current State | Result | Log? |
|---|----------------|---------------|--------|------|
| 1 | FAIL (no doc) | PASS | FIXED | ✅ |
| 2 | FAIL + Exception | PASS | FIXED (exception becomes history) | ✅ |
| 3 | PASS | FAIL | REGRESSION | ✅ |
| 4 | PASS + Note | FAIL | REGRESSION + auto-exception! | ✅ |
| 5 | (new row) | FAIL | NEW_ISSUE | ✅ |
| 6 | FAIL | FAIL | STILL_FAILING | ❌ |
| 7 | FAIL | FAIL + Justification | EXCEPTION_ADDED | ✅ |
| 8 | FAIL + Exception | FAIL (user cleared BOTH) | EXCEPTION_REMOVED | ✅ |
| 9 | FAIL + Exception | FAIL + Exception | NO_CHANGE | ❌ |
| 10 | FAIL + Exception | FAIL (edit text) | EXCEPTION_UPDATED | ⚠️ |

---

## What Does NOT Trigger "Exception Removed"

> [!WARNING]
> These should **NEVER** log "Exception Removed"

1. ❌ PASS row with "Exception" dropdown → just ignore (never was valid exception)
2. ❌ Exception row becomes PASS → that's FIXED (exception docs become historical)
3. ❌ PASS row had justification → stays PASS → just a note
4. ❌ User adds exception dropdown to PASS row → ignore on regeneration

Only trigger "Exception Removed" when:
- Row is **still FAIL/WARN**, AND
- User **explicitly cleared BOTH** justification AND status

---

## Field Resilience

| Field | Bad Input Example | Action |
|-------|-------------------|--------|
| Date | "not a date", empty | Keep original, log warning |
| Review Status | Invalid value | Ignore, log warning |
| Justification | " " (whitespace only) | Treat as empty |
| Notes | Any value | Preserve |
| Purpose | Any value | Preserve |

---

## Centralized Implementation Location

```
src/autodbaudit/
├── domain/
│   ├── change_types.py      # Enums (FindingStatus, ChangeType)
│   └── state_machine.py     # is_exception_eligible(), classify_transition()
├── application/
│   ├── stats_service.py     # count_exceptions(), calculate_stats()
│   └── diff/
│       └── findings_diff.py # Diff logic using state_machine.py
```

**Rule**: Never inline exception logic. Always call state_machine functions.

---

## 12 E2E Test Scenarios

| # | Scenario | Expected |
|---|----------|----------|
| 01 | FAIL + add justification | EXCEPTION_ADDED, status auto-set |
| 02 | PASS + add justification | Note only (no exception, no status) |
| 03 | PASS + Exception dropdown | **Ignored** (no exception, no "removed" log) |
| 04 | FAIL + Exception → sync again | NO duplicate log |
| 05 | FAIL + Exception → PASS | FIXED (exception becomes history) |
| 06 | PASS → FAIL | REGRESSION |
| 07 | PASS + note → FAIL | REGRESSION + auto-exception! |
| 08 | FAIL + Exception → clear both | EXCEPTION_REMOVED |
| 09 | FAIL + Exception → still FAIL | No change |
| 10 | Any + bad date | Original kept, warning logged |
| 11 | Sync 3× | Counts stable, no duplicates |
| 12 | Edit justification text | EXCEPTION_UPDATED (not new) |

---

*This document is the canonical reference for E2E testing implementation.*
