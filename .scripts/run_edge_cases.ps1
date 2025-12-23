# Run specific failing tests with verbose output
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python -m pytest "tests/atomic_e2e/test_integration.py::TestEdgeCases" -v --tb=long 2>&1
Pop-Location
