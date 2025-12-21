# Wrapper to run diagnostic
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python scripts\diag_actions.py
Pop-Location
