# Annotation & Compliance System

The "Annotation" system allows the user to overlay their intent (business context) onto the raw audit findings (technical reality). This is what turns a "List of Failures" into a "Compliance Report".

## Concepts

### 1. The Review Status Dropdown
Located in the "Review Status" column (standardized across sheets).
*   **Values**:
    *   `⏳ Needs Review`: (Default) The item is a discrepancy that has not been addressed.
    *   `✓ Exception`: The auditor explicitly accepts this discrepancy.
    *   (Empty): The item is compliant/passing, or ignored.

### 2. Justification (The Key to Compliance)
The "Justification" (or "Exception Reason") column is the **primary driver of compliance**.
*   **Rule**: If a row has a `FAIL` or `WARN` status, providing a **non-empty Justification** converts it to a "Documented Exception".
*   **Effect**:
    *   The row is counted as "Documented Exception" instead of "Active Issue".
    *   The `⏳` indicator changes to `✅`.
    *   The row color changes from Orange (Action) to Blue (Info).

### 3. Visual Indicators (Column B)
Most sheets have a narrow Column B containing a visual status icon.
*   `⏳` **(Action Needed)**:
    *   Means: The item is fundamentally non-compliant AND has no justification.
    *   Auditor Action: Must either Fix the issue (remediate) OR Document it (justify).
*   `✅` **(Documented/Pass)**:
    *   Means: The item is either technically passing OR has been justified.
    *   Auditor Action: None.
*   `❌` **(Critical)**:
    *   Means: High-risk failure (e.g., SA account active).
    *   Auditor Action: Immediate remediation recommended.

## Workflow Example: "Documenting an Exception"

1.  **Audit Finding**: `xp_cmdshell` is `1` (Enabled). Policy requires `0`.
    *   Sheet: `Configuration`
    *   Result: Row is marked `FAIL`. Column B shows `⏳`.
2.  **User Action**:
    *   User clicks "Review Status" -> Selects `✓ Exception`.
    *   User types in "Justification": *"Required for legacy backup job ABC-123"*.
    *   User saves Excel.
3.  **Sync**:
    *   Run `autodbaudit sync`.
    *   System detects the justification.
    *   Updates Database: Marks this specific finding as "Excepted".
    *   Updates Stats: "Active Issues" -1, "Documented Exceptions" +1.
    *   Regenerates Excel: Row now shows `✅` and has Blue background.

## Database Persistence
Annotations are stored in the `row_annotations` table in SQLite.
*   **Schema**:
    *   `entity_type`: (e.g., `login`)
    *   `entity_key`: (UUID or legacy key)
    *   `field_name`: (`justification`, `review_status`, `notes`)
    *   `field_value`: The text content.
