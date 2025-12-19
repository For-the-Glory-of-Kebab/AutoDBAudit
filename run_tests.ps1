#!/usr/bin/env pwsh
# Run tests and capture output
$env:PYTHONPATH = "$PSScriptRoot\src"
& "$PSScriptRoot\venv\Scripts\python.exe" -m pytest tests\test_comprehensive_e2e.py -v --tb=short 2>&1 | Tee-Object -FilePath "test_output.txt"
Get-Content "test_output.txt"
