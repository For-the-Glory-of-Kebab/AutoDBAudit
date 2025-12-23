# Run single failing test with verbose output
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python -m pytest "tests/atomic_e2e/test_universal.py::TestStateMatrix::test_SM01_justification_on_status[FAIL-True]" -v --tb=long -s
Pop-Location
