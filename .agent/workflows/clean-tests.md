---
description: Clean test workspace and reset test environment
---
// turbo-all

Clean up the test workspace, removing logs, dumps, and temporary files:

```powershell
cd c:\Users\sickp\source\SQLAuditProject\AutoDBAudit
if (Test-Path ".test_workspace\logs") { Remove-Item ".test_workspace\logs\*" -Force -ErrorAction SilentlyContinue }
if (Test-Path ".test_workspace\output") { Remove-Item ".test_workspace\output\*" -Recurse -Force -ErrorAction SilentlyContinue }
if (Test-Path ".test_workspace\dumps") { Remove-Item ".test_workspace\dumps\*" -Force -ErrorAction SilentlyContinue }
if (Test-Path "debug.log") { Remove-Item "debug.log" -Force -ErrorAction SilentlyContinue }
Write-Host "Test workspace cleaned"
```
