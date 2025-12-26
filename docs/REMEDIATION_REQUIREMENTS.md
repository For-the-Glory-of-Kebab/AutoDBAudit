# Remediation Module Requirements

> **Source of Truth**: Requirements for the remediation engine.
> **Last Updated**: 2025-12-26

---

## Core Requirements

### R1: Exception-Aware Script Generation

Exceptionalized items must NOT break applications when remediation runs.

**Aggressiveness Levels:**
| Level | CLI Flag | Behavior |
|-------|----------|----------|
| 1 | `--aggressiveness 1` | Exceptionalized fixes **COMMENTED OUT** with ⚠️❌ markers |
| 2 | `--aggressiveness 2` | Exceptionalized fixes commented with warning |
| 3 | `--aggressiveness 3` | Exceptionalized fixes included, marked only |

**Default**: Aggressiveness 1 (Safe)

---

### R2: Hybrid Remediation Approach

Some fixes require both T-SQL and OS-level changes:

| Fix Type | Method | Example |
|----------|--------|---------|
| Configuration | T-SQL `sp_configure` | Disable xp_cmdshell |
| Service Account | PSRemote | Change MSSQLSERVER account |
| Protocols | PSRemote | Disable Named Pipes |
| Service Restart | PSRemote | Apply sp_configure changes |

---

### R3: Service Restart After Configuration

When `sp_configure` changes result in `running != configured`:
1. Generate restart command in script
2. Graceful stop with timeout (60s default)
3. Wait for connections to drain
4. Restart with retry logic (3 attempts)
5. Verify service is running

---

### R4: Data Priority (Fallback Chain)

When determining current state for remediation:
```
1. Manual User Input (ALWAYS takes precedence)
2. PSRemote Live Data (if can_pull_os_data = true)
3. Cached Data (if PSRemote unavailable)
4. T-SQL Data (fallback)
```

---

### R5: Docker/Linux Exceptions

- PSRemote not applicable (no WinRM)
- Default instance name EXEMPT from Req 14
- No OS-level remediation available

---

### R6: Script Generation (Jinja2)

Templates located in `src/autodbaudit/application/remediation/templates/`:
- `tsql/` - T-SQL remediation scripts
- `powershell/` - PowerShell remediation scripts

Each template receives:
- Finding details
- Is exceptionalized (bool)
- Exception justification
- Aggressiveness level
- Target info

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Remediation Service                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Script Gen   │  │ OS Data      │  │ Finding      │      │
│  │ (Jinja2)     │  │ Puller       │  │ Store        │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                │                 │                │
│         └────────────────┴─────────────────┘                │
│                          │                                  │
│                          ▼                                  │
│              ┌─────────────────────────┐                   │
│              │ Remediation Scripts:    │                   │
│              │ - Combined.sql          │                   │
│              │ - OSFixes.ps1           │                   │
│              │ - ServiceRestart.ps1    │                   │
│              └─────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
src/autodbaudit/application/
├── remediation/
│   ├── __init__.py
│   ├── service.py           # Main orchestrator
│   ├── script_generator.py  # Jinja2-based generator
│   ├── models.py            # Data classes
│   └── templates/
│       ├── tsql/
│       │   ├── header.sql.j2
│       │   ├── sp_configure.sql.j2
│       │   └── footer.sql.j2
│       └── powershell/
│           ├── header.ps1.j2
│           ├── service_restart.ps1.j2
│           └── protocol_change.ps1.j2
├── os_data/
│   ├── __init__.py
│   └── puller.py             # OS data with fallback
```
