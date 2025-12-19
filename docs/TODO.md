# TODO - AutoDBAudit Project

## ✅ Completed (2025-12-19)

### Sync Engine Testing & Edge Cases
- [x] Fix `test_sync_logic.py` (import, schema, attributes)
- [x] Add edge case tests (instance unavailable, fix+exception priority)
- [x] Verify multi-sync stability
- [x] Verify action deduplication
- [x] All 31 tests passing (26 state_machine + 5 sync_logic)

## ✅ Completed (2025-12-18)

### Sync Engine Modular Refactor
- [x] Design state machine for all transitions
- [x] Create domain types (`change_types.py`, `state_machine.py`)
- [x] Build StatsService (single source of truth)
- [x] Extract diff logic to `application/diff/`
- [x] Extract action logic to `application/actions/`
- [x] Rewrite sync_service.py as thin orchestrator
- [x] Documentation (`docs/SYNC_ENGINE_ARCHITECTURE.md`)

---

## 🔴 High Priority

### E2E Robust Test Suite Completion
- [ ] Complete `tests/e2e_robust/test_audit_lifecycle.py` patching
- [ ] Verify 6 cycle scenarios pass (Fresh → Exception → Stability → Fix → Regression → Removal)
- [ ] Real SQL Server validation

### CLI Output Improvements
- [ ] Use `StatsService` in all commands
- [ ] Improve visual formatting

---

## 🟡 Medium Priority

### Excel Robustness
- [ ] Review merged cell handling
- [ ] Add ID tracking to all sheets

### Annotation Sync Refactor
- [ ] Break up `annotation_sync.py` (932 lines)
- [ ] Use new domain types

---

## 🟢 Low Priority / Backlog

- [ ] WARN/CRITICAL severity distinction
- [ ] Hotfix orchestration
- [ ] --regenerate-excel command

---

## 📚 Key Documents
- `docs/SYNC_ENGINE_ARCHITECTURE.md` - Full spec
- `docs/SYNC_ENGINE_REQUIREMENTS.md` - Requirements
- `docs/SESSION_HANDOFF_2025-12-19_TESTING.md` - Today's session
