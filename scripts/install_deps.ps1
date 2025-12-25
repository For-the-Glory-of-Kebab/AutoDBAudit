Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
pip install jinja2 pywinrm --quiet
Pop-Location
