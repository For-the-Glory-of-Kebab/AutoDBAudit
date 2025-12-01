<#
.SYNOPSIS
  Inline purge — runs in current session, no extra window.
#>
if (-not (Test-Path (Join-Path $PSScriptRoot 'PSModules.zip'))) {
    Write-Warning "Bundle zip not found — purge will still run but no restore is possible until it’s recreated."
}

$ErrorActionPreference = 'Stop'

function Remove-Or-RenameFolder {
  param([Parameter(Mandatory)][string]$Path)
  try {
    if (Test-Path -LiteralPath $Path -PathType Container) {
      Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
      return $true
    }
  } catch {
    try {
      $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
      $new   = "$Path.corrupt_$stamp"
      Rename-Item -LiteralPath $Path -NewName (Split-Path -Leaf $new) -ErrorAction Stop
      Write-Warning "Renamed locked folder: '$Path' -> '$new'"
    } catch {
      Write-Error "Unable to remove or rename '$Path'. $($_.Exception.Message)"
    }
  }
}

$root          = $PSScriptRoot
$modulesFolder = Join-Path $root 'PSModules'
$manifestPath  = Join-Path $root 'modules-manifest.json'

# Which modules
$modulesToPurge = @()
if (Test-Path $manifestPath) {
  try {
    $mods = (Get-Content $manifestPath -Raw | ConvertFrom-Json).Pinned.Name
    if ($mods) { $modulesToPurge = $mods }
  } catch {}
}
if (-not $modulesToPurge -and (Test-Path $modulesFolder)) {
  $modulesToPurge = (Get-ChildItem $modulesFolder -Directory).Name
}

# Purge staged
if (Test-Path $modulesFolder) {
  Remove-Or-RenameFolder -Path $modulesFolder
  Write-Host "Purged staging at: $modulesFolder"
}

# Purge installed (optional)
$globalRoot = Join-Path $env:ProgramFiles 'PowerShell\7\Modules'
$userRoot   = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'PowerShell\Modules'
foreach ($name in $modulesToPurge) {
  foreach ($rootPath in @($userRoot,$globalRoot)) {
    $path = Join-Path $rootPath $name
    if (Test-Path $path) {
      Remove-Or-RenameFolder -Path $path
      Write-Host "Removed: $name from $rootPath"
    }
  }
}