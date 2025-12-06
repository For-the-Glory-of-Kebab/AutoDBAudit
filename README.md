# AutoDBAudit

**SQL Server Security Audit & Remediation Tool**

Self-contained, offline-capable tool for SQL Server security compliance auditing, discrepancy analysis, remediation script generation, and centralized hotfix deployment.

---

## Project Status

✅ **Phase 0 Complete** - Foundation & Setup  
🚧 **Phase 1 In Progress** - Core Audit Engine  
⏳ **Phase 2 Planned** - Remediation & Analysis  
⏳ **Phase 3 Planned** - Hotfix Deployment & Polish  

---

## Quick Start

### Prerequisites
- Python 3.11+ (3.14.0 recommended)
- Windows 10/11 or Windows Server 2016+
- ODBC Driver 17/18 for SQL Server (or fallback drivers)

### Installation

```bash
# 1. Clone/navigate to project
cd d:\Raja-Initiative

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
.\venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Verify setup
python test_setup.py
```

### Configuration

```bash
# Copy example configs
copy config\sql_targets.example.json config\sql_targets.json
copy config\audit_config.example.json config\audit_config.json

# Edit with your SQL Server details
notepad config\sql_targets.json
notepad config\audit_config.json
```

---

## Project Structure

```
d:\Raja-Initiative\
├── 1-Report-and-Setup/        # Legacy PowerShell implementation (reference)
├── src/                       # Python source code
│   ├── core/                  # Core audit engine, SQL connectivity
│   ├── remediation/           # Discrepancy analysis, script generation
│   ├── utils/                 # Utilities (logging, credentials)
│   └── hotfix/                # Hotfix deployment module
├── queries/                   # SQL query files (version-specific)
│   ├── sql2008/              # SQL Server 2008 R2 compatible
│   └── sql2019plus/          # SQL Server 2012+ (modern)
├── config/                    # Configuration files
├── output/                    # Generated reports and scripts
├── credentials/               # Encrypted credentials (gitignored)
├── main.py                    # CLI entry point
├── requirements.txt           # Python dependencies
└── venv/                      # Virtual environment (gitignored)
```

---

## Usage

### Check ODBC Drivers
```bash
python main.py --check-drivers
```

### Run Audit (When Implemented)
```bash
# Fresh audit
python main.py --audit --config config/audit_config.json

# Incremental (append to existing)
python main.py --audit --config config/audit_config.json \
  --append-to output/Acme_SQL_Audit_History.xlsx
```

### Generate Remediation Scripts
```bash
python main.py --generate-remediation --config config/audit_config.json
```

### Apply Remediation
```bash
python main.py --apply-remediation --scripts output/remediation_scripts/2025-12-02/
```

### Deploy Hotfixes
```bash
python main.py --deploy-hotfixes --hotfix-config config/hotfix_mapping.json
```

---

## Development

### Python Design Patterns Used

1. **src/ Layout** - Modern Python project structure
2. **Dataclasses** - Typed configuration objects
3. **Dependency Injection** - Testable, modular design
4. **Context Managers** - Automatic resource cleanup
5. **Type Hints** - Static type checking support
6. **Logging** - Structured application logging

### Code Style

- **PEP 8** compliant
- **4-space indentation**
- **snake_case** for functions/variables
- **PascalCase** for classes
- **Type hints** for function signatures
- **Docstrings** for all modules/classes/functions

### Adding New Features

```python
# Example: Adding a new utility module
# 1. Create file: src/utils/my_utility.py
# 2. Add docstring and type hints
# 3. Import in src/utils/__init__.py (if needed)
# 4. Use dependency injection in consuming code
```

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pyodbc | ≥5.0.0 | SQL Server connectivity (2008 R2 through 2022+) |
| openpyxl | ≥3.1.0 | Excel generation (icons, charts, formatting) |
| pywin32 | ≥306 | Windows DPAPI credential encryption |
| pyinstaller | ≥6.0.0 | Build standalone executable |

**No pandas/numpy** - Intentionally minimal for PyInstaller optimization

---

## Building Standalone Executable

```bash
# Activate venv
.\venv\Scripts\activate

# Build
pyinstaller --onefile --console main.py

# Output: dist/main.exe (~40-60 MB)
```

---

## Testing

```bash
# Run setup tests
python test_setup.py

# Run unit tests (when implemented)
pytest tests/

# Test SQL connection
python main.py --validate-config
```

---

## Architecture Decisions

### Why Python over PowerShell?
- Better project structure and modularity
- Superior library ecosystem (openpyxl, pyodbc)
- PyInstaller for true standalone deployment
- More maintainable for complex logic

### Why pip over UV/Poetry?
- Maximum compatibility with PyInstaller
- Industry standard, battle-tested
- Simpler for offline deployment scenarios

### Why venv over conda?
- Lightweight, built-in
- Cleaner PyInstaller builds
- Perfect for single-app deployment

### Why src/ layout?
- Prevents import issues
- Industry standard (2020+)
- Clearer separation of concerns

---

## Documentation

- [`project_overview.md`](C:\Users\920\.gemini\antigravity\brain\61f9fe26-7e99-440c-8ec9-2a1a287c6169\project_overview.md) - Complete requirements & legacy analysis
- [`implementation_plan.md`](C:\Users\920\.gemini\antigravity\brain\61f9fe26-7e99-440c-8ec9-2a1a287c6169\implementation_plan.md) - Technical roadmap & architecture
- [`python_for_dotnet_devs.md`](C:\Users\920\.gemini\antigravity\brain\61f9fe26-7e99-440c-8ec9-2a1a287c6169\python_for_dotnet_devs.md) - Python guide for .NET developers
- [`db-requirements.md`](db-requirements.md) - 22 security requirements

---

## License

Internal tool for SQL Server security auditing.

---

## Support

Contact: AutoDBAudit Team
