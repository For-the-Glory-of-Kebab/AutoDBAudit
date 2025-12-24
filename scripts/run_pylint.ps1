$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot
& "$projectRoot\venv\Scripts\Activate.ps1"
pylint src/autodbaudit --output-format=text --reports=no --score=no 2>&1 | Select-Object -First 100
