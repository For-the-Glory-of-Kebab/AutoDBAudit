# Active Tasks

**Last Updated:** 2025-12-22 15:00

---

## ✅ COMPLETED: Linked Servers E2E Test Suite

**Status:** Done (62 tests passing)

Created comprehensive test suite in `tests/atomic_e2e/sheets/linked_servers/`:
- [x] Exception lifecycle (add/update/remove)
- [x] Multi-sync stability (idempotency)
- [x] Edge cases (Unicode, bad dates, long text)
- [x] Action log column verification
- [x] Annotation persistence through status changes

---

## ✅ COMPLETED: Triggers E2E Test Suite

**Status:** Done (19 tests passing)

- [x] Created harness with trigger-specific KEY_COLS
- [x] Exception lifecycle tests
- [x] SERVER vs DATABASE scope tests
- [x] **FOUND & FIXED 2 production bugs!**

---

## ⏸️ PAUSED: Additional Sheet Tests

**Status:** Paused (user time constraint)

Extensibility proven. Next sheets when time allows:
1. Backups
2. Server Logins
3. Permissions
4. Database Users
5. Configuration

---

## 🔮 Future Enhancement

**Add FIXED/REGRESSION Detection to Harness**
- Current harness only detects EXCEPTION changes
- FIXED (FAIL→PASS) and REGRESSION (PASS→FAIL) require SyncService integration
- Tests adapted to verify annotation persistence instead

---

## 📝 Notes

- Manual verification: Run fresh audit to confirm triggers appear in action logs
- Test framework catches real production bugs - keep expanding!
