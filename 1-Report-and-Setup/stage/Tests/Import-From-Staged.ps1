param(
    [string]$ModulesRoot,
    [string[]]$ModulesToTry
)
$ErrorActionPreference = 'Stop'
$env:PSModulePath = $ModulesRoot
foreach ($m in $ModulesToTry) {
    try {
        Import-Module -Name $m -Force -ErrorAction Stop
        Write-Host "OK: $m"
    } catch {
        Write-Error "FAIL: $m -> $($_.Exception.Message)"
        exit 2
    }
}
