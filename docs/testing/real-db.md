# Real-DB E2E (Condensed)

Status: Extracted from legacy Real-DB E2E Plan (consolidated for clarity and quick consumption).

TL;DR: Use a baseline snapshot strategy to avoid pre-existing noise and run randomized stateful Hypothesis tests to explore sync edge-cases. Keep tests concise and reproducible; prefer small atomic fixtures and snapshot-based assertions rather than brittle global state assertions.

## Baseline Snapshot Strategy

- PHASE 0: Capture a baseline by running the `audit` command on clean instances and save `baseline_snapshot.json` (mapping: sheet -> [entity keys]).
- PHASE 1: Apply small, deterministic atomic fixture(s) (examples: `sa_enable.sql`, `login_weak_create.sql`) and record what we added (e.g., `test_additions.json`).
- PHASE 2: Run `audit` again, compute a delta vs baseline, and assert NEW findings == test additions.

Why: This isolates test-induced changes from pre-existing discrepancies (e.g., 'King' login) and yields deterministic outcomes even on messy instances.

Implementation notes:

- Keep baseline captures small and versioned (baseline_snapshot-YYYY-MM-DD.json).
- Use helpers (BaselineManager) to capture and diff results; see the backup branch for a sample `BaselineManager` implementation.

## Hypothesis Randomized Sync Testing

- Pattern: Use Hypothesis `RuleBasedStateMachine` to apply sequences of operations: apply_discrepancy, fix_discrepancy, add_exception, run_sync.
- Invariant: After any run that includes a `run_sync`, assert that observed stats (active issues, exceptions) match the expected state from the state machine.
- Implementation hint: Keep the test harness light by using an in-repo RealDBTestContext and small atomic SQL fixtures.

## Test Categories (L1-L8, short)

- L1: Foundation tests (audit → Excel exists, sheets present, headers match schema).
- L2: Annotation persistence (notes, justifications, review status).
- L3: State transitions (FAIL → PASS, regression tests).
- L4: Action log (log entry semantics).
- L5: Cross-sheet consistency tests.
- L6: CLI-level command tests.
- L7: Error handling tests (locked file, bad config).
- L8: Stateful randomized Hypothesis tests (RuleBasedStateMachine).

## Quick-run checklist

- [ ] Capture baseline snapshot from a clean instance.
- [ ] Ensure King (sysadmin) is protected and not modified by atomic fixtures.
- [ ] Prepare atomic fixtures and a small baseline manager helper.
- [ ] Run the randomized suite under timeboxed settings to find flaky sequences.

## Where to find more examples

Full example and extended implementation details live in the legacy backup branch; this doc captures the essential strategy and minimal reproducible pattern required for the rewrite.
