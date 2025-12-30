# Discrepancy Simulation Toolkit

## Overview

The `simulate-discrepancies/` folder contains a development-time toolkit for simulating various types of discrepancies on local SQL Server test instances. This is crucial for testing the AutoDBAudit application's functionality in documentation, remediation, and synchronization logic—both automated (via scripts) and manual (via direct inspection).

This toolkit is a dependency for comprehensive testing but is not part of the production build. It ensures the app can handle real-world discrepancies accurately.

## Purpose

- **Simulate Real Scenarios**: Create controlled discrepancies (e.g., missing logins, orphaned databases, config mismatches) to validate detection, reporting, and fixing.
- **Test Automation**: Enable end-to-end tests that assert correct behavior.
- **Manual Verification**: Allow developers to inspect and verify app responses manually.

## Requirements

- **Comprehensive Coverage**: Must create at least one instance of each type of discrepancy supported by AutoDBAudit (e.g., database orphans, login mismatches, permission issues).
- **Randomization with Tracking**: Randomize names (e.g., DB names, login names) and numbers (e.g., IDs, counts) to simulate variability, but track them explicitly for accurate assertions in tests and manual checks.
- **Revert Functionality**: Provide full revert capability that identifies and removes all created discrepancies, restoring the test instance to a clean slate. This includes cleaning test databases, logins, configurations, etc.
- **Assertion Support**: Both automated (scripted assertions) and manual (logged outputs for inspection).

## Files

- `2008.sql`, `2019+.sql`: Scripts to create discrepancies for specific SQL Server versions.
- `2008_revert.sql`, `2019+_revert.sql`: Revert scripts to clean up.
- `annotation_writer.py`, `discrepancy_tracker.py`: Python helpers for tracking and writing annotations.
- `run_simulation.py`, `run_full_e2e.py`, `verify_e2e.py`: Execution scripts for simulation and verification.
- `legacy/`: Archived older versions.

## Usage

1. Run simulation: `python simulate-discrepancies/run_simulation.py` (select version).
2. Test app functionality on the modified instance.
3. Assert results: Use `verify_e2e.py` for automated checks or inspect logs manually.
4. Revert: `python simulate-discrepancies/run_simulation.py --revert` to clean slate.

## Maintenance

- Fix redundancies and broken parts (e.g., ensure tracking is accurate).
- Update for new discrepancy types as the app evolves.
- Keep in sync with `AgentStuff/backlog/todos.md` for any deferred improvements.
