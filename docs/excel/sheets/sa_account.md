# SA Account Sheet Specification

**Entity**: SA Account Security Status.

## Column Specifications
| Column | Header | Alignment | Wrapping | Special Logic / CF |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `_UUID` (Hidden) | - | - | Unique ID. |
| **B** | `Indicator` | Center | No | `⏳` Action / `✓` Waived. |
| **C** | `Server` | Center | No | **Merged**. (Server Group Banding). |
| **D** | `Instance` | Center | No | **Merged**. (Instance Group Banding). |
| **E** | `Status` | Center | No | **CF**: `✅ PASS` (Green), `⚠️ WARN` (Orange), `❌ FAIL` (Red). |
| **F** | `Is Disabled` | Center | No | **Dropdown**: `✓` (Green), `✗` (Red). |
| **G** | `Is Renamed` | Center | No | **Dropdown**: `✓` (Green), `✗` (Red). |
| **H** | `Current Name` | Center | No | - |
| **I** | `Default DB` | Center | No | - |
| **J** | `Review Status` | Center | No | **Dropdown**: `Pending` (Gray), `Reviewed` (Green). |
| **K** | `Justification` | **Center** | **Yes** | User Input. |
| **L** | `Last Reviewed` | **Center** | **Yes** | Timestamp. |
| **M** | `Notes` | **Center** | **Yes** | User Input. |
