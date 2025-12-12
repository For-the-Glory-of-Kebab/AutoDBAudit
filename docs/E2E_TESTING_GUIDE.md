# End-to-End (E2E) Testing Guide

This guide walks you through a complete validation cycle ("0 to 100") of the AutoDBAudit tool, including simulating a version update.

## Prerequisites
-   SQL Server instances available (e.g., localhost).
-   `sql_targets.json` configured.

## Workflow Overview

1.  **Baseline Audit**: Capture the initial state (FAILs expected).
2.  **Generate Scripts**: Create remediation scripts.
3.  **Simulate Downgrade**: Artificial Step to "age" the database record.
4.  **Simulate Remediation**: Acknowledge that you applied scripts (or dry-run).
5.  **Sync (Re-Audit)**: Capture new state and verify detection of changes.

---

## Step 1: Baseline Audit (Run 1)

Start a fresh audit. This captures the current "real" state.

```powershell
python main.py --audit --new --name "E2E Test Run"
```
-   **Verify**: Check the generated Excel report in `output/audit_XXX/`.
-   **Verify**: SQLite DB created at `output/audit_history.db`.

## Step 2: Generate Remediation

Create the fix scripts.

```powershell
python main.py --generate-remediation
```
-   **Verify**: Scripts created in `output/audit_XXX/remediation/v001/`.
-   **Check**: Open a script and verify the new icons, headers, and secrets file.
-   **Optional**: Dry-run execution to check parsing.
    ```powershell
    python main.py --apply-remediation --dry-run
    ```

## Step 3: Simulate "Old State" (The Trick)

To verify that the system detects updates (e.g., version changes), we will artificially "downgrade" the history we just captured. This makes the *real* server look like an upgrade when we audit it again.

**Run the simulation script:**
```powershell
python src/simulate_update.py --downgrade
```
-   **Effect**: Modifies `output/audit_history.db`.
-   **Result**: The tool now believes your SQL instances are old (e.g., SQL 2017 RTM).

## Step 4: Apply Remediation (Real or Pretend)

**Option A: Real Fix**
Execute the scripts against your local SQL Server.
```powershell
python main.py --apply-remediation
```

**Option B: Pretend (For Testing Sync Logic Only)**
If you don't want to actually change your server configuration (e.g., disable xp_cmdshell), you can skip this. However, if you don't apply fixes, the Sync report will show "Still Failing" instead of "Fixed".
*Recommendation: Apply one safe fix (e.g., create a test user or dummy change) if possible, or just accept that things will be "Still Failing" but the Version will be "Updated" in the logs/report.*

## Step 5: Sync / Re-Audit (Run 2)

Run the sync command. This performs a new audit and diffs it against the history.

```powershell
python main.py --sync
```

**Expected Output:**
1.  **Version Change**: Because we downgraded the history in Step 3, the tool will verify the "real" version (which is newer) and update the database.
    -   *Note*: The CLI output won't scream "UPGRADE!" unless there is a specific Finding for it, but the Excel report (inventory sheet) on this new run will show the correct (newer) version, differing from the modified DB state.
2.  **Remediation Status**:
    -   **Fixed**: Any items you actually fixed in Step 4.
    -   **Still Failing**: Items you ignored.
    -   **New**: Any new issues introduced.

## Verification Checklist

-   [ ] **Command Output**: Did `main.py --sync` run without errors?
-   [ ] **Counts**: accurately reflect what you fixed vs ignored?
-   [ ] **Inventory**: Does the final status reflect the *real* version (undoing the simulation)?

---
*Tip: To reset everything, just delete the `output` directory and start over.*
