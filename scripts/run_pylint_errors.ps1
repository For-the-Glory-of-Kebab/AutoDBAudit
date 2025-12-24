$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot
& "$projectRoot\venv\Scripts\Activate.ps1"
# Run pylint with specific message types: E=Errors, W=Warnings (skip C=Convention, R=Refactor, I=Info)
pylint src/autodbaudit --disable=C, R, I --output-format=text --reports=no --score=no 2>&1
