# TODO Tracker

> Track work items. Checked items are complete.

---

## 🔴 High Priority (Next Steps)

### Schema Updates
- [ ] Add `action_log` table to schema.py
- [ ] Update `create_tables()` to include action_log

### Excel Columns
- [ ] Add Notes/Reason/Status Override to report_writer.py
- [ ] Add columns to: Logins, Config, Databases, etc.

### Command Refactor
- [ ] Implement `--sync` (separate from --finalize)
- [ ] Add real timestamp tracking in sync
- [ ] Refactor `--finalize` to read Excel + persist all

---

## 🟡 Medium Priority

- [ ] `--run-remediation` command (execute TSQL)
- [ ] `--status` command (show audit state)
- [ ] Permission Grants sheet

---

## ✅ Completed

### 2025-12-09: Documentation
- [x] AUDIT_WORKFLOW.md - Complete lifecycle
- [x] SCHEMA_DESIGN.md - All tables
- [x] CLI_REFERENCE.md - Command reference
- [x] PROJECT_STATUS.md - Current state

### 2025-12-09: Exception Service
- [x] exception_service.py
- [x] ExcelAnnotationReader
- [x] upsert_annotation helper
- [x] --apply-exceptions CLI

### 2025-12-09: Finalize Service
- [x] finalize_service.py
- [x] compare_findings diff logic
- [x] --finalize CLI

### 2025-12-09: Remediation Service
- [x] remediation_service.py
- [x] TSQL templates (SA, config, logins, db, db_users)
- [x] --generate-remediation CLI

### 2025-12-09: Findings Storage
- [x] findings table in schema.py
- [x] finding_changes table
- [x] 9 finding types wired in data_collector

---

*Last Updated: 2025-12-09*
