# Database Users Sheet Specification

**Entity**: User Accounts per Database.

## Column Specifications
| Column | Header | Alignment | Wrapping | Special Logic / CF |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `_UUID` (Hidden) | - | - | Unique ID. |
| **B** | `Indicator` | Center | No | `⏳` Action / `✓` Waived. |
| **C** | `Server` | Center | No | **Merged**. Group Banding. |
| **D** | `Instance` | Center | No | **Merged**. Group Banding. |
| **E** | `Database` | Center | No | **Merged**. Group Banding. |
| **F** | `User Name` | Center | No | - |
| **G** | `Type` | Center | No | **Dropdown**: `🪟 WINDOWS_USER`, `👤 SQL_USER`. |
| **H** | `Login Status` | Center | No | **Dropdown**: `✓ Mapped` (Grn), `🔧 System` (Gry), `⚠️ Orphaned` (Red). |
| **I** | `Mapped Login` | Center | No | - |
| **J** | `Compliant` | Center | No | **Dropdown**: `✓` (Grn), `⚠️ Review` (Org), `❌ GUEST` (Red). |
| **K** | `Review Status` | Center | No | **Dropdown**: `Pending` (Gray), `Reviewed` (Green). |
| **L** | `Justification` | **Center** | **Yes** | User Input. |
| **M** | `Last Reviewed` | **Center** | **Yes** | Timestamp. |
| **N** | `Notes` | **Center** | **Yes** | User Input. |
