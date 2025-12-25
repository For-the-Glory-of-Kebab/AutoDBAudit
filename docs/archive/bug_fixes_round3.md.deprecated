# Critical Bug Fixes Round 3 - COMPLETED

## 1. Client Protocols Sheet ✅
- [x] Fixed Conditional Formatting typo: `file=` → `fill=` (was causing CF to fail)
- [x] Status column (H) now has proper CF rules
- [x] Enabled column (F) has proper CF rules based on protocol type
- [x] Server/Instance merging verified working via ServerGroupMixin

## 2. CLI Stats Enhancement ✅
- [x] Added per-sheet breakdown with: active, exceptions, compliant, regressions, new issues, fixed

## 3. Exception Removal Logging ✅
- [x] Now detects when Review Status changes FROM "Exception" to other status
- [x] Also detects when both justification AND status are cleared
- [x] Logs detailed info: old status → new status

## 4. Databases Sheet ✅
- [x] Trustworthy ON = RED (security risk) - uses `apply_boolean_styling(invert=True)`
- [x] Trustworthy OFF = GREEN (secure)
- [x] CF rules added for dynamic styling

## 5. Role Matrix Sheet ✅
- [x] Fixed column indices: meta_cols=[3,4,5,6,7] (Host, Instance, DB, Principal, Type)
- [x] Fixed Risk column index: `len(ROLE_MATRIX_COLUMNS) + 1` (accounts for UUID)
- [x] Added `_finalize_grouping` call in `_finalize_role_matrix`
- [x] Roles start at column 8
- [x] db_owner with YES/checkmark styling via existing logic

## 6. Permission Grants Sheet ✅
- [x] Verified collector correctly uses `scope="DATABASE"` for DB permissions
- [x] Scope column properly displays SERVER or DATABASE
