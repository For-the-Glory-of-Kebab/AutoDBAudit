# Excel Interface Reference

This document details the visual and functional standards for the Excel User Interface.
**Source Code**: `src/autodbaudit/infrastructure/excel_styles.py`

## 1. Visual Standards

The application uses a strict "Premium" styling set to ensure professional reporting.

### Color Palette (Hex)
| Usage | Color | Hex | Visual |
| :--- | :--- | :--- | :--- |
| **Header BG** | Navy Blue | `203764` | Dark/Professional |
| **Pass** | Vibrant Green | `C6EFCE` | Background |
| **Fail** | Vibrant Red | `FFC7CE` | Background |
| **Warn/Exception** | Vibrant Yellow | `FFEB9C` | Background |
| **Info** | Light Blue | `BDD7EE` | Background |
| **Manual Input** | Light Gray | `F2F2F2` | Use for User columns |
| **Critical** | Bright Red | `FF0000` | White Text |

### Icons & Indicators
We use Unicode icons with text fallbacks.

| Icon | Name | Meaning | Fallback |
| :---: | :--- | :--- | :--- |
| **✓** | PASS | Compliant state | `[PASS]` |
| **✗** | FAIL | Non-compliant state | `[FAIL]` |
| **⚠** | WARN | Warning state | `[WARN]` |
| **⚡** | EXCEPTION | Documented Exception | `[EXCPT]` |
| **⏳** | ACTION | Action Needed (No Justification) | `[PEND]` |
| **🔒** | LOCKED | File/Row Locked | `[LOCK]` |
| **▶** | RUNNING | Service Running | `[RUN]` |
| **⏹** | STOPPED | Service Stopped | `[STOP]` |
| **🛡️** | SECURE | Security Feature Active | `[SEC]` |
| **👑** | PRIVILEGE| High Privilege Role | `[PRIV]` |

### Indicator Column (Column B)
The **Indicator** column is a Tri-State visual cue:
*   `⏳` (Hourglass): **Action Required**. Discrepancy found, no justification provided.
*   `✓` (Checkmark): **Exception Documented**. Discrepancy found, but waived/justified by user.
*   **Empty**: **Compliant**. No issues.

### Boolean Indicators (Tick/Cross)
For specific toggle columns (e.g., Clustered, HADR), use explicitly styled boolean symbols.

| Value | Visual | Meaning |
| :---: | :--- | :--- |
| **✓** | **Green Bold** | Enabled / Yes / Active |
| **✗** | **Red/Gray** | Disabled / No / Inactive |
*   **Validation**: These columns must use a Dropdown List containing exactly `✓, ✗`.

### Font Standards
*   **Main Font**: `Segoe UI` (Standard Windows UI font).
*   **Sizes**:
    *   Title: 18pt, Bold.
    *   Header: 11pt, Bold, White.
    *   Data: 10pt.
    *   Notes: 9pt, Italic, Gray.
*   **Monospace**: `Consolas` 10pt (used for code/config values).

---

## 2. Valid Data Values

When interacting with the Excel sheet (e.g., via specialized generic input columns), the system recognizes these normalized status values from the `Status` Enum.

**Enum Source**: `autodbaudit.infrastructure.excel_styles.Status`

*   `pass`
*   `fail`
*   `warn`
*   `exception`
*   `info`
*   `new`
*   `changed`
*   `critical`

---

## 3. Structural Definitions

### Column Definition (`ColumnDef`)
Every column in the report is generated from a `ColumnDef` object with these attributes:
*   `name`: Header text.
*   `width`: Width in chars (default 12).
*   `alignment`: Left, Center, or Right.
*   `is_manual`: **Important**. If True, the column is styled as "Input" (Gray BG) indicating it is safe for user editing.
*   `is_status`: If True, applies conditional formatting based on the `Status` enum rules above.

### 4. Row Grouping & Banding (Visual Hierarchy)
*   **Cascading Palette Rotation**: The report utilizes a **rotating palette of distinct pastel colors** (e.g., Mint, Lavender, Apricot, Sky) that cascades down the grouping hierarchy (e.g., Server → Instance → Database).
*   **Hierarchical Application**: The color rotation applies to each level of grouping. The first level (Server) rotates through the base palette. Nested levels (Instance, then Database) use tonal variations or sub-rotations to distinguish themselves within the parent block.
*   **Row Color Propagation**: The color of the **deepest grouped entity** designates the background color for the remainder of the row, ensuring a cohesive visual flow.
*   **Merging**: All groupable columns (`Server`, `Instance`, `Database`, etc.) are **vertically merged** to reduce visual noise.

### 5. Alignment & Wrapping
*   **Large Text Blocks** (Notes, Justification, Purpose, Findings): `Alignment: Center`, `Wrap Text: Yes`.
*   **Dates**: `Alignment: Center`, `Wrap Text: Yes`.
*   **Indicators**: `Alignment: Center`.
*   **Standard Text/Numbers**: `Center` alignment preferred unless strictly numerical lists.

---

## 4. Interaction Rules

*   **Locked Columns**: Most columns are locked to prevent accidental data corruption.
*   **Unlocked Columns**: Only columns marked `is_manual` (like Justification, Review Status, Notes) are unlocked.
*   **Hidden Column A (_UUID)**:
    *   **MUST NEVER BE MODIFIED.**
    *   Contains the 8-char hex UUID used for sync.
    *   Width: 0.
