#!/usr/bin/env pwsh
# Runner script for AutoDBAudit - avoids compound commands
# Usage: .\run.ps1 --audit / --sync / --test / -m pytest ...
$env:PYTHONPATH = "$PSScriptRoot\src"

if ($args[0] -eq "--test") {
    # Run tests
    & "$PSScriptRoot\venv\Scripts\python.exe" -m pytest $args[1..$args.Length] 2>&1
}
else {
    # Run main app
    & "$PSScriptRoot\venv\Scripts\python.exe" src/main.py @args
}
