---
description: Command execution rules to avoid confirmation prompts
---

# Safe Command Auto-Run Policy

// turbo-all

## Auto-Run Works For

1. **Python scripts (file-based)**
   ```powershell
   python script.py
   python src/test_file.py
   ```

2. **PowerShell file operations**
   ```powershell
   New-Item, Remove-Item, Copy-Item, Get-ChildItem
   ```

3. **Git read-only**
   ```powershell
   git status, git log, git diff
   ```

## Does NOT Auto-Run (IDE limitation)

- `python -c "..."` (inline code) - always prompts
- Multi-command pipelines
- Commands with quotes in arguments

## Workaround for Import Tests

Instead of:
```powershell
python -c "from module import X; print('OK')"  # PROMPTS
```

Do this:
1. Create temp script: `test_imports.py`
2. Run: `python test_imports.py`  # AUTO-RUNS
3. Delete script after

## User Preference

Focus interactions on:
- Big-picture decisions
- Bugs and features
- Architecture vision

NOT on:
- Routine verification
- File moves
- Simple tests

Auto-run all safe operations. Only prompt for destructive or external operations.
