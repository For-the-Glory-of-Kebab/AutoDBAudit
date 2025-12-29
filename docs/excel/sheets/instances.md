# Instances Sheet Specification

**Entity**: Instance Inventory & Properties.

## Column Specifications
| Column | Header | Alignment | Wrapping | Special Logic / CF |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `_UUID` (Hidden) | - | - | Unique ID. |
| **B** | `Indicator` | Center | No | `⏳` Action / `✓` Waived. |
| **C** | `Config Name` | Center | No | - |
| **D** | `Server` | Center | No | **Merged**. (Server Group Banding). |
| **E** | `Instance` | Center | No | **Merged**. (Instance Group Banding). |
| **F** | `Machine Name` | Center | No | - |
| **G** | `IP Address` | Center | No | `127.0.0.1:1433`. |
| **H** | `Version` | Center | No | - |
| **I** | `Build` | Center | No | - |
| **J** | `Version Status` | Center | No | **CF**: `✅ PASS` (Green), `⚠️ WARN` (Orange), `❌ FAIL` (Red). |
| **K** | `SQL Year` | Center | No | - |
| **L** | `Edition` | Center | No | - |
| **M** | `Clustered` | Center | No | **Dropdown**: `✓` (Bold/Green), `✗` (Gray). |
| **N** | `HADR` | Center | No | **Dropdown**: `✓` (Bold/Green), `✗` (Gray). |
| **O** | `OS` | Center | No | - |
| **P** | `CPU` | Center | No | - |
| **Q** | `RAM` | Center | No | - |
| **R** | `Review Status` | Center | No | **Dropdown**: `Pending` (Gray), `Reviewed` (Green). |
| **S** | `Justification` | **Center** | **Yes** | User Input. |
| **T** | `Notes` | **Center** | **Yes** | User Input. |
| **U** | `Last Reviewed` | **Center** | **Yes** | Timestamp. |
