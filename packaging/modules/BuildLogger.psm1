# BuildLogger.psm1
# Standardized logging for AutoDBAudit Build System

$Script:LogPrefix = "[AutoDBAudit Build]"

function Write-BuildInfo {
    param([string]$Message)
    Write-Host "$Script:LogPrefix [INFO] $Message" -ForegroundColor Cyan
}

function Write-BuildSuccess {
    param([string]$Message)
    Write-Host "$Script:LogPrefix [SUCCESS] $Message" -ForegroundColor Green
}

function Write-BuildWarning {
    param([string]$Message)
    Write-Host "$Script:LogPrefix [WARN] $Message" -ForegroundColor Yellow
}

function Write-BuildError {
    param([string]$Message)
    Write-Host "$Script:LogPrefix [ERROR] $Message" -ForegroundColor Red
}

function Write-BuildHeader {
    param([string]$Title)
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Magenta
    Write-Host "  $Title" -ForegroundColor White
    Write-Host ("=" * 60) -ForegroundColor Magenta
    Write-Host ""
}

Export-ModuleMember -Function Write-BuildInfo, Write-BuildSuccess, Write-BuildWarning, Write-BuildError, Write-BuildHeader
