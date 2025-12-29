# Test Architecture (Condensed)

This document captures the recommended test layering and E2E strategy for the rewrite.

- Test Pyramid: Unit → Integration → Per-sheet E2E (fast) → Ultimate E2E / Real-DB E2E (slow).
- Use atomic fixtures and a baseline snapshot strategy for Real-DB tests to avoid brittle assertions.
- Keep per-sheet E2E tests fast (<120s) and deterministic; reserve the slow, randomized Hypothesis stateful suite (L8) for targeted nightly runs.

Quick commands
- Per-sheet e2e: `pytest tests/ultimate_e2e/ -m e2e`  
- Real-DB set: see `docs/testing/real-db.md` for baseline strategy.

Notes
- The legacy atomic_e2e and real_db plans have been condensed into this doc and `docs/testing/real-db.md` (the backup branch contains full examples).