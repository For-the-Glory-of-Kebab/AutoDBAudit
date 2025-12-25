@echo off
REM ============================================================================
REM JSONC to JSON Converter - Strips comments from example files
REM ============================================================================
REM Usage: Just double-click this file in the config directory
REM
REM Creates:
REM   audit_config.json      (from audit_config.example.jsonc)
REM   sql_targets.json       (from sql_targets.example.jsonc)
REM   credentials\creds.json (from credentials.example.jsonc) [optional]
REM ============================================================================

echo.
echo === AutoDBAudit Config Setup ===
echo.

REM Check if we're in the config directory
if not exist "audit_config.example.jsonc" (
    echo ERROR: Run this script from the config directory!
    pause
    exit /b 1
)

REM Convert audit_config.example.jsonc -> audit_config.json
echo Converting audit_config.example.jsonc...
powershell -NoProfile -Command "(Get-Content 'audit_config.example.jsonc' -Raw) -replace '(?m)^\s*//.*$','' -replace '/\*[\s\S]*?\*/','' | ConvertFrom-Json | ConvertTo-Json -Depth 10 | Set-Content 'audit_config.json' -Encoding UTF8"
if %errorlevel% equ 0 (echo   OK: audit_config.json created) else (echo   WARN: Failed)

REM Convert sql_targets.example.jsonc -> sql_targets.json
echo Converting sql_targets.example.jsonc...
powershell -NoProfile -Command "(Get-Content 'sql_targets.example.jsonc' -Raw) -replace '(?m)^\s*//.*$','' -replace '/\*[\s\S]*?\*/','' | ConvertFrom-Json | ConvertTo-Json -Depth 10 | Set-Content 'sql_targets.json' -Encoding UTF8"
if %errorlevel% equ 0 (echo   OK: sql_targets.json created) else (echo   WARN: Failed)

REM Convert credentials.example.jsonc if exists
if exist "credentials.example.jsonc" (
    echo Converting credentials.example.jsonc...
    if not exist "credentials" mkdir credentials
    powershell -NoProfile -Command "(Get-Content 'credentials.example.jsonc' -Raw) -replace '(?m)^\s*//.*$','' -replace '/\*[\s\S]*?\*/','' | ConvertFrom-Json | ConvertTo-Json -Depth 10 | Set-Content 'credentials\creds.json' -Encoding UTF8"
    if %errorlevel% equ 0 (echo   OK: credentials\creds.json created) else (echo   WARN: Failed)
)

echo.
echo === DONE ===
echo.
echo Now edit the .json files with your actual values.
echo The .jsonc files are for reference only.
echo.
pause
