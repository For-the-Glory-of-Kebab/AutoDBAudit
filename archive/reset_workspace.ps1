<#
.SYNOPSIS
    Resets the AutoDBAudit workspace to a clean state.
    "The Nuclear Option" for stuck processes and locked files.

.DESCRIPTION
    This script is designed to enable a fresh start during development/debugging sessions,
    especially when working with AI agents that may leave background processes or temp files.
    
    It performs the following actions:
    1. Forcefully terminates all Python processes (clearing file locks/zombies).
    2. Cleans the 'output' directory of generated reports and logs (preserves DB/dirs).
    3. Removes known temporary diagnostic scripts (repro_*.py, diagnose_*.py).
    4. Reports status with clear visual indicators.

.EXAMPLE
    .\reset_workspace.ps1

.NOTES
    Author: Antigravity
    Date:   2025-12-12
    Usage:  Run whenever tests stall, files are locked, or you want a blank slate.
#>

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   AutoDBAudit: Workspace Reset Tool      " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Kill Python Processes
Write-Host "`n[1/3] Terminating Python Processes..." -ForegroundColor Yellow
try {
    # Stop-Process throws unnecessary error if no process found, so utilize ErrorAction
    $procs = Get-Process -Name "python", "pythonw" -ErrorAction SilentlyContinue
    if ($procs) {
        $procs | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "    v Terminated $($procs.Count) process(es)." -ForegroundColor Green
    }
    else {
        Write-Host "    - No active Python processes found." -ForegroundColor Gray
    }
}
catch {
    Write-Host "    ! Failed to kill processes: $_" -ForegroundColor Red
}

# # 2. Clean Output Directory
# Write-Host "`n[2/3] Cleaning Output Directory..." -ForegroundColor Yellow
# $outputDir = Join-Path $PSScriptRoot "output"

# if (Test-Path $outputDir) {
#     # Remove Excel and Log files, but keep the folder structure
#     $files = Get-ChildItem -Path $outputDir -Include "*.xlsx", "*.log" -Recurse
#     if ($files) {
#         Remove-Item $files.FullName -Force -ErrorAction SilentlyContinue
#         Write-Host "    v Removed $($files.Count) file(s) from output/." -ForegroundColor Green
#     } else {
#         Write-Host "    - Output directory is already clean." -ForegroundColor Gray
#     }
# } else {
#     Write-Host "    - Output directory does not exist." -ForegroundColor Gray
# }

# # 3. Remove Diagnostic Debris
# Write-Host "`n[3/3] Removing Temporary Diagnostics..." -ForegroundColor Yellow
# $patterns = @("repro_*.py", "diagnose_*.py", "debug_*.py", "temp_*.py")
# $debris = Get-ChildItem -Path $PSScriptRoot -Include $patterns -File

# if ($debris) {
#     Remove-Item $debris.FullName -Force -ErrorAction SilentlyContinue
#     Write-Host "    v Removed $($debris.Count) diagnostic script(s)." -ForegroundColor Green
#     $debris.Name | ForEach-Object { Write-Host "      - $_" -ForegroundColor DarkGray }
# } else {
#     Write-Host "    - No diagnostic scripts found." -ForegroundColor Gray
# }

# Write-Host "`n==========================================" -ForegroundColor Cyan
# Write-Host "   Workspace Clean & Ready.               " -ForegroundColor Cyan
# Write-Host "==========================================" -ForegroundColor Cyan
