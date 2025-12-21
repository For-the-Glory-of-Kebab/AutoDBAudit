# AutoDBAudit Active Tasks

## Current Focus: Row UUID Architecture

### Session 2025-12-21 (Afternoon) ✅

**Bugs Fixed:**
1. Linked Server collector column names (`LinkedServerName`, `Provider`, `Product`)
2. Added `get_linked_server_logins()` call for login/risk data
3. Exception status check: `"Exception" in str(...)` for emoji matching

**Status:** 20/20 atomic E2E tests passing

---

## Next: Row UUID Implementation

**Decision:** Implement stable Row UUIDs to fix sync issues

### Checklist

#### Phase 1: SQLite Schema
- [ ] Add `row_uuid`, `status`, `first_seen_at`, `last_seen_at` columns
- [ ] Create migration script
- [ ] Update `store.py` with UUID CRUD

#### Phase 2: Excel Column Infrastructure
- [ ] Add UUID column (hidden, locked) to base
- [ ] Update all 20 sheet modules
- [ ] Implement sheet protection

#### Phase 3: Annotation Sync Rewrite
- [ ] Read by UUID instead of entity_key
- [ ] Write by UUID
- [ ] Handle edge cases (new, deleted, duplicate)

#### Phase 4: Stats Service
- [ ] Update to use UUID matching
- [ ] Remove entity_key normalization complexity

#### Phase 5: Testing
- [ ] Update test harness for UUID
- [ ] Verify 20 Linked Server tests still pass
- [ ] Manual E2E verification

---

## Paused: E2E Test Suite

**Reason:** Entity key-based sync fundamentally flawed

**Resume after:** Row UUID implementation complete

**Status at pause:**
- Infrastructure: ✅ Complete
- Linked Servers: ✅ 20/20 passing
- Remaining sheets: ⏸️ Paused

---

## Documentation Trail
- `docs/ROW_UUID_DESIGN.md` - Architecture design
- `docs/ROW_UUID_IMPLEMENTATION_PLAN.md` - Implementation phases
- `docs/SESSION_HANDOFF_2025-12-21_PM.md` - Session summary
- `docs/ATOMIC_E2E_TASK.md` - E2E test status
