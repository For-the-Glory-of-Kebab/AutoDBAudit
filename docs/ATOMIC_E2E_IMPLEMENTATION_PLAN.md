# Atomic E2E Test Architecture - Implementation Plan

> **Date**: 2025-12-21  
> **Status**: READY FOR COMMIT  
> **Approach**: Simplified sheet-by-sheet with key format testing

---

## Problem Statement

Tests pass but real `--sync` is broken. Root cause identified:
1. **Column detection** - partial string matching ('Server' matches 'Linked Server')
2. **Entity key format inconsistency** - keys differ between Excel read, DB, and stats lookup

---

## Simplified Approach

### Core Principle
**Prove ONE sheet works completely, then template to others.**

### Test Layers (Per Sheet)

| Layer | Purpose | Must Pass First |
|-------|---------|-----------------|
| **L0** | Key format consistency | - |
| **L1** | Simple fields (notes, dates) | L0 |
| **L2** | Exception detection | L0, L1 |
| **L3** | Non-discrepant rows | L0, L1 |
| **L4** | State transitions | L0-L3 |
| **L5** | Multi-sync stability | L0-L4 |
| **L6** | Combinations | L0-L5 |

### Layer 0: Key Format Consistency (NEW)

```python
def test_L0_key_format_consistency(self):
    """
    MUST PASS BEFORE ALL OTHER TESTS.
    
    Verifies:
    1. Excel read produces expected key format
    2. DB annotation key = entity_type|excel_key
    3. Stats lookup finds the annotation
    4. Case-insensitive matching works
    """
```

---

## Implementation Phases

### Phase 1: Documentation ✅
- [x] Implementation plan
- [x] Test specifications  
- [x] ENTITY_KEY_FORMATS.md
- [x] Fix EXCEL_COLUMNS.md

### Phase 2: Infrastructure
- [ ] Create `tests/atomic_e2e/core/`
- [ ] test_harness.py
- [ ] assertions.py
- [ ] randomizer.py

### Phase 3: Linked Servers (First Sheet)
- [ ] L0: Key consistency
- [ ] L1-L6: All layers
- [ ] Debug issues found
- [ ] Document fixes

### Phase 4: Remaining Sheets
- [ ] Copy template from Linked Servers
- [ ] Customize per sheet
- [ ] Update ENTITY_KEY_FORMATS.md verification status

---

## Directory Structure

```
tests/
├── atomic_e2e/
│   ├── core/
│   │   ├── test_harness.py
│   │   ├── assertions.py
│   │   └── randomizer.py
│   ├── sheets/
│   │   ├── test_linked_servers.py  ← FIRST
│   │   └── ...
│   └── .test_output/
└── archive/  ← Old tests moved here
```

---

## Key Documents

| Document | Purpose |
|----------|---------|
| [ENTITY_KEY_FORMATS.md](file:///f:/Raja-Initiative/docs/ENTITY_KEY_FORMATS.md) | Key format reference per sheet |
| [ATOMIC_E2E_TEST_SPECS.md](file:///f:/Raja-Initiative/docs/ATOMIC_E2E_TEST_SPECS.md) | Detailed test scenarios |
| [EXCEL_COLUMNS.md](file:///f:/Raja-Initiative/docs/EXCEL_COLUMNS.md) | Excel schema reference |

---

## Success Criteria

1. ✅ Linked Servers all layers pass
2. ✅ Key format verified in ENTITY_KEY_FORMATS.md
3. ✅ Stats show correct exception count
4. ✅ Actions sheet logs correctly
5. ✅ Multi-sync stable (no duplicates, no scrambling)

---

## Commit Ready

All documentation finalized. Ready for clean commit before implementation.
