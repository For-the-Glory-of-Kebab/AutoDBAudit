# Wrapper to run sync command
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python src\main.py sync --audit-id 1
Pop-Location
