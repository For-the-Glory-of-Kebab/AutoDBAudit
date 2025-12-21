# Row UUID Architecture Implementation Plan

## Approved Decisions

| Decision | Answer |
|----------|--------|
| ID Format | UUID v4 (no clashes guaranteed) |
| Protection | Maximum: hidden, locked, unselectable |
| Resurrection | New UUID for regressed rows |
| Sync Stability | UUID immutable across --sync runs |

---

## Implementation Phases

### Phase 1: SQLite Schema Update (2 hours)

1. Add columns to `annotations` table:
   ```sql
   ALTER TABLE annotations ADD COLUMN row_uuid TEXT UNIQUE;
   ALTER TABLE annotations ADD COLUMN status TEXT DEFAULT 'active';
   ALTER TABLE annotations ADD COLUMN first_seen_at TEXT;
   ALTER TABLE annotations ADD COLUMN last_seen_at TEXT;
   ```

2. Create migration script for existing data
3. Update `sqlite/store.py` with UUID CRUD methods

### Phase 2: Excel Column Infrastructure (4 hours)

1. **Modify `excel/base.py`**:
   - Add `UUID_COLUMN` constant
   - Add `_write_uuid()` helper
   - Add sheet protection helpers

2. **Update each sheet module** (~20 files):
   - Add UUID column as Column A
   - Shift all other columns +1
   - Update column references

3. **Sheet protection**:
   - Lock UUID column
   - Hide UUID column (width=0)
   - Allow editing annotation columns only

### Phase 3: Annotation Sync Rewrite (4 hours)

1. **Read by UUID** instead of entity_key:
   ```python
   def read_all_from_excel(excel_path):
       for row in rows:
           uuid = row[0]  # Column A
           if not uuid:
               uuid = generate_uuid()  # New row
           annotations[uuid] = fields
   ```

2. **Write by UUID**:
   ```python
   def write_all_to_excel(excel_path, annotations):
       for uuid, fields in annotations.items():
           row = find_row_by_uuid(ws, uuid)
           write_fields(row, fields)
   ```

3. **Handle edge cases**:
   - New rows (no UUID)
   - Deleted rows (UUID in DB, not in Excel)
   - Duplicate UUIDs (regenerate second)

### Phase 4: Stats Service Update (2 hours)

1. Update key matching to use UUID
2. Remove complex entity_key normalization
3. Simplify exception lookup

### Phase 5: Testing (4 hours)

1. Update test harness for UUID
2. Run all 20 Linked Server tests
3. Manual E2E verification
4. Edge case tests (delete, duplicate, clear UUID)

---

## Files to Modify

| Category | Files |
|----------|-------|
| Schema | `sqlite/schema.py`, `sqlite/store.py` |
| Base Excel | `excel/base.py`, `excel/writer.py` |
| Sheet Modules | `excel/{all 20 sheet files}.py` |
| Sync | `annotation_sync.py` |
| Stats | `stats_service.py` |
| Tests | `test_harness.py`, `test_linked_servers.py` |

---

## Migration Strategy

### New Audits
- UUID generated for every row on creation

### Existing Databases
- Migration adds `row_uuid` column
- First sync after migration generates UUIDs
- Old entity_key kept as reference

### Existing Excel Files
- First sync reads file, adds UUID column
- Saves with new column structure

---

## Success Criteria

1. ✅ UUID persists across multiple --sync runs
2. ✅ Deleted rows detected (UUID in DB, not Excel)
3. ✅ Annotations match correctly by UUID
4. ✅ Stats show accurate counts
5. ✅ User cannot edit UUID column
6. ✅ All 20+ atomic tests pass
