# Wrapper for annotation diagnostic
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python scripts\diag_annotations.py
Pop-Location
