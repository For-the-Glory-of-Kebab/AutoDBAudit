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

## HIGH PRIORITY - In Progress

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
**Status**: Deferred - CF limitations make dynamic approach impractical.

### 3. Extended Merge Cells Logic
**Status**: Needs careful design before implementation.

---

## DONE BUT UNVERIFIED 🔄

### PSRemote Integration (2025-12-26)
- OS Data Puller with fallback chain (Manual > PSRemote > Cached)
- PowerShell scripts: Get-SqlServerOSData, Restart-SqlServerService, Set-ClientProtocol
- Docker/Linux exception for default instance naming

### Remediation Engine (2025-12-26)
- Jinja2 template system with SQL 2008 compatibility
- Individual INSERT lines per item (easy commenting in/out)
- Aggressiveness levels (1=safe, 3=aggressive)
- Connecting user NEVER auto-uncommented
- Exception-aware script generation
- 8 unit tests (L2)

---

## COMPLETED ✅

- [x] Access Preparation (8-layer strategy)
- [x] Default Instance Naming Check (Requirement 14)
- [x] Text Wrap for date/justification columns
- [x] Unicode/Persian name support (UTF-8 loading)
- [x] Build manifest includes assets/scripts
