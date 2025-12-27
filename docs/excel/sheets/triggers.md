# Triggers Sheet Specification

**Entity**: DDL/Logon Triggers.

## Column Specifications
| Column | Header | Alignment | Wrapping | Special Logic / CF |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `_UUID` (Hidden) | - | - | Unique ID. |
| **B** | `Indicator` | Center | No | `⏳` Action / `✓` Waived. |
| **C** | `Server` | Center | No | **Merged**. Group Banding. |
| **D** | `Instance` | Center | No | **Merged**. Group Banding. |
| **E** | `Scope` | Center | No | **Dropdown**: `SERVER` (Blue), `DATABASE`. |
| **F** | `Database` | Center | No | **Merged**. Group Banding. |
| **G** | `Trigger Name` | Center | No | - |
| **H** | `Event` | Center | No | - |
| **I** | `Enabled` | Center | No | **Dropdown**: `✓` (Grn), `✗` (Red). |
| **J** | `Review Status` | Center | No | **Dropdown**: `Pending` (Gray), `Reviewed` (Green). |
| **K** | `Notes` | **Center** | **Yes** | User Input. |
| **L** | `Justification` | **Center** | **Yes** | User Input. |
| **M** | `Last Reviewed` | **Center** | **Yes** | Timestamp. |
