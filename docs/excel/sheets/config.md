# Configuration Sheet Specification

**Entity**: sp_configure Settings.

## Column Specifications
| Column | Header | Alignment | Wrapping | Special Logic / CF |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `_UUID` (Hidden) | - | - | Unique ID. |
| **B** | `Indicator` | Center | No | `⏳` Action / `✓` Waived. |
| **C** | `Server` | Center | No | **Merged**. (Server Group Banding). |
| **D** | `Instance` | Center | No | **Merged**. (Instance Group Banding). |
| **E** | `Setting` | Center | No | - |
| **F** | `Current` | Center | No | - |
| **G** | `Required` | Center | No | - |
| **H** | `Status` | Center | No | **CF**: `✅ PASS` (Green), `❌ FAIL` (Red). |
| **I** | `Risk` | Center | No | **CF**: `Critical` (Red), `High` (Red), `Med` (Org), `Low` (Grn). |
| **J** | `Review Status` | Center | No | **Dropdown**: `Pending` (Gray), `Reviewed` (Green). |
| **K** | `Justification` | **Center** | **Yes** | User Input. |
| **L** | `Last Reviewed` | **Center** | **Yes** | Timestamp. |
