# Services Sheet Specification

**Entity**: SQL Services.

## Column Specifications
| Column | Header | Alignment | Wrapping | Special Logic / CF |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `_UUID` (Hidden) | - | - | Unique ID. |
| **B** | `Indicator` | Center | No | `⏳` Action / `✓` Waived. |
| **C** | `Server` | Center | No | **Merged**. (Server Group Banding). |
| **D** | `Instance` | Center | No | **Merged**. (Instance Group Banding). |
| **E** | `Service Name` | Center | No | - |
| **F** | `Type` | Center | No | - |
| **G** | `Status` | Center | No | **Dropdown**: `✓ Running` (Green), `✗ Stopped` (Red/Warn). |
| **H** | `Startup` | Center | No | **Dropdown**: `⚡ Auto` (Grn), `🔧 Manual` (Org), `⛔ Disabled` (Gry). |
| **I** | `Service Account` | Center | No | - |
| **J** | `Compliant` | Center | No | **Dropdown**: `✓` (Green), `✗` (Red). |
| **K** | `Review Status` | Center | No | **Dropdown**: `Pending` (Gray), `Reviewed` (Green). |
| **L** | `Justification` | **Center** | **Yes** | User Input. |
| **M** | `Last Reviewed` | **Center** | **Yes** | Timestamp. |
