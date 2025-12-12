# Engineering Standards & Architecture Guidelines

> "This codebase needs to be of utmost engineering quality and architecture relative to its scope."

All contributors must adhere to these standards to ensure the application is reliable, maintainable, and deployable as a single executable.

## 1. Reliability & Robustness
*   **No Fragile Paths**: Never use chains like `Path(__file__).parent.parent...`. Use the `autodbaudit.utils.resources` module for path resolution.
*   **Explicit Error Handling**: Do not fail silently. If an optional component (like an icon) fails, log a warning with a timestamp.
*   **Type Safety**: Use Pydantic/dataclasses for data structures. Avoid "mystery dicts".

## 2. Deployment Capability (PyInstaller)
The application is designed to be shipped as a single `.exe`.
*   **Asset Location**: Use `get_asset_path()` to locate files. This helper checks `sys._MEIPASS` (runtime temp dir for frozen apps) and the development project root.
*   **CWD Independence**: Do not assume the user's Current Working Directory is the application directory. Always resolve paths relative to the application/module location.

## 3. Architecture
*   **Layers**:
    *   `application/`: Orchestration logic (Service, Manager).
    *   `infrastructure/`: External I/O (Excel, SQL, SQLite).
    *   `domain/`: Core business logic and models.
    *   `utils/`: Shared generic helpers.
*   **Dependency Injection**: Pass configuration and resources into classes; avoid hardcoding global state where possible.

## 4. Documentation
*   Keep `docs/` synced with code changes.
*   Update `task.md` status accurately.
