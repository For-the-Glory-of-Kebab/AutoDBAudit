# Run inline debug
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python .scripts\debug_inline.py 2>&1
Pop-Location
