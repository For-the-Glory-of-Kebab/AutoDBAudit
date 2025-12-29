param([Parameter(ValueFromRemainingArguments = $true)]$RemainingArgs)
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python -m pytest tests/real_db/L1_foundation/test_audit_creates_excel.py -v --tb=long 2>&1 | Tee-Object -FilePath output\test_output.txt
Pop-Location
