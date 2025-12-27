param([Parameter(ValueFromRemainingArguments = $true)]$RemainingArgs)
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1

# Run all tests in tests/real_db/
# Use -v for verbose, --timeout to prevent hangs
# Tee output to file for analysis
python -m pytest tests/real_db/ -v --timeout=900 2>&1 | Tee-Object -FilePath output\full_realdb_test_suite.txt

Pop-Location
