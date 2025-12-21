# Atomic E2E Test Implementation

## Current Phase: PLANNING (Finalizing Documentation)

---

## Checklist

### Phase 0: Documentation & Commit
- [x] Create implementation plan
- [x] Create test specifications
- [x] Fix EXCEL_COLUMNS.md (Linked Servers Purpose column)
- [/] Create ENTITY_KEY_FORMATS.md reference
- [/] Update implementation plan with simplified approach
- [ ] Sync all docs to docs/ folder
- [ ] User approval for commit

### Phase 1: Infrastructure
- [ ] Create `tests/atomic_e2e/` directory structure
- [ ] Build `core/test_harness.py`
- [ ] Build `core/excel_helper.py`
- [ ] Build `core/assertions.py`
- [ ] Build `core/randomizer.py`
- [ ] Verify wrapper scripts work autonomously

### Phase 2: Linked Servers (First Sheet)
- [ ] Layer 0: Key format consistency test
- [ ] Layer 1: Simple fields (Purpose, Notes, Dates)
- [ ] Layer 2: Exception detection
- [ ] Layer 3: Non-discrepant rows
- [ ] Layer 4: State transitions
- [ ] Layer 5: Multi-sync stability
- [ ] Layer 6: Combinations
- [ ] Debug and fix any issues found

### Phase 3: Remaining Sheets (Template-Based)
- [ ] SA Account
- [ ] Server Logins
- [ ] Configuration
- [ ] (remaining 13 data sheets)

### Phase 4: Cross-Sheet & Verification
- [ ] Cross-sheet isolation tests
- [ ] CLI stats verification
- [ ] Actions sheet verification

---

## Key Decisions Made
1. **Simplified approach**: One sheet at a time, prove it works, then template
2. **Layer 0 added**: Key format consistency test before any other tests
3. **Real writer only**: No mocking Excel structure
4. **Constrained randomization**: Guaranteed coverage with random variation
