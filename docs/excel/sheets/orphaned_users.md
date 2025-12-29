# Orphaned Users Sheet Specification

**Entity**: Users without Logins.

## Column Specifications
| Column | Header | Alignment | Wrapping | Special Logic / CF |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `_UUID` (Hidden) | - | - | Unique ID. |
| **B** | `Indicator` | Center | No | `⏳` Action / `✓` Waived. |
| **C** | `Server` | Center | No | **Merged**. Group Banding. |
| **D** | `Instance` | Center | No | **Merged**. Group Banding. |
| **E** | `Database` | Center | No | **Merged**. Group Banding. |
| **F** | `User Name` | Center | No | - |
| **G** | `Type` | Center | No | **Dropdown**: `🪟 Windows`, `🔑 SQL`. |
| **H** | `Status` | Center | No | **Dropdown**: `⚠️ Orphaned` (Org), `✓ Fixed` (Grn). |
| **I** | `Review Status` | Center | No | **Dropdown**: `Pending` (Gray), `Reviewed` (Green). |
| **J** | `Justification` | **Center** | **Yes** | User Input. |
| **K** | `Last Reviewed` | **Center** | **Yes** | Timestamp. |
