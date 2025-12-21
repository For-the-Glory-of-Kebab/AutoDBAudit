# Row UUID Architecture Design

## Executive Summary

This document proposes adding a **Row UUID** to every data row across all sheets to provide a stable, immutable identifier for Excel ↔ SQLite synchronization.

---

## Problem Statement

Current sync relies on **composite entity keys** built from data columns:
```
linked_server|localhost|intheend|insecure_link|sa|sa
```

**Failure modes:**
1. Key columns may be empty (merged cells, missing data)
2. Keys change when underlying data changes
3. Case-sensitivity and normalization issues
4. Deleted rows leave orphaned DB records with no match
5. Resurfaced rows (fixed then regressed) get new keys

---

## Proposed Solution

### UUID Format
```
UUID v4: 550e8400-e29b-41d4-a716-446655440000
Short ID alternative: 8-char hex (e.g., "A7F3B2C1")
```

**Recommendation:** Use short 8-char hex for readability if user accidentally unhides column

---

## Excel Column Strategy

### Option A: Hidden Column (Recommended)
- **Column A** contains UUID
- Column width set to 0 (hidden)
- Sheet protection locks column A

```python
# Set column width to 0
ws.column_dimensions['A'].width = 0
ws.column_dimensions['A'].hidden = True

# Protect sheet except editable columns
ws.protection.sheet = True
ws.protection.password = None  # No password, just prevent accidental edits
```

### Option B: Custom Document Property
- Store UUIDs in Excel workbook properties
- Cons: Not visible per-row, harder to debug

### Option C: Named Ranges
- Define named range per UUID
- Cons: Complex, doesn't scale

**Decision: Option A (Hidden Column)**

---

## Excel Protection Strategy

### Goals
1. User CANNOT accidentally edit UUID
2. User CAN edit annotation columns (Purpose, Justification, Review Status, Last Reviewed)
3. UUID visible for debugging if user explicitly unhides

### Implementation

```python
# Per-cell protection
for row in range(2, max_row + 1):
    uuid_cell = ws.cell(row=row, column=1)
    uuid_cell.protection = Protection(locked=True)
    
# Per-editable-column unlock
for col in editable_columns:
    for row in range(2, max_row + 1):
        cell = ws.cell(row=row, column=col)
        cell.protection = Protection(locked=False)

# Enable sheet protection (no password = user can disable if needed)
ws.protection.sheet = True
ws.protection.enable()
```

### What This Achieves
- ✅ UUID cells locked (cannot be edited without disabling protection)
- ✅ Annotation columns unlocked (user can edit freely)
- ✅ Protection is advisory (no password), expert user can disable
- ✅ Hidden column width persists across saves

---

## UUID Lifecycle

### 1. Initial Audit (Row Creation)
```
Event: New row written to Excel
Action: Generate UUID v4, write to hidden column A
SQLite: Store in annotations.row_uuid or findings.row_uuid
```

### 2. Sync (Row Match)
```
Event: Reading Excel for sync
Action: Read UUID from column A
Match: Look up in SQLite by UUID
Result: Perfect 1:1 match regardless of key changes
```

### 3. Row Deleted (Discrepancy Resolved)
```
Event: Row exists in SQLite but not in Excel
Interpretation: Underlying issue was fixed (no longer FAIL)
Action: Mark SQLite record as "resolved", keep UUID for history
Do NOT: Delete from SQLite (we need audit trail)
```

### 4. Row Resurfaces (Regression)
```
Event: Previously resolved row reappears in audit
Question: Is this the "same" row or a "new" row?

Strategy A: Match by entity key, reuse old UUID
  - Pros: Historical continuity
  - Cons: Entity key matching is what we're trying to avoid

Strategy B: Always generate new UUID
  - Pros: Simple, no ambiguity
  - Cons: Lose historical link to previous occurrence

Strategy C: "Resurrection" lookup by entity key + time window
  - If entity key matches resolved record within N days, reuse UUID
  - Otherwise, new UUID

**Recommendation: Strategy B (new UUID) with entity_key as soft reference**
```

### 5. User Clears UUID (Accidental)
```
Event: User unhides column, deletes UUID
Detection: UUID column empty but row has data
Action: Generate new UUID, log warning
Result: Row becomes "new" in DB, old record orphaned
```

### 6. Duplicate UUID (Copy-Paste)
```
Event: User duplicates row including UUID
Detection: Same UUID appears twice in sheet
Action: On sync read, detect duplicates, regenerate one
```

---

## SQLite Schema Changes

### Current Schema (annotations table)
```sql
CREATE TABLE annotations (
    id INTEGER PRIMARY KEY,
    entity_key TEXT UNIQUE,
    entity_type TEXT,
    purpose TEXT,
    justification TEXT,
    review_status TEXT,
    last_reviewed TEXT,
    -- ... other fields
);
```

### Proposed Schema
```sql
CREATE TABLE annotations (
    id INTEGER PRIMARY KEY,
    row_uuid TEXT UNIQUE NOT NULL,  -- NEW: Stable identifier
    entity_key TEXT,                 -- Keep for reference, not unique
    entity_type TEXT,
    sheet_name TEXT,                 -- NEW: Which sheet this belongs to
    status TEXT,                     -- NEW: 'active', 'resolved', 'orphaned'
    first_seen_at TEXT,              -- NEW: Audit trail
    last_seen_at TEXT,               -- NEW: Audit trail
    resolved_at TEXT,                -- NEW: When marked resolved
    purpose TEXT,
    justification TEXT,
    review_status TEXT,
    last_reviewed TEXT
);

CREATE INDEX idx_annotations_uuid ON annotations(row_uuid);
CREATE INDEX idx_annotations_entity_key ON annotations(entity_key);
```

### Migration Strategy
```sql
-- Add columns
ALTER TABLE annotations ADD COLUMN row_uuid TEXT;
ALTER TABLE annotations ADD COLUMN sheet_name TEXT;
ALTER TABLE annotations ADD COLUMN status TEXT DEFAULT 'active';
ALTER TABLE annotations ADD COLUMN first_seen_at TEXT;
ALTER TABLE annotations ADD COLUMN last_seen_at TEXT;

-- Generate UUIDs for existing records
UPDATE annotations SET row_uuid = hex(randomblob(4)) WHERE row_uuid IS NULL;

-- Create index
CREATE UNIQUE INDEX IF NOT EXISTS idx_annotations_uuid ON annotations(row_uuid);
```

---

## Code Impact Analysis

### Files That Need Changes

| File | Change Required |
|------|-----------------|
| `excel/base.py` | Add UUID column definition, write logic |
| `excel/writer.py` | Include UUID in sheet creation |
| `excel/{sheet}.py` (all 20) | Add UUID to column definitions |
| `annotation_sync.py` | Read/write by UUID instead of entity_key |
| `stats_service.py` | Update key matching to use UUID |
| `sqlite/schema.py` | Add new columns, migration |
| `sqlite/store.py` | CRUD by UUID |
| All test files | Update to include UUID |

### Estimated Effort
- **Schema + Migration**: 2 hours
- **Excel Writer Updates**: 4 hours (20 sheets)
- **Annotation Sync Rewrite**: 4 hours
- **Stats Service Refactor**: 2 hours
- **Testing**: 4 hours
- **Total**: ~16-20 hours

---

## Edge Cases Matrix

| Scenario | Detection | Action | Result |
|----------|-----------|--------|--------|
| New row (first audit) | No UUID | Generate UUID | New record in DB |
| Existing row (sync) | UUID matches DB | Update annotations | Modified record |
| Row deleted | UUID in DB, not in Excel | Mark as resolved | Historical record |
| Row resurfaces | Entity key match, no UUID | Generate new UUID | New record (separate from history) |
| UUID cleared by user | Empty UUID, has data | Generate new UUID | Log warning, new record |
| UUID duplicated | Same UUID twice in sheet | Regenerate second | Log error |
| UUID collision | Two different rows same UUID | Astronomically unlikely (1 in 2^128) | No action needed |
| Sheet reordered | UUIDs in different order | Match by UUID | Works correctly |
| Merged cells hidden | UUID per logical row | Read all rows | Works correctly |

---

## Alternatives Considered

### 1. Composite Key with Hash
- Hash the entity key to create stable ID
- **Problem**: Key changes → hash changes

### 2. Row Number as ID
- Use Excel row number
- **Problem**: Rows reorder, delete, insert

### 3. Timestamp-based ID
- First-seen timestamp as ID
- **Problem**: Precision issues, not unique

### 4. No Change (Current System)
- Keep entity key matching
- **Problem**: All current bugs persist

---

## Questions for User

1. **Short ID vs Full UUID**: Prefer 8-char hex (`A7F3B2C1`) or full UUID?
2. **Resurrection**: When fixed issue regresses, should it link to old history or start fresh?
3. **Protection level**: Advisory (no password) or enforced (with password)?
4. **Migration**: Regenerate all existing Excel files or grandfather them?

---

## Recommendation

**Proceed with Row UUID implementation** using:
- Hidden Column A with 8-char hex ID
- Advisory sheet protection (no password)
- New UUID for resurfaced rows (no resurrection)
- Migration adds UUID to existing records on first sync

This provides the stability we need while being minimally invasive to the user experience.
