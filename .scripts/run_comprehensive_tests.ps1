# Run all E2E tests including new comprehensive tests
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python -m pytest tests/atomic_e2e/ --tb=no -q --ignore=tests/atomic_e2e/sheets/_archive/ --ignore=tests/atomic_e2e/sheets/backups --ignore=tests/atomic_e2e/sheets/server_logins --ignore=tests/atomic_e2e/sheets/configuration --ignore=tests/atomic_e2e/sheets/databases --ignore=tests/atomic_e2e/sheets/permissions --ignore=tests/atomic_e2e/sheets/sensitive_roles --ignore=tests/atomic_e2e/sheets/services --ignore=tests/atomic_e2e/sheets/orphaned_users --ignore=tests/atomic_e2e/sheets/database_users
Pop-Location
