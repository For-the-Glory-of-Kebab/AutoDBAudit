# Developer Guide & Engineering Standards

**Version**: 1.2
**Role**: Guide for contributors and AI agents working on the codebase.

## 1. Architectural Principles

*   **Layered Architecture**: Strict separation of concerns.
    *   `domain/`: Business logic, State Machine (No I/O).
    *   `application/`: Orchestration (Sync Service, Action Detector).
    *   `infrastructure/`: External Systems (Excel, SQLite, SQL Server).
*   **Offline First**: Valid for air-gapped environments. No external dependencies beyond standard library + `openpyxl`.
*   **Single Binary**: Deploys as a PyInstaller `.exe`. Do not assume `cwd` is the app directory (use `get_asset_path`).

## 2. Engineering Standards

*   **Explicit Error Handling**: No silent failures. Log everything with context.
*   **Type Safety**: Use Type Hints everywhere. Avoid "mystery dicts".
*   **No Fragile Paths**: Use `autodbaudit.utils.resources` for file resolution.

## 3. Workflow for Agents

### 3.1 Do Not Touch
*   `db-requirements.md` (Without explicit instruction)
*   Legacy `1-Report-and-Setup/` folder

### 3.2 Command Execution
*   Use `python main.py --audit` for testing.
*   Use `.\scripts\run_e2e.ps1` for regression testing.

## 4. Key Files Map

| Component | Critical File |
| :--- | :--- |
| **State Machine** | `src/autodbaudit/domain/state_machine.py` |
| **Sync Logic** | `src/autodbaudit/application/sync_service.py` |
| **Excel Keys** | `docs/DATA_KEYS.md` |
| **DB Schema** | `src/autodbaudit/infrastructure/sqlite/schema.py` |

## 5. Development Setup

```powershell
# Activate Environment
.\venv\Scripts\Activate.ps1

# Run Linter
flake8 src/

# Run Tests
pytest tests/
```
