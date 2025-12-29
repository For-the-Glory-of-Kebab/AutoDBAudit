# Backups Sheet Specification

**Entity**: Database Backup Status.

## Column Specifications
| Column | Header | Alignment | Wrapping | Special Logic / CF |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `_UUID` (Hidden) | - | - | Unique ID. |
| **B** | `Indicator` | Center | No | `⏳` Action / `✓` Waived. |
| **C** | `Server` | Center | No | **Merged**. Group Banding. |
| **D** | `Instance` | Center | No | **Merged**. Group Banding. |
| **E** | `Database` | Center | No | - |
| **F** | `Recovery Model` | Center | No | **Dropdown**: `🛡️ Full` (Grn), `⚡ Simple` (Org). |
| **G** | `Last Full Backup` | Center | No | Date / `NEVER`. |
| **H** | `Days Since` | Center | No | - |
| **I** | `Backup Path` | Center | No | - |
| **J** | `Size (MB)` | **Center** | No | - |
| **K** | `Status` | Center | No | **Dropdown**: `PASS` (Grn), `WARN` (Org), `FAIL` (Red). |
| **L** | `Review Status` | Center | No | **Dropdown**: `Pending` (Gray), `Reviewed` (Green). |
| **M** | `Justification` | **Center** | **Yes** | User Input. |
| **N** | `Last Reviewed` | **Center** | **Yes** | Timestamp. |
| **O** | `Notes` | **Center** | **Yes** | User Input. |
