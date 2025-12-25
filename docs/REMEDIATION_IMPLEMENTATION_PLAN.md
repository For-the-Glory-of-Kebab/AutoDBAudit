# Remediation Module Implementation Plan

## Executive Summary

The remediation module needs significant work to meet production requirements:
1. **T-SQL Scripts**: Logic mostly correct but needs validation
2. **PSRemoting**: Scripts exist but not integrated into CLI
3. **Hotfix Module**: All service methods are stubs (`NotImplementedError`)
4. **Sync Engine**: State machine logic is sound but key matching has edge cases

---

## User Review Required

> [!IMPORTANT]
> **PSRemoting Exposure**: The Bootstrap-WinRM.ps1 and Enable-WinRM.ps1 scripts exist but are NOT exposed through the CLI. Need decision on:
> - Should we add CLI commands like `autodbaudit remediate --enable-psremoting TARGET`?
> - Or keep them as standalone scripts in the dist package?

> [!WARNING]
> **Hotfix Module**: The entire HotfixService is stubbed out. The `deploy()`, `resume()`, `retry_failed()`, and `get_deployment_status()` methods all raise `NotImplementedError`. This means the automated hotfix deployment feature is not functional.

---

## Proposed Changes

### Phase 1: Critical T-SQL Fixes

#### [VERIFY] [access_control.py](file:///c:/Users/sickp/source/SQLAuditProject/AutoDBAudit/src/autodbaudit/application/remediation/handlers/access_control.py)
- SA rename: Already changed to `$@` ✓
- Verify aggressiveness levels generate correct output
- Ensure login auditing script is generated (Requirement #22)

---

### Phase 2: PSRemoting CLI Integration

#### [MODIFY] [cli.py](file:///c:/Users/sickp/source/SQLAuditProject/AutoDBAudit/src/autodbaudit/interface/cli.py)
Add new arguments to remediate subparser:
```python
parser_rem.add_argument("--enable-psremoting", metavar="TARGET", help="Enable PSRemoting on target")
parser_rem.add_argument("--disable-psremoting", metavar="TARGET", help="Disable PSRemoting on target")
```

Add handler functions to call Bootstrap-WinRM.ps1

---

### Phase 3: Manifest Update for PSRemoting Scripts

#### [MODIFY] [manifest.json](file:///c:/Users/sickp/source/SQLAuditProject/AutoDBAudit/packaging/manifest.json)
Add PSRemoting scripts to dist package:
```json
{
  "Source": "src/autodbaudit/hotfix/Bootstrap-WinRM.ps1",
  "Destination": "scripts/Bootstrap-WinRM.ps1"
},
{
  "Source": "src/autodbaudit/hotfix/CreateAccess/Enable-WinRM.ps1",
  "Destination": "scripts/Enable-WinRM.ps1"
}
```

---

### Phase 4: Sync Engine Validation

#### [VERIFY] [sync_service.py](file:///c:/Users/sickp/source/SQLAuditProject/AutoDBAudit/src/autodbaudit/application/sync_service.py)
- Verify state transitions work correctly
- Verify exception clearing on FIXED items

#### [VERIFY] [state_machine.py](file:///c:/Users/sickp/source/SQLAuditProject/AutoDBAudit/src/autodbaudit/domain/state_machine.py)
- Line 124-135: FIXED logic verified
- Line 153-173: Exception state changes verified

---

## Verification Plan

### Automated Tests
1. Run existing E2E tests: `python .scripts/run_in_venv.py -m pytest tests/ultimate_e2e/ -v`
2. Verify all 179 tests pass

### Manual Verification
1. Generate remediation scripts at each aggressiveness level
2. Verify SA script contains: Rename to `$@`, Password scramble, DISABLE
3. Test PSRemoting scripts on a test VM
4. Run full sync cycle and verify statistics match Excel

---

## Implementation Priority

| Item | Priority | Effort | Impact |
|------|----------|--------|--------|
| PSRemoting in dist | P0 | Low | High - Required for deployment |
| CLI PSRemoting commands | P1 | Medium | Medium - Convenience |
| Hotfix module implementation | P2 | High | Low - Future feature |
| Sync engine validation | P0 | Low | High - Core correctness |
