
$env:PYTHONPATH = "src"
Write-Host "Starting Ultimate Sync Integrity Test..." -ForegroundColor Cyan

# Run pytest on the new test file
python -m pytest tests/ultimate_e2e/test_sync_integrity.py -v

if ($LASTEXITCODE -eq 0) {
    Write-Host "SUCCESS: Ultimate Sync Integrity Test Passed!" -ForegroundColor Green
}
else {
    Write-Host "FAILURE: Ultimate Sync Integrity Test Failed!" -ForegroundColor Red
}
