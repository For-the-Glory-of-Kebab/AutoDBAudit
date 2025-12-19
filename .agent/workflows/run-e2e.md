---
description: Full test suite for sync engine E2E validation
---
// turbo-all

Run the comprehensive E2E tests for sync engine validation:

1. Run comprehensive e2e tests:
```powershell
cd c:\Users\sickp\source\SQLAuditProject\AutoDBAudit
.\venv\Scripts\python.exe -m pytest tests/test_comprehensive_e2e.py -v --tb=short 2>&1
```

2. If available, run the true CLI e2e test (requires SQL Server):
```powershell
cd c:\Users\sickp\source\SQLAuditProject\AutoDBAudit
.\venv\Scripts\python.exe -m pytest tests/test_true_cli_e2e.py -v --tb=short 2>&1
```

3. Review test output for failures. Check `output/` for generated reports.
