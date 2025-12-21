# Wrapper script for running pytest autonomously
# Usage: .\scripts\run_pytest.ps1 [test_path] [extra_args]

param(
    [string]$TestPath = "tests\",
    [string]$ExtraArgs = ""
)

$ErrorActionPreference = "Continue"

# Activate venv and run pytest
& "$PSScriptRoot\..\venv\Scripts\Activate.ps1"
$cmd = "pytest $TestPath $ExtraArgs"
Invoke-Expression $cmd
