Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python -m pytest tests/ --ignore=tests/archive -q
Pop-Location
