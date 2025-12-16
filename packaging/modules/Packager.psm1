# Packager.psm1
# Handles final artifact creation (Compression)

function Invoke-Packaging {
    param(
        [string]$SourcePath,
        [string]$OutputPath
    )
    
    if (Test-Path $OutputPath) {
        Remove-Item $OutputPath -Force
    }
    
    Write-Host "Compressing $SourcePath -> $OutputPath" -ForegroundColor Gray
    Compress-Archive -Path "$SourcePath\*" -DestinationPath $OutputPath
    
    if (Test-Path $OutputPath) {
        return $true
    }
    return $false
}

Export-ModuleMember -Function Invoke-Packaging
