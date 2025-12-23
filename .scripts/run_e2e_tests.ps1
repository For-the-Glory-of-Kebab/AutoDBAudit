# Run all E2E sheet tests
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python -m pytest tests/atomic_e2e/sheets/ --tb=no -q --ignore=tests/atomic_e2e/sheets/_archive/
Pop-Location
