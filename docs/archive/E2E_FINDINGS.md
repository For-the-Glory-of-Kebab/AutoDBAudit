# E2E Testing Findings & feedback

**Date:** 2025-12-12
**Phase:** Manual E2E Verification (Remediation & Sync)

## 1. Safety & Anti-Lockout Mechanisms 🛡️
**Severity:** CRITICAL
**Context:** Modifying the login used by the auditor (e.g., `king`) or the last remaining `sysadmin` can cause irreversible lockout. The current scripts comment out modifications to the connection user but need stronger visual warnings and logic checks.

**Requirements:**
-   **Connection User Alert:** If a script targets the current connection user (even if commented out), it must feature a high-visibility warning block (ASCII art/Banner).
    -   *Example:* "⚠️ WARNING: THIS IS YOUR CURRENT CONNECTION! ⚠️"
-   **Sysadmin Preservation:** Logic should arguably check if the target is the *last* enabled `sysadmin` before allowing a disable/permissions drop.
    -   *Implementation:* T-SQL safety check block at the start of the script:
        ```sql
        IF (SELECT COUNT(*) FROM sys.server_principals sp JOIN sys.server_role_members srm ON sp.principal_id = srm.member_principal_id WHERE srm.role_principal_id = SUSER_ID('sysadmin') AND sp.is_disabled = 0) <= 1
        BEGIN
            PRINT '❌ ABORTING: Attempt to disable/demote the last active sysadmin.';
            SET NOEXEC ON;
        END
        ```

## 2. SQL Error: Password Policy Enforcement 🐛
**Severity:** HIGH
**Context:** Enforcing `CHECK_POLICY` or `CHECK_EXPIRATION` on SQL Server 2025 (Docker) caused a "Severe error".
**Error Message:** `A severe error occurred on the current command. The results, if any, should be discarded.`
**Hypothesis:**
-   Possible bug in SQL Server 2025 Preview/RC?
-   Conflict with `CONTAINED` database users vs Server Logins?
-   Transaction handling issue in the generated script?
**Action:** Isolate the specific T-SQL statement causing this and create a minimal repro case.

## 3. Service Restart Notifications 📢
**Severity:** MEDIUM (UX)
**Context:** Certain remediation actions (e.g., changing `Login Auditing` mode, enabling `C2 Audit Tracing`) require a SQL Server service restart to take effect.
**Requirement:**
-   Scripts should detect if "Restart Required" changes were applied.
-   Print a summary at the end of the execution output.
    -   *Example command output:*
        ```text
        ✅ Applied: Enable Failed Login Auditing
        ⚠️  ACTION REQUIRED: SQL Server Service must be restarted for audit changes to take effect.
        ```
-   Add a generic T-SQL print block at the end of relevant scripts:
    ```sql
    PRINT '*****************************************************************'
    PRINT '⚠️  IMPORTANT: Service Restart Required for changes to take effect.'
    PRINT '*****************************************************************'
    ```

## 4. Sync Logic Issues (Placeholder)
**Context:** User reported a "multitude of issues" with `--sync`.
**Pending:** Awaiting user detail.
