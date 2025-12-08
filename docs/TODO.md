# TODO Tracker

> Track work items. Move completed items to bottom when done.

---

## 🔴 High Priority - Next Up

### SQLite Integration
- [ ] Wire `HistoryStore` into `audit_service.py`
- [ ] Create `.db` file alongside `.xlsx` during audit
- [ ] Schema v2 tables populated with audit data

### `--finalize` Command
- [ ] Read annotations from completed Excel file
- [ ] Store in SQLite `*_annotations` tables
- [ ] Preserve across audit runs

---

## 🟡 Medium Priority

### Additional Sheets
- [ ] Permission Grants sheet (Requirement #28)
- [ ] Role Membership Matrix visualization

### Code Quality
- [ ] Fix broad exception catches in `data_collector.py`
- [ ] Add encoding param to `open()` in `config_loader.py`
- [ ] Remove unused imports

---

## 🟢 Low Priority / Future

- [ ] Historical diff tracking between audits
- [ ] Rich/Typer for better terminal UI
- [ ] Progress bars for long operations
- [ ] Hotfix deployment features

---

## ✅ Completed

### 2025-12-08: Infrastructure + Encryption
- [x] Create `sql/` subfolder (connector.py, query_provider.py)
- [x] Create `sqlite/` subfolder (store.py, schema.py)
- [x] Add Encryption sheet (#17) with SMK/DMK/TDE
- [x] Update all imports and documentation

### 2025-12-08: CLI Integration
- [x] `AuditDataCollector` for modular data collection
- [x] `AuditService.run_audit()` generates Excel directly
- [x] CLI `--audit` command works end-to-end

### 2025-12-08: Excel Reporting
- [x] Modular `excel/` package with 21 files
- [x] 17 sheets with conditional formatting
- [x] Server/instance grouping with colors
- [x] Dropdown validation on all boolean/enum columns

### 2025-12-07: Query Provider
- [x] Strategy pattern for SQL 2008 vs 2012+
- [x] All audit queries version-compatible

### 2025-12-06: Foundation
- [x] Domain-driven project structure
- [x] Python 3.11+ typing throughout

---

*Last updated: 2025-12-08*
