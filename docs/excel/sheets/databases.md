# Databases Sheet Specification

**Entity**: Database Inventory & Status.

## Column Specifications
| Column | Header | Alignment | Wrapping | Special Logic / CF |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `_UUID` (Hidden) | - | - | Unique ID. |
| **B** | `Indicator` | Center | No | `⏳` Action / `✓` Waived. |
| **C** | `Server` | Center | No | **Merged**. Group Banding. |
| **D** | `Instance` | Center | No | **Merged**. Group Banding. |
| **E** | `Database` | Center | No | **Merged**. (Database Banding). |
| **F** | `Owner` | Center | No | - |
| **G** | `Recovery` | Center | No | **Dropdown**: `🛡️ Full`, `📦 Bulk-Logged`, `⚡ Simple`. <br> **CF**: Icons. |
| **H** | `State` | Center | No | **Dropdown**: `✓ Online` (Grn), `⛔ Offline` (Org), `⚠️ Suspect` (Red). |
| **I** | `Data (MB)` | **Center** | No | - |
| **J** | `Log (MB)` | **Center** | No | - |
| **K** | `Trustworthy` | Center | No | **Dropdown**: `✓ ON` (Red/Warn), `✗ OFF` (Green). |
| **L** | `Review Status` | Center | No | **Dropdown**: `Pending` (Gray), `Reviewed` (Green). |
| **M** | `Justification` | **Center** | **Yes** | User Input. |
| **N** | `Last Reviewed` | **Center** | **Yes** | Timestamp. |
| **O** | `Notes` | **Center** | **Yes** | User Input. |
