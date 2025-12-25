Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python -m pytest tests/ultimate_e2e/test_atoms.py -v --tb=short
Pop-Location
