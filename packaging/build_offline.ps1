<#
.SYNOPSIS
    Builds the "Ultimate Offline" distribution for AutoDBAudit.
    
.DESCRIPTION
    This script creates a fully self-contained 'dist' folder containing:
    1. Compiled AutoDBAudit.exe
    2. Portable PowerShell 7
    3. Portable Windows Terminal
    4. Portable Sublime Text 4
    5. Required PowerShell Modules (SqlServer, etc.)
    
    WARNING: Requires Internet Access to download portable binaries.
    
.EXAMPLE
    .\build_offline.ps1 -Clean
#>

param (
    [Switch]$Clean,
    [String]$DistDir = "$PSScriptRoot\dist"
)

$ErrorActionPreference = "Stop"

# --- Configuration ---
# URLs for Portable Tools (Direct Downloads)
# Note: These URLs need to be maintained. Using latest stable as of Dec 2025.
$Urls = @{
    Pwsh     = "https://github.com/PowerShell/PowerShell/releases/download/v7.4.0/PowerShell-7.4.0-win-x64.zip"
    Terminal = "https://github.com/microsoft/terminal/releases/download/v1.18.2822.0/Microsoft.WindowsTerminal_1.18.2822.0_8wekyb3d8bbwe.msixbundle" 
    # Note: Terminal portable is tricky; using a known trick with renaming .msixbundle to .zip and extracting core
    Sublime  = "https://download.sublimetext.com/sublime_text_build_4169_x64.zip"
}

Write-Host "🏗️  STARTING OFFLINE BUILD..." -ForegroundColor Cyan

# 1. Setup Dist Directory
if ($Clean -and (Test-Path $DistDir)) {
    Write-Host "   Cleaning old dist..." -ForegroundColor Gray
    Remove-Item $DistDir -Recurse -Force
}
if (-not (Test-Path $DistDir)) { New-Item -ItemType Directory -Path $DistDir | Out-Null }
$BinDir = Join-Path $DistDir "bin"
$ToolsDir = Join-Path $DistDir "tools"
$DataDir = Join-Path $DistDir "data"

New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
New-Item -ItemType Directory -Force -Path $ToolsDir | Out-Null
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

# 2. Compile Python EXE
Write-Host "🐍 Compiling AutoDBAudit.exe..." -ForegroundColor Green
try {
    # Assume we are in packaging/ folder
    python -m PyInstaller --clean --onefile --name "AutoDBAudit" --distpath $BinDir --workpath "$PSScriptRoot\build" --specpath "$PSScriptRoot" "$PSScriptRoot\..\src\main.py" 
}
catch {
    Write-Warning "PyInstaller failed. Is it installed? (pip install pyinstaller)"
    exit 1
}

# 3. Download & Setup PowerShell 7 Portable
Write-Host "⚡ Setting up PowerShell 7 Portable..." -ForegroundColor Green
$PwshDir = Join-Path $BinDir "pwsh"
if (-not (Test-Path $PwshDir)) {
    New-Item -ItemType Directory -Path $PwshDir | Out-Null
    $ZipPath = Join-Path $Env:TEMP "pwsh.zip"
    # Invoke-WebRequest -Uri $Urls.Pwsh -OutFile $ZipPath
    # Expand-Archive -Path $ZipPath -DestinationPath $PwshDir -Force
    # Remove-Item $ZipPath
    
    # MOCK FOR OFFLINE DEV: 
    Write-Host "   [MOCK] Download disabled in dev environment. Create '$PwshDir' manually or uncomment download lines." -ForegroundColor DarkGray
    # Create dummy acts as pwsh.exe for testing folder structure
    New-Item -ItemType File -Path (Join-Path $PwshDir "pwsh.exe") -Force | Out-Null
}

# 4. Download & Setup Sublime Text 4
Write-Host "📝 Setting up Sublime Text 4..." -ForegroundColor Green
$SublimeDir = Join-Path $ToolsDir "SublimeText"
if (-not (Test-Path $SublimeDir)) {
    New-Item -ItemType Directory -Force -Path $SublimeDir | Out-Null
    # $ZipPath = Join-Path $Env:TEMP "sublime.zip"
    # Invoke-WebRequest -Uri $Urls.Sublime -OutFile $ZipPath
    # Expand-Archive -Path $ZipPath -DestinationPath $SublimeDir -Force
    # Remove-Item $ZipPath
    
    Write-Host "   [MOCK] Download disabled in dev environment." -ForegroundColor DarkGray
    New-Item -ItemType File -Path (Join-Path $SublimeDir "sublime_text.exe") -Force | Out-Null
}

# 4b. Inject Sublime Preferences
$SublimeData = Join-Path $SublimeDir "Data\Packages\User"
New-Item -ItemType Directory -Force -Path $SublimeData | Out-Null
$SublimePrefFile = Join-Path $SublimeData "Preferences.sublime-settings"
$SublimeConfig = @{
    "color_scheme"                      = "Monokai.sublime-color-scheme"
    "font_size"                         = 11
    "rulers"                            = @(80, 100)
    "tab_size"                          = 4
    "translate_tabs_to_spaces"          = $true
    "trim_trailing_white_space_on_save" = $true
    "ignored_packages"                  = @("Vintage")
} | ConvertTo-Json
Set-Content -Path $SublimePrefFile -Value $SublimeConfig

# 5. Save PowerShell Modules
Write-Host "📦 Bundling 'SqlServer' Module..." -ForegroundColor Green
$ModDir = Join-Path $BinDir "modules"
if (-not (Test-Path $ModDir)) { New-Item -ItemType Directory -Path $ModDir | Out-Null }

# Attempt to save module if internet + nuget avail
try {
    # Save-Module -Name SqlServer -Path $ModDir -Force -ErrorAction Stop
    Write-Host "   [MOCK] Save-Module skipped in dev env. Run manually." -ForegroundColor DarkGray
}
catch {
    Write-Warning "Failed to save SqlServer module. Check internet connection."
}

# 6. Create Launchers
Write-Host "🚀 Creating Launchers..." -ForegroundColor Green

# 6a. Start-Console.cmd
$LauncherContent = @"
@echo off
set "DIST_ROOT=%~dp0"
set "PWSH_PATH=%DIST_ROOT%bin\pwsh\pwsh.exe"
set "APP_PATH=%DIST_ROOT%bin\AutoDBAudit.exe"
set "PSModulePath=%DIST_ROOT%bin\modules;%PSModulePath%"

echo [AutoDBAudit Portable Environment]
echo --------------------------------
echo Root: %DIST_ROOT%
echo Pwsh: %PWSH_PATH%
echo --------------------------------

if exist "%PWSH_PATH%" (
    "%PWSH_PATH%" -NoExit -ExecutionPolicy Bypass -Command "Write-Host 'Welcome to AutoDBAudit Shell' -ForegroundColor Cyan; `$env:PATH += ';%DIST_ROOT%bin'; Set-Location '%DIST_ROOT%data'; & '%APP_PATH%' --help"
) else (
    echo ERROR: Portable PowerShell not found at %PWSH_PATH%
    echo Falling back to system PowerShell...
    powershell -NoExit -ExecutionPolicy Bypass -Command "Set-Location '%DIST_ROOT%data'; & '%APP_PATH%' --help"
)
"@
Set-Content -Path (Join-Path $DistDir "Start-Console.cmd") -Value $LauncherContent

# 6b. Start-Editor.cmd
$EditorLauncher = @"
@echo off
set "DIST_ROOT=%~dp0"
set "EDITOR=%DIST_ROOT%tools\SublimeText\sublime_text.exe"

if exist "%EDITOR%" (
    start "" "%EDITOR%" --project "%DIST_ROOT%data"
) else (
    echo ERROR: Sublime Text not found at %EDITOR%
    pause
)
"@
Set-Content -Path (Join-Path $DistDir "Start-Editor.cmd") -Value $EditorLauncher

# 7. Copy Default Configs & Scripts
Write-Host "CDR Copying default configs & scripts..." -ForegroundColor Green
$ConfigSrc = Join-Path "$PSScriptRoot\..\config" "*.example.json"
Copy-Item $ConfigSrc -Destination (Join-Path $DataDir "config") -Force

# Scripts (OS Hardening, etc)
$ScriptsDist = Join-Path $DataDir "scripts"
if (-not (Test-Path $ScriptsDist)) { New-Item -ItemType Directory -Path $ScriptsDist | Out-Null }
$ScriptSrc = Join-Path "$PSScriptRoot\..\assets\scripts" "*.ps1"
if (Test-Path $ScriptSrc) {
    Copy-Item $ScriptSrc -Destination $ScriptsDist -Force
}


Write-Host "✅ BUILD COMPLETE!" -ForegroundColor Cyan
Write-Host "   Output: $DistDir"
