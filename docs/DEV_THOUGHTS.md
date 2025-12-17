# Developer Thoughts & Vision 🧠

**Last Updated:** 2025-12-17
**Status:** Active Brainstorming & Requirements

This document captures high-level concerns, architectural goals, and feature requests from the lead developer. It serves as a guiding star for future development sessions.

## 1. Reliability & Resilience 🛡️
*   **Non-Destructive Sync:** The `--sync` process must be bulletproof. If it encounters a fatal error, it must forcefully revert all changes to that sync run. We treat Excel as a frontend; the backend (sync engine) must have app-grade error handling.
*   **State Handling:** Must gracefully handle any hiccups or state changes in the Excel file or database without corruption.

## 2. UI/UX Improvements 🎨
*   **Instance Merging:** The "Instances" sheet looks cluttered. It repeats instance names. We need a clean visual merge (e.g., merging "Server" and "Instance" cells vertically) to clearly show services/configs for each instance.
*   **Visual Stats:** The CLI and Cover sheet need better visual indicators (icons) for:
    *   Fixed 🟢
    *   Regression 🔴
    *   New Issue ⚠️
    *   Still Failing ❌
*   **Stats Detail:** Explicitly show counts for "Documented" (Note/Date) vs "Exception" (Status/Justification).
*   **Fonts:** The default Calibri is ugly. Brainstorm a custom font setting for generated sheets (headers vs rows).

## 3. Client Protocols 🔌
*   **Current Issue:** Only identifies TCP/IP correctly.
*   **Goal:** Need reliable logging of all protocols. If automatic detection (via PSRemote?) isn't possible yet, allow manual entry that persists.

## 4. Robust Remediation 🛠️
*   **Coverage:** Remediations must cover **everything**, including non-TSQL items like Services and Client Protocols.
*   **PowerScripting:** Generate robust PowerShell scripts for items that TSQL can't handle (e.g., service restarts, config applications).
*   **Human-Friendly Scripts:** Instead of multiple `DELETE` statements, group them! Use commented-out blocks where the user just uncomments the specific users/items to remove.
    *   *Action:* Review all requirements -> Check corresponding remediation -> Implement grouped syntax if possible.

## 5. Advanced logic 🧠
*   **Merge Logic:** Implement robust logic to merge passing cells vertically for cleaner visuals, BUT it must be smart enough to:
    *   Unmerge if data changes.
    *   Read merged cells correctly (don't read row 2 as empty if merged with row 1).
    *   Handle sorting/ordering changes without breaking data.
*   **Lazy Flag:** Add a `--lazy` flag to `--sync` that automatically marks all remaining discrepancies as "Exceptional". Useful for bulk-deferring issues to be documented later.

## 6. Logic Gaps 🕳️
*   **Version Mismatch:** The version mismatch in Instances table isn't counting as discrepant. It needs exception/fix logic applied.

## 7. The Finalize Vision 🏁
*   **Goal:** What does `--finalize` actually do?
*   **Proposal:** Squash diff history into one "Initial Audit" and one "Final State".
*   **Reproducibility:** Must be reproducible from the "Archive" of audit runs.
*   **Baseline:** The final state should serve as the baseline for **next year's** audit.

---
*Reference: Originally captured in `docs/the Human Dev Thoughts.txt`*
