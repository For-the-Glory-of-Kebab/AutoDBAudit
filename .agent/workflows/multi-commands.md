---
description: Combined multi-step commands that should never prompt
---
// turbo-all

Complex multi-command sequences that are SAFE:

1. Setup test workspace:
```powershell
New-Item -ItemType Directory -Path ".test_workspace\logs" -Force | Out-Null
New-Item -ItemType Directory -Path ".test_workspace\output" -Force | Out-Null  
New-Item -ItemType Directory -Path ".test_workspace\dumps" -Force | Out-Null
```

2. Clean and run tests:
```powershell
Remove-Item ".test_workspace\*" -Recurse -Force -ErrorAction SilentlyContinue
.\venv\Scripts\python.exe -m pytest tests/ --ignore=tests/e2e_robust -v --tb=short
```

3. Reset output and run audit:
```powershell
Remove-Item "output\*.xlsx" -Force -ErrorAction SilentlyContinue
.\venv\Scripts\python.exe -m src.main --audit --new --name "Test"
```

4. Run script, capture output:
```powershell
$output = .\venv\Scripts\python.exe -m pytest tests/ -v 2>&1
$output | Out-File ".test_workspace\logs\pytest.log"
$output | Select-Object -Last 20
```

All combined operations within the project are SAFE.
