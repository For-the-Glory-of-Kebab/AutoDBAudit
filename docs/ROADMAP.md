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

## MEDIUM PRIORITY - Future

### 1. Persian/RTL Font Support
**Status**: Deferred - CF limitations make dynamic approach impractical.

### 2. Extended Merge Cells Logic
**Status**: Needs careful design before implementation.

---

## DONE BUT UNVERIFIED 🔄

### PSRemote pywinrm Implementation (2025-12-26)
- `infrastructure/psremote/client.py` - Multi-transport (HTTP/HTTPS), multi-auth (negotiate/kerberos/ntlm/basic)
- `infrastructure/psremote/executor.py` - ScriptExecutor for running bundled PS scripts
- `os_data/puller.py` - Updated to use actual ScriptExecutor (no more placeholder!)
- Connection caching for repeated calls
- Ultra-resilient retry logic

### Remediation Engine (2025-12-26)
- Jinja2 template system with SQL 2008 compatibility
- Individual INSERT lines per item (easy commenting)
- Aggressiveness levels (1-3)
- Exception-aware script generation
- 8 unit tests (L2)

---

## COMPLETED ✅

- [x] Access Preparation (8-layer strategy)
- [x] Default Instance Naming Check (Requirement 14)
- [x] Text Wrap for date/justification columns
- [x] Unicode/Persian name support (UTF-8 loading)
- [x] Build manifest includes assets/scripts
- [x] Manual Action Log - Dropdowns + CF (in actions.py)
