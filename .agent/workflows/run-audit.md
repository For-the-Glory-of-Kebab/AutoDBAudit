---
description: Run the full CLI audit workflow for manual testing
---
// turbo-all

Run a complete audit cycle for testing:

1. Create a fresh audit:
```powershell
cd c:\Users\sickp\source\SQLAuditProject\AutoDBAudit
.\venv\Scripts\python.exe -m src.main --audit --new --name "Test Audit"
```

2. Run a sync (after making Excel edits):
```powershell
cd c:\Users\sickp\source\SQLAuditProject\AutoDBAudit
.\venv\Scripts\python.exe -m src.main --sync
```

3. Check the output:
```powershell
Get-ChildItem "output\*.xlsx" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
```
