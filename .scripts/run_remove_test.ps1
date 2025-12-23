# Run specific test with verbose output
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python -m pytest "tests/atomic_e2e/test_integration.py::TestExceptionLifecycle::test_I04_remove_exception_logs_removed" -v --tb=long 2>&1
Pop-Location
