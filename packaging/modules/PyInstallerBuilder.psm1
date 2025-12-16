# PyInstallerBuilder.psm1
# Encapsulates PyInstaller execution logic

function Invoke-PyInstallerBuild {
    param(
        [string]$SpecFile,
        [string]$DistPath,
        [string]$WorkPath,
        [switch]$Clean
    )

    if (-not (Test-Path $SpecFile)) {
        Write-Error "Spec file not found: $SpecFile"
        return $false
    }
    
    # Check if PyInstaller is available via python module (preferred for venv)
    $UsePythonModule = $true
    try {
        python -c "import PyInstaller" 2>$null
        if ($LASTEXITCODE -ne 0) {
            $UsePythonModule = $false
        }
    }
    catch {
        $UsePythonModule = $false
    }

    if (-not $UsePythonModule -and -not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
        Write-Error "PyInstaller not found (checked 'pyinstaller' in PATH and 'python -m PyInstaller'). Ensure pip install pyinstaller is run."
        return $false
    }

    $buildArgs = @($SpecFile)
    if ($DistPath) { $buildArgs += "--distpath"; $buildArgs += $DistPath }
    if ($WorkPath) { $buildArgs += "--workpath"; $buildArgs += $WorkPath }
    if ($Clean) {
        $buildArgs += "--clean"
        $buildArgs += "--noconfirm"
    }

    if ($UsePythonModule) {
        Write-Host "Executing: python -m PyInstaller $buildArgs" -ForegroundColor Gray
        python -m PyInstaller @buildArgs
    }
    else {
        Write-Host "Executing: pyinstaller $buildArgs" -ForegroundColor Gray
        pyinstaller @buildArgs
    }

    if ($LASTEXITCODE -eq 0) {
        return $true
    }
    return $false
}

Export-ModuleMember -Function Invoke-PyInstallerBuild
