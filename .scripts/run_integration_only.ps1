# Run integration tests only
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python -m pytest tests/atomic_e2e/test_integration.py -v --tb=short 2>&1
Pop-Location
