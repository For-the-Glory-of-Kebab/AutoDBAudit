# ADR 0003 — Remediation aggressiveness: Safe-by-default

Status: Proposed

Decision

Default remediation aggressiveness is level 1 (Safe). By default, generated fixes that touch exceptionalized or potentially risky items are commented out; operators must opt-in to more aggressive levels.

Rationale

- Safety-first reduces risk of unintentional service disruption and increases user trust in automated remediation.

Consequences

- CLI must support `--aggressiveness` and `--dry-run` to preview effects.  
- Tests should validate generated scripts across aggressiveness levels.

Notes

This ADR documents the policy used to prevent accidental changes and guides future tool UX.
