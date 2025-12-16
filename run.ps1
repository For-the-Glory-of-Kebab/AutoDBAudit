#!/usr/bin/env pwsh
# Runner script for AutoDBAudit - avoids compound commands
# $env:PYTHONPATH = "$PSScriptRoot\src"
python src/main.py @args
