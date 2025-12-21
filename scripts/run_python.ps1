# Wrapper script for running python commands autonomously
# Usage: .\scripts\run_python.ps1 "script.py" or .\scripts\run_python.ps1 "-c 'code'"

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Args
)

$ErrorActionPreference = "Continue"

# Activate venv and run python with all args
& "$PSScriptRoot\..\venv\Scripts\Activate.ps1"
$argString = $Args -join " "
$cmd = "python $argString"
Invoke-Expression $cmd
