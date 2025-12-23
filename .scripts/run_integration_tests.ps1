# Run integration tests specifically
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python -m pytest tests/atomic_e2e/test_integration.py -v --tb=short
Pop-Location
