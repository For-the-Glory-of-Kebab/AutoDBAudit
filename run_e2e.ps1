$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting AutoDBAudit Comprehensive E2E Tests..." -ForegroundColor Cyan

# Check for venv
if (-not (Test-Path "venv")) {
    Write-Error "Virtual environment 'venv' not found. Please install dependencies."
    exit 1
}

# 1. Run Logic Tests (Fast, mocked)
Write-Host "`n📌 Phase 1: Running Logic Tests (Mocked DB)" -ForegroundColor Yellow
& "venv\Scripts\python.exe" -m pytest tests\test_comprehensive_e2e.py -v
if ($LASTEXITCODE -ne 0) {
    Write-Error "Logic tests failed!"
    exit $LASTEXITCODE
}

# 2. Run True CLI E2E Tests (Slow, Real SQL)
Write-Host "`n📌 Phase 2: Running True CLI E2E Tests (Real SQL + Excel)" -ForegroundColor Yellow
Write-Host "   This will run --audit and multiple --sync commands."
& "venv\Scripts\python.exe" tests\test_true_cli_e2e.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ ALL E2E TESTS PASSED SUCCESSFULLY!" -ForegroundColor Green
    
    if (Test-Path "e2e_report.md") {
        Write-Host "`nReport generated at: e2e_report.md"
        Get-Content "e2e_report.md" | Select-Object -First 20
    }
}
else {
    Write-Error "`n❌ E2E Tests Failed!"
    exit $LASTEXITCODE
}
