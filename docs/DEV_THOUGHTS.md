# Developer Thoughts & Vision 🧠

**Last Updated:** 2025-12-20
**Status:** Active Brainstorming & Requirements

This document captures high-level concerns, architectural goals, and feature requests from the lead developer. It serves as a guiding star for future development sessions.

---

## 1. Reliability & Resilience 🛡️

*   **Non-Destructive Sync:** The `--sync` process must be bulletproof. If it encounters a fatal error, it must forcefully revert all changes to that sync run. We treat Excel as a frontend; the backend (sync engine) must have app-grade error handling.
*   **State Handling:** Must gracefully handle any hiccups or state changes in the Excel file or database without corruption.
*   **Recovery System:** Need a way to revert the last `--sync` run or help recover from mistakes. The Action Log getting corrupted should NEVER cause a 20+ sync audit to be rendered unusable. This recovery feature should ideally never be needed!
*   **Input Resilience:** App must be super resilient to wrong inputs, broken Excel sheets, and user mistakes. The whole point is streamlining compliance - we can't have fragile error handling.

---

## 2. UI/UX Improvements 🎨

*   **Instance Merging:** The "Instances" sheet looks cluttered. It repeats instance names. We need a clean visual merge (e.g., merging "Server" and "Instance" cells vertically) to clearly show services/configs for each instance.
*   **Visual Stats:** The CLI and Cover sheet need better visual indicators (icons) for:
    *   Fixed 🟢
    *   Regression 🔴
    *   New Issue ⚠️
    *   Still Failing ❌
*   **Stats Detail:** Explicitly show counts for "Documented" (Note/Date) vs "Exception" (Status/Justification).
*   **Fonts:** The default Calibri is ugly. Brainstorm a custom font setting for generated sheets (headers vs rows).

---

## 3. Excel Formatting 📊

*   **Column Widths:** Justification, Purpose, Notes, and Date columns need appropriate width from the start. Currently too narrow - forces manual resizing.
*   **Text Wrapping:** Enable text wrapping by default on note/justification columns. Adding data then manually applying wrapping is tedious.
*   **Preset Widths Table:**
    | Column Type | Suggested Width |
    |-------------|-----------------|
    | Justification | 40-50 |
    | Purpose | 35-40 |
    | Notes | 30-35 |
    | Last Reviewed | 18-20 |

---

## 4. CLI Interface Refactor 💻

*   **Help System:** Need `-h` / `--help` for EACH subcommand with clear instructions.
*   **Better Defaults:** If audit name not supplied, default to `{OrgName}_{Date}` format.
*   **Stats & Logs:** All CLI output (stats, logs, progress) must be more robust, intuitive, and professional.
*   **Audit ID Handling:** If multiple audits exist and no ID is specified:
    *   Prompt user to select which audit
    *   OR default to most recent with clear indication
*   **Output Example:**
    ```
    AutoDBAudit v1.0.0
    
    Available audits:
      1. ACME_2024-12-15 (5 instances, last sync: 2024-12-18)
      2. ACME_2024-11-01 (3 instances, finalized)
    
    Select audit [1]: _
    ```

---

## 5. Dependency Management 📦

*   **Separate Runtime vs Dev Dependencies:**
    *   **Runtime:** openpyxl, pyodbc, pillow, etc.
    *   **Dev-only:** pytest, black, mypy, ruff, etc.
*   **PyInstaller Optimization:**
    *   Output `.exe` must be self-contained
    *   No dev dependencies included
    *   No external scripts required
    *   Minimize file size where possible

---

## 6. Cleanup Tasks 🧹

*   **Remove Empty Runs Folder:** The `Runs/` folder is created at output location but never used (we don't save per-run Excel anymore). Delete the folder and all logic that creates it.

---

## 7. Client Protocols 🔌

*   **Current Issue:** Only identifies TCP/IP correctly.
*   **Goal:** Need reliable logging of all protocols. If automatic detection (via PSRemote?) isn't possible yet, allow manual entry that persists.

---

## 8. Robust Remediation 🛠️

*   **Coverage:** Remediations must cover **everything**, including non-TSQL items like Services and Client Protocols.
*   **PowerScripting:** Generate robust PowerShell scripts for items that TSQL can't handle (e.g., service restarts, config applications).
*   **Human-Friendly Scripts:** Instead of multiple `DELETE` statements, group them! Use commented-out blocks where the user just uncomments the specific users/items to remove.
    *   *Action:* Review all requirements → Check corresponding remediation → Implement grouped syntax if possible.

---

## 9. Advanced Logic 🧠

*   **Merge Logic:** Implement robust logic to merge passing cells vertically for cleaner visuals, BUT it must be smart enough to:
    *   Unmerge if data changes.
    *   Read merged cells correctly (don't read row 2 as empty if merged with row 1).
    *   Handle sorting/ordering changes without breaking data.
*   **Lazy Flag:** Add a `--lazy` flag to `--sync` that automatically marks all remaining discrepancies as "Exceptional". Useful for bulk-deferring issues to be documented later.

---

## 10. Logic Gaps 🕳️

*   **Version Mismatch:** The version mismatch in Instances table isn't counting as discrepant. It needs exception/fix logic applied.

---

## 11. The Finalize Vision 🏁

*   **Goal:** What does `--finalize` actually do?
*   **Proposal:** Squash diff history into one "Initial Audit" and one "Final State".
*   **Reproducibility:** Must be reproducible from the "Archive" of audit runs.
*   **Baseline:** The final state should serve as the baseline for **next year's** audit.

---

## Priority Matrix

| Priority | Item | Effort |
|----------|------|--------|
| 🔴 HIGH | Recovery/revert system | Medium |
| 🔴 HIGH | Input resilience | Medium |
| 🟡 MEDIUM | CLI refactor with help | Medium |
| 🟡 MEDIUM | Excel column widths + wrapping | Low |
| 🟡 MEDIUM | Dependency separation | Low |
| 🟢 LOW | Remove Runs folder | Trivial |
| 🟢 LOW | Font customization | Low |

---

*Reference: Originally captured in `docs/the Human Dev Thoughts.txt`*

