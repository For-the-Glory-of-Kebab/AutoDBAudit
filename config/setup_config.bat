@echo off
REM ============================================================================
REM JSONC to JSON Converter - Strips comments from example files
REM ============================================================================
REM Usage: Double-click this file OR run from config directory
REM
REM Creates:
REM   audit_config.json      (from audit_config.example.jsonc)
REM   sql_targets.json       (from sql_targets.example.jsonc)
REM   ..\credentials\credentials.json (from credentials.example.jsonc)
REM ============================================================================

echo.
echo === AutoDBAudit Config Setup ===
echo.

REM Check if we're in the config directory
if not exist "audit_config.example.jsonc" (
    echo ERROR: Run this script from the config directory!
    echo.
    echo Expected files:
    echo   - audit_config.example.jsonc
    echo   - sql_targets.example.jsonc
    echo   - credentials.example.jsonc
    pause
    exit /b 1
)

REM PowerShell function to strip JSONC comments and output valid JSON
set PS_CMD=^
$content = Get-Content -Path $args[0] -Raw; ^
$content = $content -replace '//.*',''; ^
$content = $content -replace '/\*[\s\S]*?\*/',''; ^
$content = $content -replace ',(\s*[}\]])','^$1'; ^
$json = $content ^| ConvertFrom-Json; ^
$json ^| ConvertTo-Json -Depth 20 ^| Set-Content -Path $args[1] -Encoding UTF8

echo Converting audit_config.example.jsonc...
powershell -NoProfile -Command "$content = Get-Content 'audit_config.example.jsonc' -Raw; $content = $content -replace '//.*',''; $content = $content -replace '/\*[\s\S]*?\*/',''; $content = $content -replace ',(\s*[}\]])', '$1'; $json = $content | ConvertFrom-Json; $json | ConvertTo-Json -Depth 20 | Set-Content 'audit_config.json' -Encoding UTF8"
if %errorlevel% equ 0 (
    echo   [OK] audit_config.json created
) else (
    echo   [FAIL] audit_config.json - check your JSONC syntax!
)

echo Converting sql_targets.example.jsonc...
powershell -NoProfile -Command "$content = Get-Content 'sql_targets.example.jsonc' -Raw; $content = $content -replace '//.*',''; $content = $content -replace '/\*[\s\S]*?\*/',''; $content = $content -replace ',(\s*[}\]])', '$1'; $json = $content | ConvertFrom-Json; $json | ConvertTo-Json -Depth 20 | Set-Content 'sql_targets.json' -Encoding UTF8"
if %errorlevel% equ 0 (
    echo   [OK] sql_targets.json created
) else (
    echo   [FAIL] sql_targets.json - check your JSONC syntax!
)

REM Convert credentials.example.jsonc to ../credentials/credentials.json
if exist "credentials.example.jsonc" (
    echo Converting credentials.example.jsonc...
    if not exist "..\credentials" mkdir "..\credentials"
    powershell -NoProfile -Command "$content = Get-Content 'credentials.example.jsonc' -Raw; $content = $content -replace '//.*',''; $content = $content -replace '/\*[\s\S]*?\*/',''; $content = $content -replace ',(\s*[}\]])', '$1'; $json = $content | ConvertFrom-Json; $json | ConvertTo-Json -Depth 20 | Set-Content '..\credentials\credentials.json' -Encoding UTF8"
    if %errorlevel% equ 0 (
        echo   [OK] ..\credentials\credentials.json created
    ) else (
        echo   [FAIL] credentials.json - check your JSONC syntax!
    )
) else (
    echo   [SKIP] credentials.example.jsonc not found
)

echo.
echo ============================================
echo   SETUP COMPLETE
echo ============================================
echo.
echo Next steps:
echo   1. Edit audit_config.json with your organization info
echo   2. Edit sql_targets.json with your SQL Server targets
echo   3. Edit ..\credentials\credentials.json with your passwords
echo.
echo The .example.jsonc files contain helpful comments for reference.
echo.
pause
