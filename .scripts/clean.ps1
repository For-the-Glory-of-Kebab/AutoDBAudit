# Clean test workspace
Remove-Item ".test_workspace\*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "debug.log" -Force -ErrorAction SilentlyContinue
Remove-Item "output\*.xlsx" -Force -ErrorAction SilentlyContinue
Remove-Item "output\*.db" -Force -ErrorAction SilentlyContinue
Write-Host "Test workspace cleaned"
