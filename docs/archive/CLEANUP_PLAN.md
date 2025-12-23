# Codebase Cleanup & Consolidation Plan

## Critical Issues Identified

### 1. Dead/Legacy Code (IMMEDIATE DELETE)
| File | Lines | Status |
|------|-------|--------|
| `sync_service_legacy.py` | 718 | ❌ DEAD - not imported anywhere |
| `entity_diff.py` | 948 | ⚠️ Check imports before removing |

### 2. Large Files Needing Refactor (>500 lines)
| File | Lines | Action |
|------|-------|--------|
| `annotation_sync.py` | 1276 | 🔴 SPLIT: Extract detect_exception_changes, persist methods |
| `query_provider.py` | 1748 | Split by entity type or query category |
| `schema.py` | 1368 | Split into separate migration modules |
| `entity_diff.py` | 948 | Delete if dead, else refactor |
| `store.py` | 912 | Split persistence logic by domain |
| `stats_service.py` | 788 | Extract calculation helpers |

### 3. Docs Consolidation
**26 docs + 54 archived = chaos**

Archive these redundant docs:
- `E2E_STATE_MATRIX.md` → merge into `SYNC_ENGINE_ARCHITECTURE.md`
- `E2E_TESTING_GUIDE.md` → merge into `ULTIMATE_E2E_TEST.md`
- `E2E_TEST_STATUS.md` → archive (stale)
- `SESSION_IMPLEMENTATION_PLAN.md` → archive
- `SESSION_HANDOFF.md` → REWRITE with current state
- `SESSION_UUID_INTEGRATION.md` → merge into architecture

**Keep & Update:**
- `SYNC_ENGINE_ARCHITECTURE.md` - canonical sync logic doc
- `EXCEL_COLUMNS.md` - column definitions
- `ENTITY_KEY_FORMATS.md` - key format reference
- `ROW_UUID_DESIGN.md` - UUID design doc
- `CLI_REFERENCE.md` - CLI commands

### 4. Test Directory Cleanup
**6 subdirectories + 26 test files = overlapping chaos**

| Directory | Files | Action |
|-----------|-------|--------|
| `ultimate_e2e/` | 7 | ✅ KEEP - current test suite |
| `atomic_e2e/` | 29 | Review, merge into ultimate_e2e or delete |
| `e2e/` | 2 | Delete if superseded |
| `e2e_robust/` | 11 | Delete if superseded |
| `sheets/` | 2 | Delete if superseded |
| Root files | 26 | Archive ones not actively used |

### 5. Naming Inconsistencies
- `"status"` vs `"Exception Status"` vs `"Review Status"` - STANDARDIZE
- `"justification"` vs `"Exception Reason"` - already mapped, verify consistency
- `entity_key` format varies by context - document clearly

### 6. Crash Bug (FROM PREVIOUS SESSION)
**Test showed exception appended but test still fails**
```
DEBUG: Exception APPENDED: sa_account - E107AD81 - change=added
```
Root cause: Test filter checks for `"Documented"` or `"Added"` but code uses lowercase `"added"`.

---

## Execution Order

### Phase 1: Fix Crash Bug (5 min)
- [ ] Fix change_type case mismatch in detect_exception_changes

### Phase 2: Delete Dead Code (10 min)
- [ ] Delete `sync_service_legacy.py`
- [ ] Check `entity_diff.py` imports, delete if dead
- [ ] Remove any other unused modules

### Phase 3: Archive Stale Docs (15 min)  
- [ ] Move redundant docs to `docs/archive/`
- [ ] Rewrite `SESSION_HANDOFF.md` with accurate current state
- [ ] Consolidate E2E docs into single source of truth

### Phase 4: Cleanup Tests (20 min)
- [ ] Identify which test suites are canonical
- [ ] Archive deprecated test files
- [ ] Ensure `ultimate_e2e/` is the single E2E suite

### Phase 5: Refactor Large Files (LATER - with user approval)
- [ ] Split `annotation_sync.py` into modules
- [ ] Split `schema.py` into migration modules

---

## User Review Required

> [!IMPORTANT]
> Before Phase 4-5, confirm:
> 1. Which test suite should be canonical? (`ultimate_e2e/` seems newest)
> 2. Any archived docs you want preserved as-is?
> 3. Priority: Fix bugs first or cleanup first?
