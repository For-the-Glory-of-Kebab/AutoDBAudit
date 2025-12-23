# Run failed tests only with full output
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python -m pytest tests/atomic_e2e/test_universal.py tests/atomic_e2e/test_integration.py tests/atomic_e2e/test_stats.py tests/atomic_e2e/test_persistence.py -v --tb=line -x
Pop-Location
