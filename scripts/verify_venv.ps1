# Verify that we're using venv's python and pytest
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1

Write-Host "=== VENV VERIFICATION ===" -ForegroundColor Cyan
Write-Host "Python path: $(Get-Command python | Select-Object -ExpandProperty Source)"
Write-Host "Pytest path: $(Get-Command pytest | Select-Object -ExpandProperty Source)"
Write-Host "Python version: $(python --version)"
Write-Host "=========================" -ForegroundColor Cyan

Pop-Location
