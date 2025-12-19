---
description: Run all unit tests with verbose output, auto-approved
---
// turbo-all

Run all tests excluding the incomplete e2e_robust suite:

```powershell
cd c:\Users\sickp\source\SQLAuditProject\AutoDBAudit
.\venv\Scripts\python.exe -m pytest tests/ --ignore=tests/e2e_robust -v --tb=short 2>&1
```

If tests fail, review the output. For test file issues, check the `tests/` directory.
