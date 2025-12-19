# Run any Python code via venv
# Usage: .\.scripts\python.ps1 [-m module] [-c code] [script.py] [args...]
param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Args
)

$env:PYTHONPATH = (Get-Location).Path
& ".\venv\Scripts\python.exe" @Args 2>&1
