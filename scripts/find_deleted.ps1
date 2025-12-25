Push-Location $PSScriptRoot\..
git log --all --oneline -- "*simulate*" "*discrepanc*" | Select-Object -First 20
git log --all --oneline --diff-filter=D -- . | Select-Object -First 30
Pop-Location
