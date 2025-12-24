<#
.SYNOPSIS
    Enables PowerShell Remoting (WinRM) on this machine.
.DESCRIPTION
    Configures the Windows Remote Management (WinRM) service to allow
    Remote PowerShell connections. Required for the 'OS Remediation' feature.
    
    Actions:
    - Enables PSRemoting (Force)
    - Starts WinRM Service
    - Sets LocalAccountTokenFilterPolicy (if Workgroup)
.NOTES
    Run as Administrator.
#>

Write-Host "=== Configuring PowerShell Remoting ===" -ForegroundColor Cyan

# 1. Enable PSRemoting
Write-Host "[1] Enabling PSRemoting..."
try {
    Enable-PSRemoting -Force -ErrorAction Stop
    Write-Host "    [OK] PSRemoting enabled." -ForegroundColor Green
}
catch {
    Write-Host "    [ERR] Failed to enable PSRemoting: $_" -ForegroundColor Red
}

# 2. Check WinRM Service
Write-Host "`n[2] Verifying WinRM Service..."
$svc = Get-Service WinRM
if ($svc.Status -ne 'Running') {
    Start-Service WinRM
    Write-Host "    [OK] WinRM Started." -ForegroundColor Green
}
else {
    Write-Host "    [PASS] WinRM is running." -ForegroundColor Green
}

# 3. Workgroup Support (Optional but common for dev)
$isDomain = (Get-WmiObject Win32_ComputerSystem).PartOfDomain
if (-not $isDomain) {
    Write-Host "`n[3] Workgroup Configuration (LocalAccountTokenFilterPolicy)..."
    $path = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
    $name = "LocalAccountTokenFilterPolicy"
    
    if (-not (Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
    
    New-ItemProperty -Path $path -Name $name -Value 1 -PropertyType DWord -Force | Out-Null
    Write-Host "    [OK] Policy set for administrative shares." -ForegroundColor Green
}

Write-Host "`n=== Configuration Complete ===" -ForegroundColor Cyan
Write-Host "You can now target this machine using the 'os_remediation' feature."
