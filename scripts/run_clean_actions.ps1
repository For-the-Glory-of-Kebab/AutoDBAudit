# Wrapper to run clean_actions.py
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python scripts\clean_actions.py
Pop-Location
