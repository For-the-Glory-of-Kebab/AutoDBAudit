# Feature Backlog & Testing Guidelines

## Testing Strategy (ALWAYS FOLLOW)

**Layered Test Pyramid - Run in order of scope:**
1. **L1-L2** (5-10s): Unit tests - run after atomic changes
2. **L3-L4** (30s): Integration - run after component changes  
3. **L5-L6** (2-3 min): E2E - run before commits only

**Commands:**
```powershell
# Unit test only (fast)
.\scripts\run_pytest.ps1 tests/layers/L2_state/ -v

# Full suite (before commit only)
.\scripts\run_ultimate_e2e.ps1
```

---

## HIGH PRIORITY - Deferred

### 1. Manual Action Log Enhancement
**Problem**: Pre-audit manual changes need logging in Action sheet.

**Requirements**:
- Data validation dropdowns (Category, Risk, Change Type)
- Conditional formatting per value
- Input validation, proper sorting
- Fix hex instance name display

---

## MEDIUM PRIORITY - Future

### 2. Persian/RTL Font Support
**Problem**: Persian text needs RTL alignment and different font.

**Findings**:
- ❌ Excel CF cannot detect character scripts
- ❌ CF cannot dynamically change fonts
- ✅ Python can detect Persian: `'\u0600' <= char <= '\u06FF'`
- ⚠️ Font licensing (B Nazanin, IR Nazanin)

**Status**: Deferred - CF limitations make dynamic approach impractical.

---

### 3. Extended Merge Cells Logic
**Problem**: Merge cells for all columns with repeated values.

**Requirements**:
- Detect same-value runs across rows
- Merge visually without losing data
- Handle proper value extraction from merged cells (avoid null/empty reads)
- Support virtual separation when rows added/reordered
- Must work with sync operations (annotations preserved)

**Risks**:
- openpyxl merge behavior can lose non-top cell values
- Need careful value propagation before merge
- Sync must handle merged→unmerged transitions

**Status**: Needs careful design before implementation.

---

## COMPLETED ✅

- [x] Access Preparation (8-layer strategy)
- [x] Default Instance Naming Check (Requirement 14)
- [x] Text Wrap for date/justification columns
- [x] Unicode/Persian name support (UTF-8 loading)
