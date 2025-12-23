# Active Tasks

**Last Updated:** 2025-12-23 07:55

---

## ✅ COMPLETED: E2E Test Suite for All Sheets

**Status:** 107/137 tests passing (78%)

Created test suites for 11 sheets:
- Linked Servers (62 tests) ✅
- Triggers (19 tests) ✅  
- Backups, Server Logins, Configuration
- Databases, Permissions, Sensitive Roles
- Services, Orphaned Users, Database Users

### Production Bugs Fixed
1. triggers.py column 8→9 (Enabled overwriting Event)
2. Missing save_finding() for triggers

---

## 🎯 CRITICAL: Finalize Hook & Remediation

**Status:** Next Priority

User mentioned:
- Sync and diff engine unified for every sheet
- Proper --finalize hook
- Remediation tweaks

---

## 📝 Commit Ready

Message:
```
feat(tests): add E2E test suite for 11 sheets (107 tests)

- Create comprehensive tests for Linked Servers (62) and Triggers (19)
- Add test harnesses for 9 more sheets
- Fix triggers.py column index bug
- Fix missing save_finding() for triggers
- Add entity_key parameter to base collector
```
