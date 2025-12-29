# Remediation Engine

The Remediation Engine translates **Audit Findings** into executable **Fix Scripts** (T-SQL and PowerShell).

See docs/remediation/requirements.md for the concise, authoritative requirements (R1–R6) that the remediation engine must meet.

**Philosophy**: "Safe by Default, Powerful by Choice."

## Core Capabilities

### 1. Multi-Language Generation

* **T-SQL**: For SQL Server internal fixes (e.g., Disabling Logins, Revoking Permissions, Changing Configs).
* **PowerShell**: For OS-level fixes (e.g., Restarting Services, Registry Keys).

### 2. Aggressiveness Levels

The engine supports tiered "Aggressiveness" to balance safety vs. compliance.

| Level | Name | Behavior |
| :--- | :--- | :--- |
| **1** | **Safe (Commented)** | Generates scripts where specific remediations are **commented out** by default. Use this for initial reviews. |
| **2** | **Standard** | Safe defaults, but obvious fixes (like low-risk configs) might be active. High-risk items (like disabling users) remain commented. |
| **3** | **Active (Nuclear)** | Generates **uncommented, executable** scripts for almost everything. **Use with extreme caution.** |

### 3. Exception Awareness

The engine is **aware of your annotations**.

* If you marked a finding as `✓ Exception` (or provided a valid Justification), the remediation engine will **SKIP** generating a fix for it.
* This prevents "Fix -> Break -> Fix" loops.

### 4. Template-Based Generation

* **Technology**: Jinja2 Templating.
* **Location**: `src/autodbaudit/application/remediation/templates/`
* **Structure**:
  * `tsql/main_script.sql.j2`: Master T-SQL template.
  * `powershell/os_fixes.ps1.j2`: Master PowerShell template.

## Safety Mechanisms

* **Connecting User Protection**: The script ensures it never locks out the user running the remediation (e.g., `AUDITADMIN`).
* **Idempotency**: Scripts are designed to be re-runnable without errors (using `IF EXISTS...`).
* **Dry Run**: The CLI supports `--dry-run` to generate scripts without applying them (though usually we generate to file).

## Usage

Remediation is usually an output of the audit or sync command.

```bash
# Generate remediation scripts based on current audit
autodbaudit remediate --generate

# Generate with high aggressiveness
autodbaudit remediate --generate --level 3
```
