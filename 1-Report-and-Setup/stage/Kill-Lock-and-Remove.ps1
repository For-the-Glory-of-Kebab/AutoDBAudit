param(
    [Parameter(Mandatory)]
    [string]$TargetFolder
)

Write-Host "🔍 Searching for processes locking $TargetFolder..."

# Optional: path to Sysinternals Handle.exe if you have it
$handleExe = "C:\Tools\handle.exe"

if (Test-Path $handleExe) {
    $locks = & $handleExe -accepteula $TargetFolder 2>$null | 
             Select-String -Pattern '^\s*\d+\s+[\w\.]+'

    foreach ($lock in $locks) {
        $parts = $lock.ToString().Trim() -split '\s+'
        $processId = [int]$parts[0]
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
            Write-Host "💀 Killed PID $processId"
        } catch {
            Write-Warning "Could not kill PID ${processId}: $_"
        }
    }
}
else {
    # WMI fallback — less precise but avoids external tools
    Get-Process | ForEach-Object {
        try {
            $modules = $_.Modules | ForEach-Object { $_.FileName } 2>$null
            if ($modules -match [regex]::Escape($TargetFolder)) {
                Stop-Process -Id $_.Id -Force -ErrorAction Stop
                Write-Host "💀 Killed PID $($_.Id)"
            }
        } catch {}
    }
}

# Now nuke the folder
try {
    Remove-Item $TargetFolder -Recurse -Force -ErrorAction Stop
    Write-Host "🗑 Removed $TargetFolder"
} catch {
    Write-Warning "Failed to remove ${TargetFolder}: $_"
}