# System Architecture

The application follows a **Domain-Driven Design (DDD)** inspired layered architecture.

## Layers

### 1. Domain Layer (`src/autodbaudit/domain`)
*   **Purpose**: Contains the "Business Logic" and "Source of Truth".
*   **Dependencies**: Zero (Pure Python).
*   **Key Components**:
    *   `sheet_registry.py`: Defines the Excel schema.
    *   `change_types.py`: Enums for FindingStatus (FIXED, REGRESSION, etc.).
    *   `entity_key.py`: Logic for normalizing and creating keys.

### 2. Application Layer (`src/autodbaudit/application`)
*   **Purpose**: Orchestrates use cases. "What the application DOES".
*   **Dependencies**: Domain.
*   **Key Components**:
    *   `audit_service.py`: Driver for the Audit process.
    *   `sync_service.py`: Driver for the Sync process.
    *   `remediation/`: Logic for generating fix scripts.
    *   `diff/`: Logic for comparing audit runs.

### 3. Infrastructure Layer (`src/autodbaudit/infrastructure`)
*   **Purpose**: Adapters for external systems. "How the application talks to the world".
*   **Dependencies**: Application (interfaces), Domain.
*   **Key Components**:
    *   `excel/`: **OpenPyXL** implementation for reading/writing reports.
    *   `sqlite/`: **SQLite3** implementation for persistence (`audit_history.db`).
    *   `system/`: Filesystem interactions.

### 4. Interface Layer (`src/autodbaudit/interface`)
*   **Purpose**: Entry points for the user.
*   **Dependencies**: Application.
*   **Key Components**:
    *   `cli.py`: **Typer** CLI definition. Defines commands (`audit`, `sync`, `remediate`).

## Key Data Flows

### The "Persistent Audit" Flow
1.  **CLI** invokes `SyncService`.
2.  **SyncService** calls `Infrastructure.Excel` to read annotations.
3.  **SyncService** calls `Application.Audit` to run a new scan.
4.  **Application.Diff** compares new scan vs `Infrastructure.SQLite` (History).
5.  **SyncService** calculates stats and changes.
6.  **SyncService** calls `Infrastructure.Excel` to write the new report.

## Design Principles
*   **Single Source of Truth**: Prioritize the Code (Registry) over config files for schema.
*   **Safe Defaults**: Remediation is commented by default.
*   **Lossless Sync**: Never delete user data (annotations) without explicit intent.

## Performance Architecture
*   **Parallel Execution**: The `AuditService` uses `concurrent.futures.ThreadPoolExecutor` to scan multiple SQL targets concurrently.
    *   **Max Workers**: Limited (default 5) to prevent resource exhaustion.
    *   **Thread Safety**:
        *   **SQLite**: Each thread uses a dedicated `HistoryStore` instance (connection isolation).
        *   **Excel Writer**: A `ThreadSafeWriterWrapper` protects the shared `EnhancedReportWriter` using a `threading.Lock`.
