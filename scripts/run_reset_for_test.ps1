# Wrapper for reset_for_test
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python scripts\reset_for_test.py
Pop-Location
