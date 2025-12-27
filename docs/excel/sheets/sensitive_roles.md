# Sensitive Roles Sheet Specification

**Entity**: Server Role Members (sysadmin, etc).

## Column Specifications
| Column | Header | Alignment | Wrapping | Special Logic / CF |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `_UUID` (Hidden) | - | - | Unique ID. |
| **B** | `Indicator` | Center | No | `⏳` Action / `✓` Waived. |
| **C** | `Server` | Center | No | **Merged**. (Server Group Banding). |
| **D** | `Instance` | Center | No | **Merged**. (Instance Group Banding). |
| **E** | `Role` | Center | No | **Dropdown**: `👑 sysadmin` (Red/High), `serveradmin`... |
| **F** | `Member` | Center | No | - |
| **G** | `Member Type` | Center | No | **Dropdown**: `🪟 Windows`, `🔑 SQL`. |
| **H** | `Enabled` | Center | No | **Dropdown**: `✓ Yes` (Green), `✗ No` (Gray). |
| **I** | `Review Status` | Center | No | **Dropdown**: `Pending` (Gray), `Reviewed` (Green). |
| **J** | `Justification` | **Center** | **Yes** | User Input. |
| **K** | `Last Reviewed` | **Center** | **Yes** | Timestamp. |
