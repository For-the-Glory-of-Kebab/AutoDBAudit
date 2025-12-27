# General Excel Requirements

**Status**: Uncompromisable Standards
**Scope**: Applies to ALL data sheets in the Audit Report.

## 1. Row Identity & Locking
*   **The ID Field (Column A)**:
    *   **Visibility**: Hidden.
    *   **Content**: Unique ID (UUID) for reliable retrieval/comparison.
    *   **Protection**: **LOCKED**. User cannot edit.
    *   **Consistency**: MUST be in Column A for every single sheet.
*   **Locking Mechanism**:
    *   Worksheets are protected by default.
    *   **Explicit Unlock**: Columns intended for user input (Justification, Notes, etc.) must be strictly *Unlocked* so specific ranges work while the rest of the sheet remains immutable.

## 2. Visual Indicators
*   **The Indicator Column (Column B usually)**:
    *   **Purpose**: Signals discrepancy status.
    *   **Values**:
        *   (Empty): Compliant / No Issue.
        *   `⏳`: Needs Review (Discrepancy found, no user input).
        *   `✓`: Exception Documented (Discrepancy accepted via Review Status/Justification).

## 3. Data Columns & Formatting
*   **Predetermined Values (Categorical)**:
    *   Columns like Status, Enabled/Disabled, Login Types, Roles.
    *   **Requirement**: MUST use **Drop-down Menus** (Data Validation).
    *   **Styling**: MUST have **Conditional Formatting** with dynamic icons/colors (e.g., Red Cross for Disabled, Green Tick for Enabled) to match the concept.
*   **Boolean Columns (Standard)**:
    *   Columns like "Enabled", "Is Disabled", "Clustered".
    *   **Values**: Must use **Tick (`✓`)** and **Cross (`✗`)**.
    *   **Logic**:
        *   Positive State (Good/Yes/Active): **Green Bold** (`✓`).
        *   Negative State (Bad/No/Inactive): **Red/Gray** (`✗`).
*   **Long Input Columns**:
    *   Columns: Justification, Notes, Purpose, Backup Path, Dates.
    *   **Width**: Reasonable (not excessively wide).
    *   **Alignment**: Center.
    *   **Wrapping**: **Enabled by default**.

## 4. Empty Sheet Behavior
*   **Rule**: Even if a sheet has 0 rows of data, the **Structure, Styles, and Conditional Formatting Rules** MUST be present. The user should see the headers and ready-to-use input styles immediately if they were to add a row manually.

## 5. Merged Cells
*   **Constraint**: Great care must be taken with merged cells (e.g., grouping Server/Instance names).
*   **Pitfall**: Ensure retrieval logic handles "empty value" for rows 2..N of a merged block. The system must treat the visual group as belonging to every row in that group logically.

## 6. Standard "Review Status" Column
*   **Purpose**: User feedback on discrepancies.
*   **Values (Dropdown)**:
    *   `⏳ Needs Review` (Yellow formatting).
    *   `✓ Exception` (Green formatting).
*   **Font**: Smaller, unobtrusive font.
