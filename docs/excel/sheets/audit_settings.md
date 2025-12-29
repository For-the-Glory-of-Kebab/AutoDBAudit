# Audit Settings Sheet Specification

**Entity**: Login Auditing Config.

## Column Specifications
| Column | Header | Alignment | Wrapping | Special Logic / CF |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `_UUID` (Hidden) | - | - | Unique ID. |
| **B** | `Indicator` | Center | No | `⏳` Action / `✓` Waived. |
| **C** | `Server` | Center | No | **Merged**. Group Banding. |
| **D** | `Instance` | Center | No | **Merged**. Group Banding. |
| **E** | `Setting` | Center | No | - |
| **F** | `Current Value` | Center | No | - |
| **G** | `Recommended` | Center | No | - |
| **H** | `Status` | Center | No | **CF**: `✅ PASS` (Green), `❌ FAIL` (Red). |
| **I** | `Review Status` | Center | No | **Dropdown**: `Pending` (Gray), `Reviewed` (Green). |
| **J** | `Justification` | **Center** | **Yes** | User Input. |
| **K** | `Last Reviewed` | **Center** | **Yes** | Timestamp. |
| **L** | `Notes` | **Center** | **Yes** | User Input. |
