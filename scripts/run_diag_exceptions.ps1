# Wrapper for exception diagnostic
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python scripts\diag_exceptions.py
Pop-Location
