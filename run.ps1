#!/usr/bin/env pwsh
# Runner script for AutoDBAudit - avoids compound commands
$env:PYTHONPATH = "$PSScriptRoot\src"
python main.py @args
