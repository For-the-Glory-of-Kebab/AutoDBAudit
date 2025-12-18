# TODO - AutoDBAudit Project

## ✅ Completed (2025-12-18)

### Sync Engine Modular Refactor
- [x] Design state machine for all transitions
- [x] Create domain types (`change_types.py`, `state_machine.py`)
- [x] Build StatsService (single source of truth)
- [x] Extract diff logic to `application/diff/`
- [x] Extract action logic to `application/actions/`
- [x] Rewrite sync_service.py as thin orchestrator
- [x] Unit tests (26 tests passing)
- [x] Documentation (`docs/SYNC_ENGINE_ARCHITECTURE.md`)

---

## 🔴 High Priority

### E2E Testing for Sync Refactor
- [ ] Test with real SQL instances
- [ ] Verify multi-sync stability (sync 2-3 times, no duplicates)
- [ ] Verify Actions sheet populates correctly
- [ ] Verify exception counts are accurate

### CLI Output Improvements
- [ ] Use `StatsService` in all commands
- [ ] Improve visual formatting (from DEV_THOUGHTS.md)

---

## 🟡 Medium Priority

### Excel Robustness
- [ ] Review merged cell handling
- [ ] Add ID tracking to all sheets
- [ ] Improve error handling for locked files

### Annotation Sync Refactor
- [ ] Break up `annotation_sync.py` (932 lines)
- [ ] Use new domain types

---

## 🟢 Low Priority / Backlog

- [ ] WARN/CRITICAL severity distinction
- [ ] Hotfix orchestration (stubs exist)
- [ ] Instance merging in CLI
- [ ] --regenerate-excel command

---

## 📚 Key Documents
- `docs/SYNC_ENGINE_ARCHITECTURE.md` - Full refactor spec
- `docs/SYNC_ENGINE_REQUIREMENTS.md` - Requirements
- `docs/SESSION_HANDOFF_2025-12-18_REFACTOR.md` - Session summary
