# ADR 0001 — Row Identity: Hidden 8-char UUID (Column A)

Status: Proposed

Decision

We will use a hidden 8-character hex UUID (stored in Excel Column A) as the canonical row identifier for all data sheets. This value is authoritative for Excel ↔ SQLite mapping and must be generated and preserved by all writers and readers.

Rationale

- Natural composite keys are fragile: server names, instance names, and other natural fields change and lead to collision/lost annotations.
- A short stable UUID allows rows to be relocated, renamed, or reordered in the Excel file without losing annotation or historical context.

Consequences

- All writing code must create and preserve the Column A UUID.  
- On sync, code may fallback to legacy natural-key matching for missing/invalid UUIDs, but such cases should be logged and surfaced as warnings.  
- Tests and migration scripts should include validation to detect missing or malformed UUIDs.

Notes

This ADR reflects the v3 row-uuid approach documented in the legacy materials. The ADR should be kept with the other design decisions in docs/adrs/ for future reference.
