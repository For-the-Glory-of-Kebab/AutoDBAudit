# ADR 0005 — Persian/RTL support: Spec-only until implemented

Status: Proposed

Decision

Document Persian/RTL support as an explicit spec and verification checklist, but classify it as "Spec-only" until the implementation is validated in tests and CI.

Rationale

- The feature has UI and rendering implications (fonts, RTL, dropdown translations) that require careful validation and system-level font management.

Consequences

- Implementation should be gated by tests and a simple visual verification step; the docs should include a 'How to verify' section and sample fixtures.

Notes

This ADR keeps Persian support visible as a first-class target while avoiding premature implementation commitments.
