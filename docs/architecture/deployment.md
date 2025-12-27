# Deployment & Build Architecture

**Scope**: This document defines the packaging, distribution, and runtime environment of the AutoDBAudit executable.
**Target Audience**: Developers & DevOps.

## 1. The PyInstaller Build
The application is packaged into a single-file executable (or a directory bundle) using **PyInstaller**.

### 1.1 The "Forbidden" Paths
**Critical Requirement**: The application **MUST NOT** assume that content files (templates, config defaults, documentation) exist in relative paths like `./src/` or `./templates/` when running as an EXE.

*   **Source Mode**: Code is at `src/autodbaudit/...`.
*   **Frozen Mode**: Code is extracted to a temp folder `sys._MEIPASS` (Single File) or exists in `./_internal/` (One Dir).

### 1.2 Resource Resolution Strategy
All file I/O for internal resources MUST use a `resource_path()` helper:

```python
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
```

**Common Failures to Avoid**:
1.  **Opening Documentation**: `open("./docs/README.md")` -> **FAIL** in EXE.
2.  **Loading Templates**: `Environment(loader=FileSystemLoader("./templates"))` -> **FAIL** in EXE.

---

## 2. Directory Structure Expectations

When the User runs the EXE, the following structure is expected/created:

```
[Installation Root]
├── AutoDBAudit.exe
├── sql_targets.json      (User Config)
├── secrets.json          (Encrypted Creds)
└── output/               (Generated Reports & Logs)
    ├── audit_1/
    │   ├── Audit_Report.xlsx
    │   └── remediation/   (Generated Scripts)
```

### 2.1 The "Missing Script" Bug
**Scenario**: User runs `autodbaudit remediate --apply`.
**Bug**: The app looks for scripts in `sys._MEIPASS/remediation` (internal temp) instead of `output/audit_X/remediation` (user disk).
**Fix**:
*   **Internal Resources** (Templates, defaults): Resolve via `sys._MEIPASS`.
*   **User Artifacts** (Generated SQL scripts, Reports): Resolve via `os.getcwd()` / `output/`.

**Invariance**: The CLI must always look for *generated* content in the *output* directory relative to where the user is executing the command, NOT relative to where the EXE binary sits (unless they are the same).

---

## 3. Remote Execution Constraints

### 3.1 PowerShell Wrapper
Because `Invoke-Command` and passing complex `PSCredential` objects from Python to a subprocess is fragile:
*   **Strategy**: Python generates a temporary "Wrapper Script" on the fly, saving it to disk, and executing *that* via `powershell.exe -File ...`.
*   **Why?**: This avoids "Double Quoting Hell" when passing JSON or complex strings to `-Command`.

### 3.2 TrustedHosts & IP Addresses
When running against IPs:
1.  **Check**: Is IP in `WSMan:\localhost\Client\TrustedHosts`?
2.  **Prompt**: If not, prompt user (or `--auto-trust`) to add it.
3.  **Execute**: Run the wrapper script.

---

## 4. Keying & Uniqueness
**Requirement**: Robust, Ultra-Unique Keys for Findings.

### 4.1 The Composite Key
Every finding row in the database references a `finding_key`.
*   **Format**: `v3_UUID(NAMESPACE_DNS, "{Server}|{Instance}|{Category}|{Specific_Entity_Name}")`
*   **Stability**: The key depends ONLY on the Entity Name. It persists across renames/edits if the name stays same.
*   **Clash Prevention**:
    *   Manual inputs in Excel are keyed by this UUID hidden in **Column A**.
    *   If Column A is tampered with, the Sync Engine falls back to hashing the "Natural Key" columns (Server, Instance, Entity Name) to try and recover the link.
