# AssetManager.psm1
# Handles "Field Kit" assembly based on manifest.json

function Get-BuildManifest {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        throw "Manifest not found: $Path"
    }
    return Get-Content $Path | ConvertFrom-Json
}

function Invoke-FieldKitAssembly {
    param(
        [string]$DistDir,
        [PSCustomObject]$Manifest,
        [string]$ProjectRoot
    )

    $KitName = $Manifest.OutputName
    $KitPath = Join-Path $DistDir $KitName
    
    # 1. Create clean kit structure
    if (Test-Path $KitPath) {
        Remove-Item $KitPath -Recurse -Force
    }
    New-Item -ItemType Directory -Path $KitPath | Out-Null
    
    # 2. Move Binary (The Brain)
    $ExeName = "AutoDBAudit.exe" # Determined by spec file, usually standard
    $SrcExe = Join-Path $DistDir $ExeName
    
    if (Test-Path $SrcExe) {
        Move-Item $SrcExe $KitPath
    }
    else {
        Write-BuildError "Executable not found in dist: $SrcExe"
        return $false
    }
    
    # 3. Process Assets from Manifest
    foreach ($asset in $Manifest.Assets) {
        $SourcePath = Join-Path $ProjectRoot $asset.Source
        $DestPath = Join-Path $KitPath $asset.Destination
        
        Write-Host "Processing Asset: $($asset.Source)" -ForegroundColor DarkGray
        
        # Ensure parent dest exists
        $DestParent = Split-Path $DestPath -Parent
        if (-not (Test-Path $DestParent)) {
            New-Item -ItemType Directory -Path $DestParent -Force | Out-Null
        }
        
        if (Test-Path $SourcePath) {
            if ((Get-Item $SourcePath).PSIsContainer) {
                # Directory Copy
                Copy-Item $SourcePath -Destination $DestParent -Recurse -Force
            }
            else {
                # File Copy
                Copy-Item $SourcePath -Destination $DestPath -Force
            }
        }
        else {
            if ($asset.Optional) {
                Write-BuildWarning "Optional asset skipped (missing): $($asset.Source)"
            }
            else {
                Write-BuildError "Required asset missing: $($asset.Source)"
                return $false
            }
        }
    }
    
    return $KitPath
}

Export-ModuleMember -Function Get-BuildManifest, Invoke-FieldKitAssembly
