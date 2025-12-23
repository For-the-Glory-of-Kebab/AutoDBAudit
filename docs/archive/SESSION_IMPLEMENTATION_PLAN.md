# Test Readiness Implementation Plan

## Problem Statement

The user's main objective is to ensure the project is fully validated and ready for final delivery. Key issues identified:

1. **Test Infrastructure Issues** - E2E tests failing due to test harness bugs, not product bugs
2. **Key Format Reliability Concerns** - entity_key-based matching vs stable UUID tracking
3. **pain.txt/pain2.txt Issues** - Critical P0 items needing remediation
4. **Venv Activation** - Must be verified for pyinstaller compatibility

---

## Current Architecture Analysis

### Two Parallel Annotation Tracking Systems

The codebase has **two annotation tracking systems** that are NOT fully integrated:

#### 1. Legacy System (`annotations` table - Schema v2)
```sql
-- Uses composite key: entity_type|entity_key
UNIQUE(entity_type, entity_key, field_name)
```

**Used by:** `annotation_sync.py` (current sync engine)

**Risk:** Entity keys are built from column data like `server|instance|login_name`. If data changes (e.g., server renamed), the key changes and annotations are orphaned.

#### 2. New System (`row_annotations` table - Schema v3)
```sql
-- Uses stable UUID from hidden Excel Column A
row_uuid TEXT UNIQUE NOT NULL
```

**Infrastructure exists:**
- [row_uuid_schema.py](file:///c:/Users/sickp/source/SQLAuditProject/AutoDBAudit/src/autodbaudit/infrastructure/sqlite/row_uuid_schema.py): `upsert_row_annotation()`, `get_row_annotation()`, etc.
- [row_uuid.py](file:///c:/Users/sickp/source/SQLAuditProject/AutoDBAudit/src/autodbaudit/infrastructure/excel/row_uuid.py): Excel UUID column utilities

**Status:** Infrastructure exists but **NOT integrated into main sync flow**. `annotation_sync.py` still uses entity_key matching.

> [!CAUTION]
> **The UUID-based system is not wired up to the sync engine!** This is a critical gap that could cause annotation loss if data changes.

---

## Key Questions for User

Before proceeding, I need clarification on these architectural decisions:

1. **UUID Migration Status** - The UUID infrastructure exists but isn't used by `annotation_sync.py`. Was this intentional (staged rollout) or incomplete work?

2. **Priority Decision** - Given time constraints, should I:
   - A) Wire up UUID-based tracking properly (more reliable but ~4-6 hours)
   - B) Fix test infrastructure to validate current entity_key system (~2-3 hours)
   - C) Focus on pain.txt P0 remediations first (~2-3 hours)

3. **Test Coverage Strategy** - The failing E2E tests in `test_state_transitions.py` test exception detection via `detect_exception_changes()`. The tests themselves have bugs:
   - Sample data creates PASS rows, but tests expect FAIL behavior
   - Column name mismatches (Justification vs Exception Reason)
   
   Should I fix the tests, or should I trust that the product works (based on manual testing) and document the test gaps?

---

## Venv Verification

### Current Status ✅
[run_pytest.ps1](file:///c:/Users/sickp/source/SQLAuditProject/AutoDBAudit/scripts/run_pytest.ps1) correctly activates venv:
```powershell
& "$PSScriptRoot\..\venv\Scripts\Activate.ps1"
pytest $TestPath $ExtraArgs
```

The script activates venv before running pytest. This is correct.

---

## Proposed Phases

### Phase 1: Verify and Document Current State
- [x] Verify venv activation is correct
- [ ] Document UUID vs entity_key architecture gap
- [ ] Sync docs folder with current findings

### Phase 2: Fix Test Infrastructure (If Approved)
- [ ] Fix conftest.py entity_key format in mock findings
- [ ] Add proper FAIL status to sample data or mark_row_as_fail helper
- [ ] Fix column name mismatches in test specs

### Phase 3: Address pain.txt P0 Items
Per [tests/pain.txt](file:///c:/Users/sickp/source/SQLAuditProject/AutoDBAudit/tests/pain.txt):
- [ ] Fix `--apply-remediation` default paths
- [ ] Fix SA Account remediation (renaming/disabling)
- [ ] Fix Login Audit remediation scripts
- [ ] Review aggressiveness levels

### Phase 4: UUID System Integration (If Approved)
- [ ] Update `annotation_sync.py` to use UUID-based tracking
- [ ] Migrate from `annotations` table to `row_annotations` table
- [ ] Update tests to verify UUID-based matching

---

## Verification Plan

### Existing Tests
Located in `tests/ultimate_e2e/`:
- `test_persistence.py` - Annotation roundtrip (55 pass after fix)
- `test_state_transitions.py` - Exception detection (15 failing - test bugs)
- `test_per_sheet.py` - Per-sheet validation

### Run Command
```powershell
.\scripts\run_pytest.ps1 tests\ultimate_e2e\ -v
```

### Manual Verification (pain.txt items)
1. Run full audit: `python -m autodbaudit --audit config/demo.toml`
2. Add annotations to Excel
3. Run sync: `python -m autodbaudit --sync runs/<latest>/`
4. Verify CLI stats match reality
5. Verify Action Log sheet populated correctly

---

## Immediate Next Steps

Waiting for user decision on:
1. UUID integration priority
2. Test fixing vs product fixing priority
3. Manual testing approval for pain.txt items
