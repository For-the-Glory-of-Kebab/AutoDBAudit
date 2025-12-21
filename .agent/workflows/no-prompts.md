---
description: How to run any command without triggering prompts - wrap complex commands
---

# CRITICAL: No piped commands, no 2>&1, no Select-Object

## Mistakes to NEVER make:
- ❌ `cmd 2>&1 | Select-Object -Last 20`
- ❌ `.\venv\Scripts\Activate.ps1; python file.py` (semicolon)
- ❌ `python -c "..."` or `python -m ...`
- ❌ Direct `.exe` from `./venv/`

## Correct approach:
// turbo-all
1. Use `.\scripts\run_pytest.ps1 <test>` for tests
2. Use `.\scripts\run.ps1 <args>` for CLI
3. Create wrapper scripts for anything else:

```powershell
# scripts/run_<name>.ps1
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python <command>
Pop-Location
```

4. Never pipe output - let it stream naturally
5. If you need to filter output, do it in a wrapper script
