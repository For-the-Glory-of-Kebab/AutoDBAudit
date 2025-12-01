<#
.SYNOPSIS
  Online module packager for offline use.
  Saves all required modules into ./PSModules relative to the script.
#>

# --- Config ---
$ModulesToSave = @(
    'SqlServer',
    'ImportExcel',
    'dbatools',
    'WindowsCompatibility'  # drop this if you don't need AD via PS7
)

# --- Paths (all relative to script) ---
$stagingRoot   = $PSScriptRoot
$modulesFolder = Join-Path $stagingRoot 'PSModules'
$zipPath       = Join-Path $stagingRoot 'PSModules.zip'

# --- Create staging folder ---
if (-not (Test-Path $modulesFolder)) {
    New-Item -ItemType Directory -Path $modulesFolder | Out-Null
}

# --- Save each module with dependencies ---
foreach ($m in $ModulesToSave) {
    Write-Host "Saving module: $m"
    Save-Module -Name $m -Repository PSGallery -Path $modulesFolder -Force
}

# --- Verify content ---
Write-Host "Modules staged under: $modulesFolder"
Get-ChildItem $modulesFolder -Directory | Select-Object Name, FullName

# --- Zip for transfer ---
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $modulesFolder '*') -DestinationPath $zipPath -Force
Write-Host "Zipped modules to: $zipPath"

# --- Test load from staging (without PSGallery) ---
Write-Host "Testing staged modules..."
$env:PSModulePath = "$modulesFolder"  # temporarily prepend path
foreach ($m in $ModulesToSave) {
    Import-Module $m -Force -ErrorAction Stop
    Write-Host "Loaded $m" -ForegroundColor Green
}
Write-Host "All staged modules import successfully."