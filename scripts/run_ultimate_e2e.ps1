Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python -m pytest tests/ultimate_e2e/ -v --tb=short
Pop-Location
