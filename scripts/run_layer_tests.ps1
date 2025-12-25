Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
Write-Host "Running build tests..."
python -m pytest tests/build/ -v --tb=short
Write-Host "Running layer tests..."
python -m pytest tests/layers/L3_sync/ -v --tb=short
Pop-Location
