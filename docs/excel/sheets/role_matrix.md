# Role Matrix Sheet Specification

**Entity**: Pivoted View of Roles (Info Only).

## Column Specifications
| Column | Header | Alignment | Wrapping | Special Logic / CF |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `Server` | Center | No | **Merged**. Group Banding. |
| **B** | `Instance` | Center | No | **Merged**. Group Banding. |
| **C** | `Database` | Center | No | **Merged**. Group Banding. |
| **D** | `Principal Name` | Center | No | - |
| **E** | `Principal Type` | Center | No | **Dropdown**: `🪟 Windows`, `👤 SQL`. |
| **F+** | *[Roles]* | Center | No | **CF**: `✓` (Green), `👑 YES` (Red for db_owner). |
| **Last**| `Risk` | Center | No | **Dropdown**: `🔴 High`, `—`. **CF**. |
