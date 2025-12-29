# Gap Analysis & Recommendations

**Generated At**: 2025-12-27
**Target**: Comprehensive Documentation & Standardization

## 1. Documentation Gaps Identified

While we have established a strong baseline, strict adherence to "Nothing left to imagination" reveals gaps in the underlying code vs docs:

*   **Excel Styles Hardcoding**: `excel_styles.py` defines many styles, but the *mapping* of which style applies to which specific *data scenario* is buried in logic within `base.py` and individual sheet classes.
    *   *Gap*: We need a matrix of "Data Condition -> Visual Style".
*   **CLI Return Codes**: The CLI documentation lists commands, but does not explicitly define the Exit Codes (0, 1, 130, etc.) for every failure mode. This is critical for automation/CI.
*   **Database Constraints**: The Schema doc lists tables, but does not detail unique constraints or index strategies for performance tuning (mentioned in "Performance Expectations").

## 2. Ambiguities in Current Spec

*   **"Graceful Recovery" Definition**: We state "preserve 90% progress", but the current `SyncService` is largely transactional per-step. If it fails during "Proccessing Sheet 5 of 10", do we rollback Sheets 1-4 or keep them?
    *   *Current Code*: Updates are committed in batches.
    *   *Ambiguity*: Is partial sync acceptable? (Likely yes for data, no for final report generation).

## 3. High-Priority Recommendations (Refactoring)

To meet the "Modern OOP" and "Performance" standards:

1.  **Refactor `base.py`**: This file is currently a "God Class" containing logic for formatting, reading, writing, and styling.
    *   *Action*: Split into `ExcelReader`, `ExcelWriter`, `StyleManager`, `DataFormatter`.
2.  **Parallel Audit Execution**: The current `AuditService` appears to loop sequentially through targets.
    *   *Action*: Implement `asyncio` or `ThreadPoolExecutor` for the Audit phase to hit 12+ instances simultaneously.
3.  **Strict Typing Pass**: Much of the legacy code uses `Any` or missing types.
    *   *Action*: Enforce `mypy --strict` compliance gradually.

## 4. Immediate Next Steps

1.  **Review `docs/excel/reference.md`**: Confirm the color/icon definitions match the business need.
2.  **Review `docs/architecture/standards.md`**: Approve the "One Class Per File" mandate before we start splitting files.
