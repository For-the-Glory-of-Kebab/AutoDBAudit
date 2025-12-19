# Run pytest with optional arguments
# Usage: .\.scripts\pytest.ps1 [test_path] [extra_args]
param(
    [string]$TestPath = "tests/",
    [string]$ExtraArgs = "-v --tb=short"
)

$env:PYTHONPATH = (Get-Location).Path
& ".\venv\Scripts\python.exe" -m pytest $TestPath $ExtraArgs.Split(" ") 2>&1
