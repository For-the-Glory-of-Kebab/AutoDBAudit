# TODO Tracker

---

## 🔴 High Priority

- [ ] Live test --apply-remediation with real SQL Server
- [ ] Fix SA protection: If connecting as SA, must use different approach

---

## 🟡 Medium Priority

- [ ] Carry-forward annotations on next audit
- [ ] Triggers SQLite persistence
- [ ] Permission Grants sheet
- [ ] Hotfix deployment module

---

## ✅ Completed

### 2025-12-09: Apply Remediation CLI
- [x] script_executor.py with GO batch isolation
- [x] --apply-remediation command
- [x] --dry-run mode
- [x] --rollback mode
- [x] Credential protection (skips batches modifying connection login)

### 2025-12-09: Smart Remediation Scripts
- [x] 4-category scripts (AUTO-FIX, CAUTION, REVIEW, INFO)
- [x] Orphaned user DROP with full state logging
- [x] Rollback script generation (_ROLLBACK.sql)
- [x] SA rename + disable + password logged

### 2025-12-09: Status Command
- [x] status_service.py with dashboard
- [x] --status CLI command

### 2025-12-09: SQLite Data Persistence
- [x] logins, databases, users, config
- [x] linked_servers, backups

### 2025-12-09: Earlier
- [x] finalize, exception, sync services

---

## ⚠️ Known Issues

**SA Connection Protection**: If you connect to SQL Server using the SA login,
the --apply-remediation command will SKIP all SA modification batches to prevent
locking yourself out. To apply SA remediation, use a different admin account.

---

*Last Updated: 2025-12-09*
