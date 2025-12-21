# reset_corrupted_findings.ps1 - Fix corrupted findings with invalid 'Exception' status
$ErrorActionPreference = "Stop"

# Find database files
$dbPaths = @(
    "output\audit_001\audit_history.db",
    "output\audit_history.db"
)

$dbFile = $null
foreach ($path in $dbPaths) {
    if (Test-Path $path) {
        $dbFile = $path
        break
    }
}

if (-not $dbFile) {
    Write-Host "ERROR: No database file found" -ForegroundColor Red
    exit 1
}

Write-Host "Found database: $dbFile" -ForegroundColor Cyan

# Count corrupted findings
$countQuery = "SELECT COUNT(*) FROM findings WHERE status = 'Exception';"
$count = & sqlite3 $dbFile $countQuery 2>$null

if ($count -eq 0) {
    Write-Host "No corrupted findings found - database is clean!" -ForegroundColor Green
    exit 0
}

Write-Host "Found $count corrupted findings with status='Exception'" -ForegroundColor Yellow
Write-Host "Resetting to status='FAIL'..." -ForegroundColor Yellow

# Reset corrupted findings
$updateQuery = "UPDATE findings SET status = 'FAIL' WHERE status = 'Exception';"
& sqlite3 $dbFile $updateQuery 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "Successfully reset $count findings from 'Exception' to 'FAIL'" -ForegroundColor Green
    Write-Host "You can now run --sync to verify correct statistics" -ForegroundColor Cyan
}
else {
    Write-Host "ERROR: Failed to update database" -ForegroundColor Red
    exit 1
}
