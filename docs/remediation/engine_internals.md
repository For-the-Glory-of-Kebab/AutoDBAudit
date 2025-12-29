# Remediation Engine Internals & Logic

**Scope**: This document defines the "Neurotic" details of the Remediation Engine (`--remediate`). It explains exactly how safe, idempotent, and exception-aware scripts are generated.

**Source Path**: `src/autodbaudit/application/remediation/`

### 1. High-Level Workflow
The engine follows a strict "Measure Twice, Cut Once" philosophy.

1.  **Context Loading**:
    *   Loads the designated Audit ID/Run.
    *   **Crucial**: Loads `annotations` from the database. This allows it to see which findings are "Exceptionalized" (Waived).
    *   *Rule*: **If a finding has a valid justification/exception, it is EXCLUDED from remediation.** We never automatically "fix" something a user explicitly waived.

2.  **Strategy Selection (Hybrid Fallback Engine)**:
    *   **Primary Pathway (Hybrid)**: For standard Windows Domain environments:
        *   **T-SQL Phase**: Uses ODBC for DB-level changes (`GRANT`, `sp_configure`).
        *   **PowerShell Phase**: Uses `Invoke-Command` for OS-level changes (`Services`, `Registry`, `Firewall`).
    *   **Fallback Pathway (Platform-Aware)**:
        *   *Trigger*: **Host Platform Detection**. The engine checks the `host_platform` of findings. If `!= Windows` (e.g. Linux, Docker container), it **automatically disables** OS-level script generation.
        *   *Behavior*:
            *   Executes **ALL** possible T-SQL fixes via the Python SQL Driver.
            *   **Completely Omitted**: `02_OS_Remediation.ps1` is either not generated or replaced with a "Manual Action" placeholder comment.
            *   **Safety**: This prevents Windows-specific PowerShell (Registry/Service calls) from crashing on Linux hosts.
            *   **Excel Update**: Sheets dependent on PS data remain in "Audit Only" or "Manual" state.

3.  **Script Location & Path Resolution (PyInstaller Safe)**:
    *   **Problem**: In frozen applications (PyInstaller), relative paths like `./scripts/` fail.
    *   **Solution**: The engine resolves template and output paths dynamically.
        *   *Dev Mode*: Uses `src/autodbaudit/...`.
        *   *Frozen Mode*: Uses `sys._MEIPASS` or the executable's directory.
    *   **Execution**: When running `--apply`, the CLI looks for scripts in the **User Output Directory**.

4.  **Template Rendering & Connectivity Header**:
    *   **TargetServer Injection**: To solve "IP vs Hostname" mismatch (where `@@SERVERNAME` != Connection String), the engine injects a `TargetServer: <ip_or_fqdn>` header into the generated SQL script.
    *   **Execution Logic**: The `ScriptExecutor` parses this header to determine *exactly* which connection string to use, ignoring the internal server name for connection purposes.
    *   **Exceptions**: Logic filters out findings with valid, documented exceptions (via Jinja2 logic).

5.  **Output Generation**:
    *   Writes `01_T-SQL_Remediation.sql`.
    *   Writes `02_OS_Remediation.ps1` (Windows Only).
    *   Writes `00_Rollback_Instructions.txt`.

---

## 2. Aggressiveness Levels (The Safety Valve)
The engine supports 3 levels of "Aggressiveness" which strictly control the *output code*.

### Level 1: SAFE (Default)
*   **Philosophy**: "Do No Harm. Inform Only."
*   **Behavior**: Generates the exact commands needed but **COMMENTS THEM OUT**.
*   **Example Output**:
    ```sql
    -- [SAFE MODE] Finding: xp_cmdshell enabled
    -- EXEC sp_configure 'xp_cmdshell', 0;
    -- RECONFIGURE;
    ```
*   **Use Case**: For DBAs who want to copy-paste specific fixes manually.

### Level 2: STANDARD
*   **Philosophy**: "Fix the low hanging fruit. warn on the rest."
*   **Behavior**:
    *   **Auto-Fixes**: Low-risk items (e.g., Guest User, Remote Access, Default Trace).
    *   **Comments Out**: High-risk items (e.g., Changing Auth Mode, Restarting Services).
*   **Use Case**: Standard hardening workflow.

### Level 3: ACTIVE (Nuclear)
*   **Philosophy**: "Compliance at all costs."
*   **Behavior**: Generates **executable code for ALL findings**.
*   **Safety Net**: Still respects **Exceptions**. If you waived it, it won't fix it, even in Level 3.

---

## 3. Template Logic & Implementation

### 3.1 Idempotency
All generated T-SQL is wrapped in `IF` blocks to prevent errors on re-run.

```sql
-- Pattern for removing a login
IF EXISTS (SELECT name FROM sys.server_principals WHERE name = 'rogue_user')
BEGIN
    DROP LOGIN [rogue_user];
    PRINT 'Dropped login [rogue_user]';
END
ELSE
    PRINT 'Login [rogue_user] already dropped.';
```

### 3.2 Service Restarts (The "Dangerous" Part)
Some changes (e.g., `xp_cmdshell` in some versions, or `Cross DB Chaining`) require a service restart.
*   **Logic**: The engine detects if a restart-pending config was changed.
*   **Handling**: It adds a specialized output block in the PowerShell script:
    ```powershell
    # WARN: Service restart required for changes to take effect:
    # - xp_cmdshell
    # Restart-Service -Name "MSSQLSERVER" -Force
    ```
*   **Rule**: The engine **NEVER** automatically issues a `Restart-Service` command in the main flow. It acts as a passive generator for these high-risk actions.

### 3.3 The "Exception" Gate
Inside the Jinja2 template (`rem_template.sql.j2`):

```jinja2
{% for finding in findings %}
    {% if finding.is_excepted %}
        -- [SKIPPED] Exception Documented by User: {{ finding.user }}
        -- Reason: {{ finding.justification }}
        -- Payload: EXEC sp_configure '{{ finding.key }}', ...
    {% else %}
        {{ finding.fix_command }}
    {% endif %}
{% endfor %}
```

---

## 4. Rollback Strategy
Every remediation generation is paired with a metadata snapshot.
*   **Snapshot**: The engine records the *current value* before generating the fix.
*   **Rollback Script**: It attempts to generate the inverse statement.
    *   *Value*: `1` -> Fix: `0` -> Rollback: `1`.
    *   *Existence*: `Exists` -> Fix: `DROP` -> Rollback: `CREATE`.
*   **Limitation**: Complex rollbacks (like re-creating a user with specific hash and SID) are "best effort" and heavily commented with warnings.

