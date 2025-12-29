# Server Logins Sheet Specification

**Entity**: Server-Level Logins.

## Column Specifications
| Column | Header | Alignment | Wrapping | Special Logic / CF |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `_UUID` (Hidden) | - | - | Unique ID. |
| **B** | `Indicator` | Center | No | `⏳` Action / `✓` Waived. |
| **C** | `Server` | Center | No | **Merged**. (Server Group Banding). |
| **D** | `Instance` | Center | No | **Merged**. (Instance Group Banding). |
| **E** | `Login Name` | Center | No | - |
| **F** | `Login Type` | Center | No | - |
| **G** | `Enabled` | Center | No | **Dropdown**: `✓ Yes` (Green), `✗ No` (Red). |
| **H** | `Password Policy` | Center | No | **Dropdown**: `✓ Yes` (Green), `✗ No` (Red), `N/A` (Gray). |
| **I** | `Default Database` | Center | No | - |
| **J** | `Review Status` | Center | No | **Dropdown**: `Pending` (Gray), `Reviewed` (Green). |
| **K** | `Justification` | **Center** | **Yes** | User Input. |
| **L** | `Last Reviewed` | **Center** | **Yes** | Timestamp. |
| **M** | `Notes` | **Center** | **Yes** | User Input. |
