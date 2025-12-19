# SQLite Schema Alignment Analysis

> **Created**: 2025-12-11 | **Updated**: 2025-12-11 | **Status**: 2 of 3 issues FIXED

## Summary

The `schema.py` file contains **two separate concerns**:
1. **Table DDL** (CREATE TABLE statements) - defines actual database structure
2. **Save Functions** (`save_*`) - Python functions that INSERT data

Schema alignment fixes were applied on 2025-12-11.

---

## Fixed Issues ✅

### 1. `databases` Table - FIXED ✅

**Original Issue**: Function used `page_verify` and `size_mb` but table has `data_size_mb`.

**Fix Applied**: Updated `save_database()` to:
- Use `data_size_mb` column (matches table schema)
- Accept both `data_size_mb` and `size_mb` params for backwards compatibility
- Removed non-existent `page_verify` column from INSERT

---

### 2. `linked_servers` Table - FIXED ✅

**Original Issue**: Function used 4 columns that don't exist (`uses_self_mapping`, `local_login`, `remote_login`, `is_impersonate`).

**Fix Applied**: Updated `save_linked_server()` to:
- Only INSERT columns that exist in table
- Keep legacy params in function signature for backwards compatibility (ignored)
- Added docstring noting that login mappings belong in `linked_server_logins` table

---

## Remaining Issue ⚠️

### 3. `backup_history` Table vs `save_backup_record()`

**Table DDL (summary-style):**
```sql
last_full_backup_date, last_diff_backup_date, days_since_full_backup, ...
```

**Function (event-style):**
```python
backup_type, backup_start, backup_finish, size_bytes, ...
```

**Issue**: Fundamental design mismatch:
- Table = "current backup status per DB" (summary)
- Function = "individual backup events" (log)

**Status**: Needs design decision. Not blocking - wrapped in try/except.

---

## Correctly Aligned (No Issues)

- ✅ `logins` table + `save_login()` - Fixed
- ✅ `databases` table + `save_database()` - Fixed
- ✅ `linked_servers` table + `save_linked_server()` - Fixed
- ✅ `config_settings` table + `save_config_setting()` - Correct
- ✅ `database_users` table + `save_db_user()` - Correct
- ✅ `findings` table + `save_finding()` - Correct

---

## Files Modified

| File | Change |
|------|--------|
| `schema.py` | Fixed `save_login()`, `save_database()`, `save_linked_server()` |
| `data_collector.py` | Wrapped all SQLite calls in try/except |

---

## Next Steps

1. **Delete old `audit_history.db`** - To use new schema on next audit
2. **Test cross-version** - SQL 2022 and 2008R2
3. **Decide backup_history design** - Summary vs events

*Last Updated: 2025-12-11*

