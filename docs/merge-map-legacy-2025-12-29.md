# Merge Map: Legacy -> Canonical targets

This document lists the legacy/archive files inspected and the concise extracted content merged into canonical documentation. Full originals are preserved on `backup/docs-legacy-2025-12-29` branch for future reference.

| Legacy file | Target file | Extract summary |
|-------------|-------------|-----------------|
| docs/legacy_v1/REAL_DB_E2E_PLAN.md | docs/testing/real-db.md | Baseline snapshot strategy, Hypothesis randomized state machine example, test categories L1-L8, quick-run checklist. |
| docs/legacy_v1/PERSIAN_REPORTS.md + legacy USER_GUIDE sections | docs/excel/persian.md | CLI usage, fonts, RTL config, limitations, suggested tests. Classified as Spec-only. |
| docs/legacy_v1/REMEDIATION_REQUIREMENTS.md + ACCESS_REMEDIATION_PLAN.md | docs/remediation/requirements.md | R1-R6 condensed, Aggressiveness table, restart policy, fallback chain, templates and metadata snapshot requirement. |
| docs/legacy_v1/REPORT_SCHEMA.md | docs/excel/spec_definitions.md | Row UUID paragraph (hidden Column A, 8-char hex) and any unique per-sheet column facts missing in current per-sheet docs. |
| docs/legacy_v1/TEST_ARCHITECTURE.md + archive/ATOMIC_E2E_* | docs/testing/testing-architecture.md (future) | Test pyramid, atomic E2E patterns, layer descriptions and commands. |

Notes:
- The approach is to extract concise, precise, and actionable content into the canonical docs, not to retain full legacy files in main. Legacy originals are preserved on the backup branch.
- I will proceed with these merges in the cleanup branch and prepare a draft PR for your review. Let me know if you want adjustments to the mapping or if anything else should be included.
