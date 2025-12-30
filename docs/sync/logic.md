# Sync Engine Logic Flow

The Synchronization Engine (`--sync`) is a precise, multi-phase process that reconciles the **Excel Report** with the **Database History**.

**Source Code**: `src/autodbaudit/application/sync_service.py`

**Prerequisites**:
- Run `prepare` command first to set up PowerShell remoting on target machines (see `docs/sync/prepare.md`)
- Ensure `Audit_Latest.xlsx` is not open in Excel

## Execution Phases

### Phase 1: Pre-flight Checks
Before doing anything, the engine ensures the environment is safe:
1.  **Baseline Check**: Ensures an audit baseline (Run ID 1) exists.
2.  **Finalize Check**: Aborts if the audit is already marked as `FINALIZED`.
3.  **File Lock Check**: Verifies that `Audit_Latest.xlsx` is NOT open in Excel. If it is, execution stops immediately to prevent data corruption.

### Phase 2: Read Annotations
*   **Source**: `Audit_Latest.xlsx`
*   **Action**: Reads all user inputs (Review Status, Justifications, Notes) from all sheets.
*   **Matching Strategy**:
    1.  **UUID Match**: Tries to find row by hidden Column A (UUID).
    2.  **Legacy Match**: Falls back to natural keys (e.g., Server+Instance+Login) if UUID is missing/invalid.
*   **Persistence**: Immediately saves these annotations to the SQLite `row_annotations` table.

### Phase 3: Re-Audit (The "Sync Run")
The engine performs a **fresh audit** of the targets.
*   **Action**: Connectivity is re-established, and all collectors run again.
*   **Data Collection**: Uses hybrid T-SQL + PowerShell approach.
* **T-SQL**: For DB-internal data (logins, configs, permissions).
* **PowerShell (PSRemote)**: For OS-level data (services, client protocols, registry). Prioritizes PS if available/reliable; gracefully falls back to T-SQL or cached data if PS fails or unavailable (e.g., Linux/Docker).
*   **Result**: A new "Sync Run" (Run ID > Baseline) is created in the database.
*   **Failure Handling**: If the re-audit crashes, the new run is marked as `FAILED`.

### Phase 4: Diffing
The engine compares the **Baseline** (or Previous) state vs. the **Current** state.
*   **Entities Compared**: Every login, config, permission, etc.
*   **States Detected**:
    *   `FIXED`: Issue was present in baseline, now gone (e.g., SA account disabled).
    *   `REGRESSION`: Issue was absent/fixed, now reappeared.
    *   `NEW`: Completely new issue not seen before.
    *   `SAME`: Issue persists unchanged.

### Phase 4b: Exception Detection
*   **Logic**: Checks if any *FAILING* item now has a "Justification" or "Exception" status in the annotations read in Phase 2.
*   **Result**: Items are marked as `EXCEPTION_ADDED`, `EXCEPTION_REMOVED`, or `EXCEPTION_UPDATED`.

### Phase 5: Action Recording
*   **Consolidation**: Merges strict Findings changes (Fixed/New) with Annotation changes (Exception Added).
*   **Priority**: A "Fixed" status trumps an "Exception" status (you don't need an exception for something you fixed).
*   **Persistence**: Writes to the `actions` table in SQLite.

### Phase 5b: State Cleanup
*   **Auto-Clear**: If an item is `FIXED`, its "Exception" status in the database is automatically cleared (to prevent stale exceptions if the issue returns). The "Justification" text is **preserved** for history.

### Phase 6: Stats Calculation
*   Aggregates counts for the Cover Sheet:
    *   Active Issues
    *   Documented Exceptions
    *   Compliant Items
    *   Change Stats (Fixed/New since last run)

### Phase 7: Write Excel Report
*   **Generation**: A fresh Excel file is generated from the *Current* audit data.
*   **Annotation Application**: The annotations read in Phase 2 are re-applied to the new rows.
*   **Visual Indicators**:
    *   Applies `✅` to documented exceptions.
    *   Applies `⏳` to active discrepancies.
    *   Applies `❌` to critical risks.
*   **Action Log**: The `Actions` sheet is populated with the consolidated history.

## Crucial Invariants
*   **Data Safety**: Annotations are read *before* the file is overwritten.
*   **Identity**: Rows are tracked by UUID to survive renaming/sorting.
*   **Concurrency**: File locking prevents partial writes.
