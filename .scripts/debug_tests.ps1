# Run tests with verbose output to see failures
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python -m pytest tests/atomic_e2e/ --tb=short --ignore=tests/atomic_e2e/sheets/_archive/ --ignore=tests/atomic_e2e/sheets/backups --ignore=tests/atomic_e2e/sheets/server_logins --ignore=tests/atomic_e2e/sheets/configuration --ignore=tests/atomic_e2e/sheets/databases --ignore=tests/atomic_e2e/sheets/permissions --ignore=tests/atomic_e2e/sheets/sensitive_roles --ignore=tests/atomic_e2e/sheets/services --ignore=tests/atomic_e2e/sheets/orphaned_users --ignore=tests/atomic_e2e/sheets/database_users 2>&1 | Select-String -Pattern "FAILED|AssertionError" -Context 0, 2
Pop-Location
