# Database Roles Sheet Specification

**Entity**: Role Memberships.

## Column Specifications
| Column | Header | Alignment | Wrapping | Special Logic / CF |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `_UUID` (Hidden) | - | - | Unique ID. |
| **B** | `Indicator` | Center | No | `⏳` Action / `✓` Waived. |
| **C** | `Server` | Center | No | **Merged**. Group Banding. |
| **D** | `Instance` | Center | No | **Merged**. Group Banding. |
| **E** | `Database` | Center | No | **Merged**. Group Banding. |
| **F** | `Role` | Center | No | **Dropdown**: `👑 db_owner`, `⚙️ db_securityadmin`. **CF**. |
| **G** | `Member` | Center | No | - |
| **H** | `Member Type` | Center | No | **Dropdown**: `🪟 Windows`, `👤 SQL`, `📦 Role`. |
| **I** | `Risk` | Center | No | **Dropdown**: `🔴 High`, `🟡 Medium`, `🟢 Low`. **CF**. |
| **J** | `Review Status` | Center | No | **Dropdown**: `Pending` (Gray), `Reviewed` (Green). |
| **K** | `Justification` | **Center** | **Yes** | User Input. |
| **L** | `Last Reviewed` | **Center** | **Yes** | Timestamp. |
