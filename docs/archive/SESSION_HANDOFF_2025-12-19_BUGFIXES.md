# Sync Engine Bug Fixes - Session 2025-12-19

> **Status**: ✅ All 58 Tests Pass

---

## Summary

Fixed 4 critical bugs causing sync engine failures:

| # | Bug | Root Cause | Fix |
|---|-----|------------|-----|
| 1 | Exception count → 0 | Key mismatch (annotations vs findings) | Try all type prefixes in lookup |
| 2 | Action logs stop | `status_mismatch` always true | Removed buggy check |
| 3 | Audit Settings broken | Column name mismatch | Fixed column mapping |
| 4 | Missing entity types | KNOWN_TYPES incomplete | Added db_role, permission, orphaned_user |

---

## Bug 1: Key Mismatch ✅

Annotations keyed as `type|SERVER|INSTANCE|name`, findings use `SERVER|INSTANCE|name`.

**Files**: [stats_service.py](file:///c:/Users/sickp/source/SQLAuditProject/AutoDBAudit/src/autodbaudit/application/stats_service.py), [findings_diff.py](file:///c:/Users/sickp/source/SQLAuditProject/AutoDBAudit/src/autodbaudit/application/diff/findings_diff.py)

---

## Bug 2: Duplicate Detection ✅

`status_mismatch` check caused re-detection every sync because finding status stays FAIL.

**File**: [annotation_sync.py](file:///c:/Users/sickp/source/SQLAuditProject/AutoDBAudit/src/autodbaudit/application/annotation_sync.py#L970-L988)

---

## Bug 3: Audit Settings ✅

Collector expected `AuditName`/`IsEnabled` but query returns `SettingName`/`CurrentValue`.

**File**: [security_policy.py](file:///c:/Users/sickp/source/SQLAuditProject/AutoDBAudit/src/autodbaudit/application/collectors/security_policy.py)

---

## Bug 4: Missing Entity Types ✅

KNOWN_TYPES was missing: `db_role`, `permission`, `orphaned_user`.

**Files**: stats_service.py, findings_diff.py

---

## New Test Coverage

| Test File | Tests | Coverage |
|-----------|-------|----------|
| test_multi_sync_stability.py | 6 | All entity types, count stability, no duplicates |
| test_comprehensive_e2e.py | 14 | 12 state transitions + edge cases |
| test_state_machine.py | 10 | State machine logic |
| Other tests | 28 | Sync logic, exception flow |
| **Total** | **58** | ✅ All pass |

---

## Wrapper Scripts Created

| Script | Purpose |
|--------|---------|
| `.scripts/pytest.ps1` | Run pytest without prompts |
| `.scripts/python.ps1` | Run Python via venv |
| `.scripts/clean.ps1` | Clean test workspace |
