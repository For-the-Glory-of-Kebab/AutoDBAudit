Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
pip install hypothesis allpairspy pytest-cov faker
Pop-Location
