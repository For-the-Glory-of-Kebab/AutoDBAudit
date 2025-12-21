# Wrapper to run main CLI with --sync
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python src\main.py --sync
Pop-Location
