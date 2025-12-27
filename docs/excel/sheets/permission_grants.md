# Permission Grants Sheet Specification

**Entity**: Explicit Permissions.

## Column Specifications
| Column | Header | Alignment | Wrapping | Special Logic / CF |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `_UUID` (Hidden) | - | - | Unique ID. |
| **B** | `Indicator` | Center | No | `⏳` Action / `✓` Waived. |
| **C** | `Server` | Center | No | **Merged**. Group Banding. |
| **D** | `Instance` | Center | No | **Merged**. Group Banding. |
| **E** | `Scope` | Center | No | **Dropdown**: `SERVER` (Blue), `DATABASE` (White). |
| **F** | `Database` | Center | No | **Merged**. Group Banding. |
| **G** | `Grantee` | Center | No | - |
| **H** | `Permission` | Center | No | e.g. `Control Server` (Red). |
| **I** | `State` | Center | No | **Dropdown**: `✅ GRANT` (Grn), `⛔ DENY` (Red). |
| **J** | `Entity Type` | Center | No | `OBJECT`, `DATABASE`. |
| **K** | `Entity Name` | Center | No | - |
| **L** | `Risk` | Center | No | **Dropdown**: `🔴 Warn`, `⛔ Blocked`. **CF**. |
| **M** | `Review Status` | Center | No | **Dropdown**: `Pending` (Gray), `Reviewed` (Green). |
| **N** | `Justification` | **Center** | **Yes** | User Input. |
| **O** | `Last Reviewed` | **Center** | **Yes** | Timestamp. |
| **P** | `Notes` | **Center** | **Yes** | User Input. |
