<#
.SYNOPSIS
    Modular Build Orchestrator for AutoDBAudit "Field Kit"
.DESCRIPTION
    1. Loads configuration from manifest.json
    2. Invokes PyInstaller build
    3. Assembles "Field Kit" structure (Configs, Tools, Resources)
    4. Packages final ZIP artifact
#>

param(
    [switch]$SkipCondaCheck
)

# Use automatic $PSScriptRoot
$ProjectRoot = Split-Path -Parent $PSScriptRoot

# Import Modules
Import-Module "$PSScriptRoot\modules\BuildLogger.psm1" -Force
Import-Module "$PSScriptRoot\modules\PyInstallerBuilder.psm1" -Force
Import-Module "$PSScriptRoot\modules\AssetManager.psm1" -Force
Import-Module "$PSScriptRoot\modules\Packager.psm1" -Force

try {
    Write-BuildHeader "Starting AutoDBAudit Build"
    Write-BuildInfo "Execution Root: $PSScriptRoot"


    # 1. Load Manifest
    $ManifestPath = Join-Path $PSScriptRoot "manifest.json"
    $Manifest = Get-BuildManifest -Path $ManifestPath
    Write-BuildInfo "Loaded Manifest: $($Manifest.AppName) v$($Manifest.Version)"

    # 2. Build Binary
    Write-BuildInfo "Phase 1: Compiling Binary..."
    $SpecFile = Join-Path $PSScriptRoot "autodbaudit.spec"
    
    # Run from Packaging Directory so relative paths (..) in spec file work correctly
    Push-Location $PSScriptRoot
    $SpecFile = "autodbaudit.spec" # Relative to CWD
    
    $AbsDist = Join-Path $ProjectRoot "dist"
    $AbsWork = Join-Path $ProjectRoot "build"
    
    if (-not (Invoke-PyInstallerBuild -SpecFile $SpecFile -DistPath $AbsDist -WorkPath $AbsWork -Clean)) {
        throw "PyInstaller Build Failed"
    }
    Pop-Location

    # 3. Assemble Field Kit
    Write-BuildInfo "Phase 2: Assembling Field Kit..."
    $DistDir = Join-Path $ProjectRoot "dist"
    
    $KitPath = Invoke-FieldKitAssembly -DistDir $DistDir -Manifest $Manifest -ProjectRoot $ProjectRoot
    if (-not $KitPath) {
        throw "Field Kit Assembly Failed"
    }
    Write-BuildSuccess "Field Kit Assembled at: $KitPath"

    # 4. Final Packaging (Zip)
    Write-BuildInfo "Phase 3: Creating Artifact..."
    $ZipName = "$($Manifest.OutputName)_v$($Manifest.Version).zip"
    $ZipPath = Join-Path $DistDir $ZipName
    
    if (Invoke-Packaging -SourcePath $KitPath -OutputPath $ZipPath) {
        Write-BuildSuccess "BUILD COMPLETE: $ZipPath"
        Write-BuildInfo "To test: Unzip and run AutoDBAudit.exe from a clean location."
    }
    else {
        throw "Packaging Failed"
    }

}
catch {
    Write-BuildError $_.Exception.Message
    exit 1
}
