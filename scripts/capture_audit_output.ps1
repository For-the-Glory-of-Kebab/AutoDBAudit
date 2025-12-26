Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python -m autodbaudit.interface.cli audit 2>&1 | Out-File -FilePath output\audit_output.txt -Encoding utf8
Pop-Location
