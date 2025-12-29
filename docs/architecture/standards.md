# Architecture & Engineering Standards

**"Uncompromisable Standards"** for the AutoDBAudit project.

## 1. Architectural Style: "Modern OOP"
We adopt a **C# / .NET Enterprise** style of organization within Python.

### Principles:
1.  **Strict Separation**: One Class per File (where reasonable).
    *   *Anti-Pattern*: `utils.py` with 50 helper functions.
    *   *Pattern*: `src/autodbaudit/infrastructure/excel/formatters/DateFormatter.py`
2.  **Deep Hierarchies**: Organize functionality into deep, meaningful namespace folders.
    *   `domain/` -> `security/` -> `logins/` -> `LoginValidator.py`
3.  **Strong Typing**: All function signatures MUST use Python 3.11+ type hints.
4.  **Interfaces (Abstract Base Classes)**: Define contracts in `domain/interfaces/` before implementing in `infrastructure/`.

## 2. Resilience First
The application must be **Indestructible**.

### Graceful Recovery
*   **No Crash Scenarios**: Errors (Network, Permission, File Lock) should be caught, logged, and surfaced gracefully. The app should *never* traceback to the console.
*   **State Preservation**: If a crash occurs 90% through a sync, the 90% of progress MUST be saved. Use atomic transactions for database writes.
*   **Idempotency**: All operations (Audit, Sync, Remediate) must be safe to run multiple times.

### Recovery Mechanisms
*   **Startup Cleanup**: The app checks for "Stale" runs (e.g., from power loss) on startup and marks them FAILED.
*   **File Locks**: Respect Excel file locks. Do not crash; prompt the user or fail fast with a clear message.

## 3. Performance Expectations
*   **Scale**: Must handle 50+ instances without UI freeze.
*   **Threading**: IO-bound operations (connecting to 12 servers) must happen in parallel.
*   **Memory**: Stream large datasets. Do not load 100k rows into RAM unless necessary.

## 4. Documentation
*   **Single Source of Truth**: The `docs/` folder is the bible. Code updates MUST update docs simultaneously.
*   **Traversability**: All docs must be linked from `DOCUMENTATION_HUB.md`.
