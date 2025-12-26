# PSRemote Sync/Remediation Integration Plan

> **Status**: IMPLEMENTED (Core)
> **Last Updated**: 2025-12-26

## Implemented Components

### 1. Exception-Aware Script Generation ✅
- `_wrap_exception_warning()` in `handlers/base.py`
- Aggressiveness levels: 1=commented, 2=warning, 3=indicator
- Service.py queries `is_exceptionalized` and `justification` from annotations

### 2. OS Data Puller ✅
- `os_data/puller.py` with OsDataResult dataclass
- Fallback chain: Manual > PSRemote > Cached > None

### 3. PowerShell Scripts ✅
- `Get-SqlServerOSData.ps1`: Protocols, services, audit policy
- `Restart-SqlServerService.ps1`: Graceful restart with retries
- `Set-ClientProtocol.ps1`: Enable/disable protocols

### 4. Docker/Linux Exception ✅
- `server_properties.py`: Default instance not flagged for Linux/containers

## Key Design Decisions

### Fallback Priority
```
1. Manual User Input (ALWAYS wins)
2. PSRemote Live Data (if available)
3. Cached Data (if stale)
4. T-SQL Data (fallback)
```

### Aggressiveness Levels
| Level | Behavior |
|-------|----------|
| 1 | Exceptionalized fixes COMMENTED OUT with ⚠️❌ markers |
| 2 | Exceptionalized fixes commented with warning |
| 3 | Exceptionalized fixes included, marked only |

## Files Created

| File | Purpose |
|------|---------|
| `os_data/__init__.py` | Module init |
| `os_data/puller.py` | OS data with fallback chain |
| `assets/scripts/Get-SqlServerOSData.ps1` | Data collection |
| `assets/scripts/Restart-SqlServerService.ps1` | Service restart |
| `assets/scripts/Set-ClientProtocol.ps1` | Protocol changes |

## Files Modified

| File | Change |
|------|--------|
| `handlers/base.py` | Added `_wrap_exception_warning()` |
| `remediation/service.py` | Exception-aware findings query |
| `server_properties.py` | Docker/Linux exception for Req 14 |

## Remaining Work

- Integrate os_data puller with sync_service.py
- Wire to CLI --remediate command
- Add L4 integration tests
