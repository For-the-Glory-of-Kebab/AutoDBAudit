# ADR 0004 — Agent governance: Dry-run proposals + Human Approval

Status: Proposed

Decision

Agent-driven changes must be proposed in dry-run mode and submitted as PRs for human review before being merged. Agents are not permitted to directly modify canonical docs or critical files without approval.

Rationale

- Prevents silent regressions and ensures that complex, high-impact changes are reviewed by humans.

Consequences

- CI should enforce that any PR touching critical files (docs, sync, remediation code) includes human approval and tests where applicable.  
- Agents should support a `--dry-run` mode that outputs a proposed patch without committing changes.

Notes

This ADR establishes safe guardrails for future agent-based automation.