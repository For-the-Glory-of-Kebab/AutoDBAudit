# Credentials Folder

> **⚠️ SECURITY NOTE**: This folder is in `.gitignore` and will NOT sync to Git.

## Files Here

- `*.json` - Plain text credential files (for development only)
- `*.enc` - DPAPI-encrypted credential files (for production)

## Usage

### Option 1: Plain credentials file (development only)

Create a JSON file like `sql2025.json`:
```json
{
    "username": "sa",
    "password": "YourPassword123"
}
```

Then reference in `sql_targets.json`:
```json
{
    "id": "my-server",
    "server": "localhost",
    "port": 1444,
    "auth": "sql",
    "credential_file": "credentials/sql2025.json"
}
```

### Option 2: Environment variables

Set directly on your system:
```powershell
$env:SQL_USERNAME = "sa"
$env:SQL_PASSWORD = "YourPassword123"
```

### Option 3: Direct in config (testing only)

In `sql_targets.json`:
```json
{
    "auth": "sql",
    "username": "sa", 
    "password": "YourPassword123"
}
```

---

*This folder is safe - it's excluded from version control.*
