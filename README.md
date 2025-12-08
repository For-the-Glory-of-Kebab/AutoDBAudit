# AutoDBAudit

**SQL Server Security Audit & Remediation Tool**

Self-contained, offline-capable tool for SQL Server security compliance auditing, discrepancy analysis, remediation script generation, and centralized hotfix deployment.

---

## Project Status

✅ **Phase 0 Complete** - Foundation & Setup  
✅ **Phase 1 Complete** - Excel Report Generation  
✅ **Phase 2 Complete** - CLI Integration & Data Collection  
⏳ **Phase 3 Planned** - Remediation & Analysis  
⏳ **Phase 4 Planned** - Hotfix Deployment & Polish  

---

## Features

### Excel Report Generation ✅
- **17 Sheets** with comprehensive security audit data
- **Server/Instance Grouping** with color rotation
- **Conditional Formatting** (PASS/FAIL/WARN colors)
- **Dropdown Validation** for all boolean/enum columns
- **Visual Icons** throughout for quick scanning

See [docs/excel_report_layout.md](docs/excel_report_layout.md) for complete sheet documentation.

### SQL Server Compatibility
- SQL Server 2008 R2 through 2022+
- Automatic version detection
- Version-specific query providers

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

### Run Audit (CLI)

```bash
# Set Python path and run audit
$env:PYTHONPATH="d:\Raja-Initiative\src"
python main.py --audit

# Output: output/sql_audit_YYYYMMDD_HHMMSS.xlsx (17 sheets)
```

### Generate Report (Test Mode)

```bash
# Set Python path and run test
$env:PYTHONPATH="d:\Raja-Initiative\src"
python test_multi_instance.py

# Output: output/full_audit_HHMMSS.xlsx
```

---

## Project Structure

```
d:\Raja-Initiative\
├── src/autodbaudit/           # Main Python package
│   ├── domain/               # Domain models
│   ├── application/          # Business logic
│   │   ├── audit_service.py  # Main orchestration
│   │   └── data_collector.py # Data collection logic
│   ├── infrastructure/       # External systems
│   │   ├── sql/              # SQL Server connectivity
│   │   │   ├── connector.py  # SqlConnector
│   │   │   └── query_provider.py  # Version-specific queries
│   │   ├── sqlite/           # SQLite persistence
│   │   │   ├── store.py      # HistoryStore
│   │   │   └── schema.py     # Schema definitions
│   │   ├── excel/            # Modular Excel package (21 files)
│   │   │   ├── writer.py     # Main writer (17 sheets)
│   │   │   └── *.py          # One file per sheet
│   │   └── excel_styles.py   # Styling definitions
│   └── interface/
│       └── cli.py            # Command-line interface
├── config/                   # Configuration files
├── docs/                     # Documentation
│   ├── PROJECT_STATUS.md     # Current state
│   ├── TODO.md               # Task tracker
│   ├── excel_report_layout.md # Sheet documentation
│   └── sqlite_schema.md      # Database schema
├── output/                   # Generated reports
└── db-requirements.md        # 28 security requirements
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [db-requirements.md](db-requirements.md) | 28 security requirements |
| [docs/excel_report_layout.md](docs/excel_report_layout.md) | Complete Excel sheet documentation |
| [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) | Current implementation status |
| [docs/TODO.md](docs/TODO.md) | Task tracker |
| [docs/sqlite_schema.md](docs/sqlite_schema.md) | SQLite database schema |

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

## Development

### Python Design Patterns Used

1. **Mixin Pattern** - Composable sheet functionality
2. **Strategy Pattern** - Version-specific query providers
3. **Dataclasses** - Typed configuration objects
4. **Context Managers** - Automatic resource cleanup
5. **Type Hints** - Static type checking support

### Code Style

- **PEP 8** compliant
- **4-space indentation**
- **snake_case** for functions/variables
- **PascalCase** for classes
- **Type hints** for function signatures
- **Docstrings** for all modules/classes/functions

---

## Testing

```bash
# Run setup tests
python test_setup.py

# Test SQL version detection
python test_sql_version.py

# Generate full multi-instance report
$env:PYTHONPATH="d:\Raja-Initiative\src"
python test_multi_instance.py
```

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

## License

Internal tool for SQL Server security auditing.

---

*Last updated: 2025-12-08*
