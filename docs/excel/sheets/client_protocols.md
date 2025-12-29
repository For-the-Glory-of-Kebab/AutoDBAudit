# Client Protocols Sheet Specification

**Entity**: Network Protocol Configuration.

## Column Specifications
| Column | Header | Alignment | Wrapping | Special Logic / CF |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `_UUID` (Hidden) | - | - | Unique ID. |
| **B** | `Indicator` | Center | No | `⏳` Action / `✓` Waived. |
| **C** | `Server` | Center | No | **Merged**.Group Banding. |
| **D** | `Instance` | Center | No | **Merged**. Group Banding. |
| **E** | `Protocol` | Center | No | - |
| **F** | `Enabled` | Center | No | **Dropdown**: `✓ Yes`, `✗ No`. <br> **CF**: Green if Safe+Enabled; Red if Unsafe+Enabled (Named Pipes). |
| **G** | `Port` | Center | No | - |
| **H** | `Status` | Center | No | **Dropdown**: `✅ Compliant`, `⚠️ Needs Review`, `✅ Disabled`. |
| **I** | `Notes` | **Center** | **Yes** | User Input. |
| **J** | `Review Status` | Center | No | **Dropdown**: `Pending` (Gray), `Reviewed` (Green). |
| **K** | `Justification` | **Center** | **Yes** | User Input. |
| **L** | `Last Reviewed` | **Center** | **Yes** | Timestamp. |
