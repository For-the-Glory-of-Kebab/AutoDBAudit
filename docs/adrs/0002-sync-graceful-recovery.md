# ADR 0002 — Sync semantics: Partial-commit & Explicit Finalize

Status: Proposed

Decision

Adopt a partial-commit model for sync runs: when a run fails partway, completed sheet-level commits are preserved and the run is marked as FAILED. Introduce an explicit `finalize` step that confirms a run has completed all intended sheets and is considered final.

Rationale

- Long multi-sheet syncs are common and network failures/environment issues make all-or-nothing transactions brittle and costly.
- Preserving progress reduces repeated work, makes recovery simpler, and better matches operational realities.

Consequences

- The SyncService must log per-sheet commit status and expose a recovery workflow (resume, rollback per sheet if needed).  
- Tests must include partial-run scenarios and validate recovery behaviors.

Notes

This ADR replaces the ambiguous "preserve 90%" wording with an explicit behavioral model and recovery options.
