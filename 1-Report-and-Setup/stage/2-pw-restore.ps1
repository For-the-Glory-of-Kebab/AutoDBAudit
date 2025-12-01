<#
.SYNOPSIS
  Restore saved modules offline and verify they import from the installed path only.
  - Uses staged folder or expands PSModules.zip
  - Installs to global GA PS7 Modules when elevated, else to user Modules
  - Verifies import from the installed path in an isolated GA PS7 process
#>

[CmdletBinding()]
param(
  [string[]]$SkipModules = @('WindowsCompatibility')  # PS7 parsing issue on 1.0.0
)

$ErrorActionPreference = 'Continue'

# PSGallery/TLS sanity (in case restore script ever needs gallery metadata)
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
if (-not (Get-PSRepository -Name 'PSGallery' -ErrorAction SilentlyContinue)) {
    Register-PSRepository -Default
}
Set-PSRepository -Name 'PSGallery' -InstallationPolicy Trusted

$gaPwsh = "C:\Program Files\PowerShell\7\pwsh.exe"
if (-not (Test-Path $gaPwsh)) { throw "GA PowerShell 7 not found at: $gaPwsh" }

$root          = $PSScriptRoot
$stagedFolder  = Join-Path $root 'PSModules'
$zipPath       = Join-Path $root 'PSModules.zip'
$testsFolder   = Join-Path $root 'Tests'
$manifestPath  = Join-Path $root 'modules-manifest.json'

# Ensure test folder exists up-front
New-Item -ItemType Directory -Force -Path $testsFolder | Out-Null

# Ensure staged exists (prefer staged; else expand zip)
if (-not (Test-Path $stagedFolder)) {
  if (Test-Path $zipPath) {
    Write-Host "Expanding $zipPath ..."
    Expand-Archive -Path $zipPath -DestinationPath $stagedFolder -Force
  } else {
    throw "No staged folder or zip found. Expected at $stagedFolder or $zipPath"
  }
}

# Choose install target
$globalTarget = Join-Path $env:ProgramFiles 'PowerShell\7\Modules'
$userTarget   = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'PowerShell\Modules'
$isAdmin      = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).
                  IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$targetPath   = if ($isAdmin) { $globalTarget } else { $userTarget }

New-Item -ItemType Directory -Force -Path $targetPath | Out-Null

# Copy modules to target path
foreach ($modDir in Get-ChildItem $stagedFolder -Directory) {
  $dest = Join-Path $targetPath $modDir.Name
  if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
  Copy-Item $modDir.FullName $dest -Recurse -Force
  Get-ChildItem -Path $dest -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue
  Write-Host "Installed: $($modDir.Name) -> $targetPath"
}
if (-not $isAdmin) {
  Write-Warning "Installed to user scope ($targetPath) because process is not elevated."
}

# Determine which root modules to test
$modulesToTest = $null
if (Test-Path $manifestPath) {
  try {
    $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
    $rootMods = $manifest.RootModules
    if ($rootMods) { $modulesToTest = $rootMods }
    Write-Host "Manifest created: $($manifest.CreatedUtc) — will test $($modulesToTest -join ', ')"
  } catch { }
}
if (-not $modulesToTest) {
  $modulesToTest = (Get-ChildItem $stagedFolder -Directory).Name
}

# Apply skip list
if ($SkipModules) {
  $modulesToTest = $modulesToTest | Where-Object { $_ -notin $SkipModules }
}

# Build isolated import test
$importTest = @'
param(
  [string]$ModulesInstallRoot,
  [string[]]$ModulesToTry
)
$ErrorActionPreference = 'Stop'
$env:PSModulePath = $ModulesInstallRoot
foreach ($m in $ModulesToTry) {
  try {
    Import-Module -Name $m -Force -ErrorAction Stop
    Write-Host "OK: $m"
  } catch {
    Write-Error "FAIL: $m -> $($_.Exception.Message)"
    exit 3
  }
}
'@
$importTestPath = Join-Path $testsFolder 'Import-From-Installed.ps1'
$importTest | Set-Content -Path $importTestPath -Encoding UTF8

# Launch GA PS7 isolated
$psi = @{
  FilePath         = $gaPwsh
  ArgumentList     = @(
      '-NoProfile',
      '-File', $importTestPath,
      '-ModulesInstallRoot', $targetPath,
      '-ModulesToTry'
  ) + $modulesToTest
  WorkingDirectory = $root
  Wait             = $true
  PassThru         = $true
}
$proc = Start-Process @psi
if ($proc.ExitCode -ne 0) {
  throw "Offline restore verification failed. See console output above."
}
Write-Host "Offline restore verified from: $targetPath"