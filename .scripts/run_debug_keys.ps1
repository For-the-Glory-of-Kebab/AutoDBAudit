# Debug keys wrapper
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python .scripts\debug_keys.py 2>&1
Pop-Location
