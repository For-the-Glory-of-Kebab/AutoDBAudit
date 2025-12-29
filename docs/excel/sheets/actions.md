# Actions Sheet Specification

**Entity**: Audit Change Log.

## Column Specifications
## Column Specifications
| Column | Header | Alignment | Wrapping | Special Logic / CF |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `ID` | Center | - | **Hidden**. Locked. Unique Action ID. |
| **B** | `Server` | Center | No | - |
| **C** | `Instance` | Center | No | - |
| **D** | `Category` | Center | No | **Dropdown**: See [Categories](#1-categories) below. |
| **E** | `Finding` | **Center** | **Yes** | Summary of the issue. |
| **F** | `Risk Level` | Center | No | **Dropdown**: See [Risk Levels](#2-risk-levels) below. |
| **G** | `Change Description` | **Center** | **Yes** | Detailed explanation of the event. |
| **H** | `Change Type` | Center | No | **Dropdown**: See [Change Types](#3-change-types) below. |
| **I** | `Detected Date` | **Center** | **Yes** | Date event was picked up by sync. |
| **J** | `Notes` | **Center** | **Yes** | User Input. |

---

## Detailed Value Definitions

### 1. Categories
Standardized grouping for audit findings.

| Category | Icon | Context |
| :--- | :---: | :--- |
| **SA Account** | `👤` | Status, naming, or disablement of the `sa` account. |
| **Server Logins** | `🔑` | Login creation, removal, orphan status, or password policy. |
| **Sensitive Roles** | `👑` | Changes to `sysadmin`, `securityadmin`, or `serveradmin` membership. |
| **Configuration** | `⚙️` | `sp_configure` changes (e.g., `xp_cmdshell`, `remote access`). |
| **Services** | `🛠️` | SQL Server service states (Running/Stopped) or startup types. |
| **Databases** | `🛢️` | Creation, deletion, recovery model, or trustworthy property. |
| **DB Users** | `👥` | Database-level user changes or orphan detection. |
| **DB Roles** | `🛡️` | `db_owner` or security role membership changes. |
| **Permissions** | `📜` | Explicit `GRANT` or `DENY` at scope or object level. |
| **Audit Settings** | `📝` | Changes to Login Auditing modes. |
| **Backups** | `💾` | Backup chain breaks, recovery model gaps, or missing backups. |
| **Encryption** | `🔐` | Key/Certificate changes, TDE status. |
| **Linked Servers** | `🔗` | Creation/removal of links or security context changes. |
| **Network** | `🌐` | Protocol (TCP/Named Pipes) or Port changes. |

### 2. Risk Levels
Quantifies the severity of the finding.

| Risk Level | Icon | Color Scheme | Meaning |
| :--- | :---: | :--- | :--- |
| **Critical** | `🔴` | **Red BG / White Text** | Immediate vulnerability (e.g., sa enabled, empty password). |
| **High** | `🟠` | **Orange BG / Black Text** | Significant exposure (e.g., xp_cmdshell enabled). |
| **Medium** | `🟡` | **Yellow BG / Black Text** | Best practice deviation (e.g., default port). |
| **Low** | `🟢` | **Green BG / Black Text** | Minor config cleanliness or informational. |
| **Info** | `ℹ️` | **Blue BG / Black Text** | Change record only (e.g., new database added). |

### 3. Change Types
Accurately categorizes the nature of the event in the Change Tracker.

| Change Type | Icon | Color Scheme | Conditional Formatting Logic | Definition |
| :--- | :---: | :--- | :--- | :--- |
| **Fixed** | `✅` | **Green BG** | `Cell Value == "Fixed"` | A finding that was **FAIL/WARN** in baseline/previous run is now **Pass**. |
| **Regression** | `❌` | **Red BG** | `Cell Value == "Regression"` | A finding that was **Pass** in baseline/previous run is now **FAIL/WARN**. |
| **New Issue** | `🆕` | **Yellow BG** | `Cell Value == "New Issue"` | A finding that **did not exist** in baseline/previous run and is **FAIL/WARN**. |
| **Exception Documented** | `🛡️` | **Blue BG** | `Cell Value == "Exception Documented"` | User provided a **Justification**, converting a finding to a waived state. |
| **Exception Removed** | `🗑️` | **Gray BG** | `Cell Value == "Exception Removed"` | A previously waived finding lost its justification or was manually reset. |
| **Configuration Change** | `📝` | **White BG** | `Cell Value == "Configuration Change"` | Value changed but **compliance status stayed the same** (e.g., RAM changed). |
