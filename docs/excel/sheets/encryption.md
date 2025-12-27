# Encryption Sheet Specification

**Entity**: Keys and Certificates.

## Column Specifications
| Column | Header | Alignment | Wrapping | Special Logic / CF |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `Server` | Center | No | **Merged**. Group Banding. |
| **B** | `Instance` | Center | No | **Merged**. Group Banding. |
| **C** | `Database` | Center | No | **Merged**. Group Banding. |
| **D** | `Key Type` | Center | No | **Dropdown**: `SMK`, `DMK`, `TDE`. |
| **E** | `Key Name` | Center | No | - |
| **F** | `Algorithm` | Center | No | - |
| **G** | `Created` | **Center** | **Yes** | Date. |
| **H** | `Backup Status` | Center | No | **Dropdown**: `✓ Backed Up` (Grn), `⚠️ Not...` (Org). |
| **I** | `Status` | Center | No | **Dropdown**: `PASS` (Grn), `FAIL` (Red). |
| **J** | `Notes` | **Center** | **Yes** | User Input. |
