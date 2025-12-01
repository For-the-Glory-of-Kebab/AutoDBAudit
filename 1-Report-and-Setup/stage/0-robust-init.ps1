<#
.SYNOPSIS
  Robust module packer for offline use — saves modules + all dependencies, pins versions, verifies from bundle.
.DESCRIPTION
  - Resolves dependency tree via Find-Module -IncludeDependencies
  - Saves exact versions to ./PSModules (relative to script)
  - Verifies import in a clean GA PowerShell 7 process with PSModulePath restricted
  - Outputs a manifest and zip
#>

[CmdletBinding()]
param(
    [string[]]$ModulesToRoot = @(
        'SqlServer',
        'ImportExcel',
        'dbatools',
        'WindowsCompatibility'
    ),
    [switch]$AllowPrerelease = $false
)

$ErrorActionPreference = 'Stop'

# PSGallery + TLS sanity
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
if (-not (Get-PSRepository -Name 'PSGallery' -ErrorAction SilentlyContinue)) {
    Register-PSRepository -Default
}
Set-PSRepository -Name 'PSGallery' -InstallationPolicy Trusted

# Hard-pin to GA PS7
$gaPwsh = "C:\Program Files\PowerShell\7\pwsh.exe"
if (-not (Test-Path $gaPwsh)) {
    throw "GA PowerShell 7 not found at: $gaPwsh"
}

# Relative paths
$root = $PSScriptRoot
$modulesFolder = Join-Path $root 'PSModules'
$zipPath = Join-Path $root 'PSModules.zip'
$testsFolder = Join-Path $root 'Tests'
$manifestPath = Join-Path $root 'modules-manifest.json'

New-Item -ItemType Directory -Force -Path $modulesFolder, $testsFolder | Out-Null

# Resolve dependency graph and pin versions
$resolved = @()
foreach ($name in $ModulesToRoot) {
    $fmParams = @{
        Name                = $name
        Repository          = 'PSGallery'
        IncludeDependencies = $true
        ErrorAction         = 'Stop'
    }
    if ($AllowPrerelease) { $fmParams['AllowPrerelease'] = $true }

    Write-Host "Resolving dependencies for $name ..."
    $found = Find-Module @fmParams
    if (-not $found) { throw "Module not found: $name" }
    $resolved += $found
}

# Deduplicate, pick latest
$resolved = $resolved |
Sort-Object Name, Version -Descending |
Group-Object Name |
ForEach-Object { $_.Group | Select-Object -First 1 } |
Sort-Object Name

# ---------- Helpers ----------
function Get-ModuleManifestPath {
    param(
        [Parameter(Mandatory)][string]$VersionFolder,
        [Parameter(Mandatory)][string]$Name
    )
    $candidate = Join-Path $VersionFolder "$Name.psd1"
    if (Test-Path $candidate -PathType Leaf) { return $candidate }
    $any = Get-ChildItem -Path $VersionFolder -Recurse -Filter *.psd1 -File -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($any) { return $any.FullName }
    return $null
}

function Read-ManifestVersion {
    param([Parameter(Mandatory)][string]$ManifestPath)
    $data = Import-PowerShellDataFile -Path $ManifestPath
    $ver = $data.ModuleVersion
    if (-not $ver) { $ver = $data.Version }
    if (-not $ver) { return $null }
    return [string]$ver
}

function Get-TreeHash {
    param(
        [Parameter(Mandatory)][string]$Path,
        [string]$Algorithm = 'SHA256'
    )

    if (-not (Test-Path $Path)) { return $null }

    $files = Get-ChildItem -Path $Path -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -ne '.hash' } |               # exclude self-referential file
    Sort-Object { $_.FullName.Substring($Path.Length).TrimStart('\', '/') }

    if (-not $files) { return $null }

    $sb = New-Object System.Text.StringBuilder
    foreach ($f in $files) {
        $rel = $f.FullName.Substring($Path.Length).TrimStart('\', '/')
        $fh = (Get-FileHash -Path $f.FullName -Algorithm $Algorithm).Hash
        [void]$sb.AppendLine("$rel|$fh|$($f.Length)")
    }

    $bytes = [System.Text.Encoding]::UTF8.GetBytes($sb.ToString())
    $ms = New-Object System.IO.MemoryStream(, $bytes)
    try {
        (Get-FileHash -InputStream $ms -Algorithm $Algorithm).Hash
    }
    finally {
        $ms.Dispose()
    }
}

function Unblock-Tree {
    param([Parameter(Mandatory)][string]$Path)
    Get-ChildItem -Path $Path -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue
}

function Remove-Or-RenameFolder {
    param([Parameter(Mandatory)][string]$Path)
    try {
        if (Test-Path $Path -PathType Container) {
            Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
            return $true
        }
    }
    catch {
        try {
            $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
            $new = "$Path.corrupt_$stamp"
            Rename-Item -LiteralPath $Path -NewName (Split-Path -Leaf $new) -ErrorAction Stop
            Write-Warning "Renamed locked folder: '$Path' -> '$new'"
            return $true
        }
        catch {
            Write-Error "Unable to remove or rename '$Path'. $($_.Exception.Message)"
        }
    }
}

function Import-ByManifest {
    param([Parameter(Mandatory)][string]$ManifestPath)
    Import-Module -Name $ManifestPath -Force -ErrorAction Stop
}

function Save-Module-IfNeeded {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][version]$Version,
        [Parameter(Mandatory)][string]$Destination,
        [switch]$AllowPrerelease
    )

    $versionStr = $Version.ToString()
    $moduleBase = Join-Path $Destination $Name
    $versionPath = Join-Path $moduleBase $versionStr
    $hashFilePath = Join-Path $versionPath '.hash'
    $needsDownload = $true
    $reason = "Missing"

    if (Test-Path $versionPath -PathType Container) {
        try {
            $manifestPath = Get-ModuleManifestPath -VersionFolder $versionPath -Name $Name
            if ($manifestPath) {
                $localVersion = Read-ManifestVersion -ManifestPath $manifestPath
                if ($localVersion -and $localVersion -eq $versionStr) {
                    $actualHash = Get-TreeHash -Path $versionPath
                    Write-Host "DEBUG: Current tree hash for $Name $versionStr = $actualHash"
                    if (Test-Path $hashFilePath) {
                        Write-Host "DEBUG: Stored hash in file = $(Get-Content $hashFilePath -Raw)"
                    }
                    else {
                        Write-Host "DEBUG: No .hash file found"
                    }


                    if ($actualHash) {
                        if (Test-Path $hashFilePath -PathType Leaf) {
                            $expectedHash = Get-Content -LiteralPath $hashFilePath -Raw
                            if ($expectedHash -eq $actualHash) {
                                try {
                                    Import-ByManifest -ManifestPath $manifestPath
                                    Remove-Module -Name $Name -Force -ErrorAction SilentlyContinue
                                    Write-Host "✅ [$Name] $versionStr intact and importable — skipping download"
                                    $needsDownload = $false
                                }
                                catch {
                                    $reason = "Import failed: $($_.Exception.Message)"
                                }
                            }
                            else {
                                # Hash mismatch: try import; if OK, accept and refresh the hash (skip re-download)
                                try {
                                    Import-ByManifest -ManifestPath $manifestPath
                                    Remove-Module -Name $Name -Force -ErrorAction SilentlyContinue
                                    Write-Warning "[$Name] $versionStr hash mismatch but module imports OK — accepting on-disk copy and refreshing hash"
                                    Set-Content -LiteralPath $hashFilePath -Value $actualHash -Encoding ASCII
                                    $needsDownload = $false
                                }
                                catch {
                                    $reason = "Hash mismatch and import failed: $($_.Exception.Message)"
                                }
                            }
                        }
                        else {
                            # Missing hash file: try import; if OK, create it and skip download
                            try {
                                Import-ByManifest -ManifestPath $manifestPath
                                Remove-Module -Name $Name -Force -ErrorAction SilentlyContinue
                                Write-Warning "[$Name] $versionStr missing .hash but module imports OK — creating hash file"
                                Set-Content -LiteralPath $hashFilePath -Value $actualHash -Encoding ASCII
                                $needsDownload = $false
                            }
                            catch {
                                $reason = "Missing hash file and import failed: $($_.Exception.Message)"
                            }
                        }
                    }
                    else {
                        $reason = "No files to hash"
                    }
                }
                else {
                    $reason = "Version mismatch ($(if($localVersion){$localVersion}else{'unknown'}) vs $versionStr)"
                }
            }
            else {
                $reason = "Missing manifest"
            }
        }
        catch {
            $reason = "Manifest check error: $($_.Exception.Message)"
        }
    }
    else {
        $reason = "Version folder missing"
    }

    if ($needsDownload) {
        Write-Warning "⬇ [$Name] downloading $versionStr due to: $reason"

        if (Test-Path $versionPath -PathType Container) {
            if (-not (Remove-Or-RenameFolder -Path $versionPath)) {
                throw "Cannot proceed with download; cleanup failed for '$versionPath'."
            }
        }

        $attempt = 0
        do {
            try {
                $attempt++
                $params = @{
                    Name            = $Name
                    RequiredVersion = $Version
                    Repository      = 'PSGallery'
                    Path            = $Destination
                    Force           = $true
                    AcceptLicense   = $true
                    ErrorAction     = 'Stop'
                }
                if ($AllowPrerelease) { $params['AllowPrerelease'] = $true }

                Save-Module @params

                # Unblock and hash
                Unblock-Tree -Path $versionPath
                $postHash = Get-TreeHash -Path $versionPath
                if ($postHash) {
                    Set-Content -LiteralPath $hashFilePath -Value $postHash -Encoding ASCII
                    Write-Host "📦 [$Name] $versionStr downloaded and hash stored"
                }
                else {
                    Write-Warning "[$Name] Hash skipped — no valid files to hash (empty folder?)"
                }

                # Import check by manifest path
                $manifestPath = Get-ModuleManifestPath -VersionFolder $versionPath -Name $Name
                if ($manifestPath) {
                    try {
                        Import-ByManifest -ManifestPath $manifestPath
                        Remove-Module -Name $Name -Force -ErrorAction SilentlyContinue
                    }
                    catch {
                        Write-Warning "[$Name] Import check failed post-download: $($_.Exception.Message)"
                    }
                }
                else {
                    Write-Warning "[$Name] Manifest still not found after download."
                }

                return
            }
            catch {
                if ($attempt -lt 3) {
                    Write-Warning "Save-Module failed for $Name $versionStr. Retrying ($attempt/3)... $($_.Exception.Message)"
                    Start-Sleep -Seconds (2 * $attempt)
                }
                else {
                    throw
                }
            }
        } while ($true)
    }
}

# ---------- Download/Skip stage ----------
foreach ($m in $resolved) {
    Save-Module-IfNeeded -Name $m.Name -Version $m.Version -Destination $modulesFolder -AllowPrerelease:$AllowPrerelease
}

# ---------- Manifest output ----------
$manifest = [pscustomobject]@{
    CreatedUtc      = [DateTime]::UtcNow
    PSVersion       = $PSVersionTable.PSVersion.ToString()
    Host            = $PSVersionTable.PSEdition
    RootModules     = $ModulesToRoot
    AllowPrerelease = [bool]$AllowPrerelease
    Pinned          = $resolved | Select-Object Name, Version, ProjectUri, LicenseUri
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -Path $manifestPath -Encoding UTF8

# ---------- Clean import verification in separate GA PS7 ----------
$importTest = @'
param(
    [string]$ModulesRoot,
    [string[]]$ModulesToTry
)
$ErrorActionPreference = 'Stop'
$env:PSModulePath = $ModulesRoot
foreach ($m in $ModulesToTry) {
    try {
        Import-Module -Name $m -Force -ErrorAction Stop
        Write-Host "OK: $m"
    } catch {
        Write-Error "FAIL: $m -> $($_.Exception.Message)"
        exit 2
    }
}
'@
$importTestPath = Join-Path $testsFolder 'Import-From-Staged.ps1'
$importTest | Set-Content -Path $importTestPath -Encoding UTF8

$toTry = $ModulesToRoot
Write-Host "Verifying clean import from staged modules..."
$psi = @{
    FilePath         = $gaPwsh
    ArgumentList     = @(
        '-NoProfile',
        '-File', $importTestPath,
        '-ModulesRoot', $modulesFolder,
        '-ModulesToTry'
    ) + $toTry
    WorkingDirectory = $root
    Wait             = $true
    PassThru         = $true
}
$proc = Start-Process @psi
if ($proc.ExitCode -ne 0) {
    throw "Verification import failed. Check above output."
}
Write-Host "Verification import succeeded."

# ---------- Create ZIP ----------
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $modulesFolder '*') -DestinationPath $zipPath -Force
Write-Host "Bundle created at: $zipPath"