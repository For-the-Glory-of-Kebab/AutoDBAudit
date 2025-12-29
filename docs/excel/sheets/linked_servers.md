# Linked Servers Sheet Specification

**Entity**: Linked Server Definitions.

## Column Specifications
| Column | Header | Alignment | Wrapping | Special Logic / CF |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `_UUID` (Hidden) | - | - | Unique ID. |
| **B** | `Indicator` | Center | No | `⏳` Action / `✓` Waived. |
| **C** | `Server` | Center | No | **Merged**. Group Banding. |
| **D** | `Instance` | Center | No | **Merged**. Group Banding. |
| **E** | `Linked Server` | Center | **Yes** | - |
| **F** | `Provider` | Center | No | - |
| **G** | `Data Source` | Center | No | - |
| **H** | `RPC Out` | Center | No | **Dropdown**: `✓ Yes` (Org), `✗ No` (Grn). |
| **I** | `Local Login` | Center | No | - |
| **J** | `Remote Login` | Center | No | - |
| **K** | `Impersonate` | Center | No | **Dropdown**: `✓ Yes` (Org), `✗ No` (Grn). |
| **L** | `Risk` | Center | No | **Dropdown**: `🔴 HIGH`, `🟢 Normal`. |
| **M** | `Review Status` | Center | No | **Dropdown**: `Pending` (Gray), `Reviewed` (Green). |
| **N** | `Purpose` | **Center** | **Yes** | User Input. |
| **O** | `Justification` | **Center** | **Yes** | User Input. |
| **P** | `Last Reviewed` | **Center** | **Yes** | Timestamp. |
