# Sync Engine & Change Tracking Logic

**Scope**: This document defines the functional requirements and logic for the **Synchronization Engine** (`--sync`), the **Change Tracker**, and their integration with the **Action Sheet**.

## 1. Core Architecture
The Sync Engine is the "Heartbeat" of the audit system. It is designed to be **idempotent**, **parallel**, and **resilient**.

### 1.1 Parallel Execution Model
To prevent timeouts ("SQL 60s limit") and optimize performance on large estates:
*   **Strategy**: **Per-Server Parallelism**.
*   **Concurrency**: Uses `ThreadPoolExecutor` to query multiple SQL Instances simultaneously.
*   **Isolation**: Each server connection is handled in its own scope. A timeout/failure on `Server A` **MUST NOT** impact `Server B`.
*   **Safety**: Database writes (SQLite) are serialized (locked) to prevent race conditions, while reads/queries occur in parallel.

### 1.2 The "Dual-Source" Truth
The engine reconciles two sources of truth on every run:
1.  **Live State**: The current configuration of the SQL Servers (queried via T-SQL/PowerShell).
2.  **User State**: The annotations (Notes, Justifications, Review Status) from the **Last Excel Report**.

---

## 2. Change Tracking "The Matrix"

The Change Tracker detects differences between the **Baseline** (or Last Sync) and the **Current Live State**. It calculates transitions based on **Compliance Status** and **User Input**.

### 2.1 State Definitions
*   **PASS**: Compliant. No finding.
*   **FAIL/WARN**: Discrepant. Finding exists.
*   **EXCEPTIONALIZED**: Finding exists (FAIL/WARN) but has a valid `Justification` or `Review Status`.
*   **MISSING**: Entity no longer exists (e.g., Login dropped).

### 2.2 Transition Matrix
This matrix defines *exactly* what happens when an entity moves from `State A` (Last) to `State B` (Current).

| Previous State | Current State | User Input (Excel) | **Resulting Action** | **Log Message** | **Indicator** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FAIL** | **PASS** | Any | **FIXED** | "Issue Resolved: [Finding]" | `✅` |
| **PASS** | **FAIL** | None | **REGRESSION** | "Regression Detected: [Finding]" | `❌` |
| **(None)** | **FAIL** | None | **NEW ISSUE** | "New Issue: [Finding]" | `🆕` |
| **FAIL** | **FAIL** | **Justification Added** | **EXCEPTION DOCUMENTED** | "Exception Note: [Note]" | `🛡️` |
| **FAIL (Excpt)** | **FAIL** | **Justification Removed**| **EXCEPTION REMOVED** | "Exception Cleared (Manual)" | `⏳` |
| **FAIL (Excpt)** | **PASS** | Any | **FIXED** | "Issue Resolved (was Exception)"| `✅` |
| **FAIL** | **FAIL** | None | **SAME** | (No Action Log Entry) | `⏳` |
| **PASS** | **PASS** | Any | **SAME** | (No Action Log Entry) | (Empty) |

### 2.3 Priority & Conflict Resolution
When multiple changes occur effectively at once (e.g., User adds a note AND fixes the issue):
1.  **FIX Trumps Exception**: If an item is Fixed (`FAIL` -> `PASS`), it is logged as **Fixed**. The user's note is preserved in the database for history, but the status becomes Compliant.
2.  **Regression is Absolute**: If an item goes `PASS` -> `FAIL`, it is a **Regression** regardless of previous history.
3.  **New vs. Existing**: An item is "New" only if its unique identity (`UUID` or `Natural Key`) was not present in the Baseline.

---

## 3. The Sync Workflow (Step-by-Step)

### Step 1: Pre-Flight & Locking
*   **Lock Check**: Checks if `Audit_Latest.xlsx` is locked/open. **Aborts** if true to prevent data corruption.
*   **Environment**: Validates database connectivity and schema version.

### Step 2: Ingest User State (Excel > DB)
*   **Action**: Reads the *current* `Audit_Latest.xlsx` (if exists).
*   **Logic**:
    *   Extracts `Justification`, `Notes`, `Review Status`, `Manual Dates`.
    *   Maps them to entities via `UUID` (Column A) or `Composite Key` (Fallback).
    *   **Persists** these updates to the `annotations` table in SQLite.
    *   *Critical*: This ensures user manual entry is "saved" before any re-generation happens.

### Step 3: Parallel Live Audit (DB > Runtime)
*   **Action**: Spawns threads to re-audit all scope targets.
*   **Output**: Generates a strictly in-memory representation of the *Current Live State*.

### Step 4: Differential Analysis (Runtime vs. Baseline)
*   **Action**: Iterates through every entity in the *Current Live State*.
*   **Comparison**: Fetches the corresponding entity from the **Baseline** (Run ID 1) or **Last Sync**.
*   **Calculation**: Applies the [Transition Matrix](#22-transition-matrix) to determine `Change Type`.

### Step 5: Action Logging (Runtime > DB)
*   **Action**: Writes `Action` records to the `action_log` table.
*   **Scope**: Only writes **State Changes** (Fixed, Regression, New, Exception Change). Static findings are not re-logged to keep noise low.

### Step 6: Excel Regeneration (Runtime + DB > Excel)
*   **Action**: Generates a **fresh** `Audit_Latest.xlsx`.
*   **Synthesis**:
    *   Writes *Current Live Data* rows.
    *   Re-hydrates *Annotations* (Notes/Justifications) from Step 2.
    *   Applies *Conditional Formatting* and *Indicators* based on the new computed state.
*   **Result**: A "Merged" report reflecting the latest reality + latest user comments.

---

## 4. Definitions of State Terms

### "Fixed"
*   **Definition**: A discrepancy that existed in the reference baseline but does not exist in the current run.
*   **Effect**: Clears `Review Status`. Preserves `Justification` (historical). Sets Indicator to Compliant.

### "Regression"
*   **Definition**: A finding that did NOT exist in the reference baseline (was Compliant) but DOES exist now.
*   **Effect**: Sets Indicator to `Action Required` (`⏳`).

### "Exception"
*   **Definition**: A finding is Non-Compliant (`FAIL`/`WARN`), BUT the user has provided a non-empty `Justification` or set `Review Status` to "Reviewed".
*   **Effect**: Sets Indicator to `Exception` (`🛡️` or `✓`). Item is counted as "Documented Exception" in stats, not "Active Issue".

### "New Issue"
*   **Definition**: An entity that was not tracked in the baseline (e.g., a newly created Login) and is Non-Compliant.
*   **Effect**: Sets Indicator to `Action Required` (`⏳`).
