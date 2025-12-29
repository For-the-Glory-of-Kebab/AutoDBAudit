# Remediation Requirements (Condensed)

This document captures the essential requirements for Remediation generation and execution. It is a condensed, actionable spec intended to be authoritative for the rewrite.

## Aggressiveness Levels
| Level | CLI Flag | Behavior |
|-------|----------|----------|
| 1 | `--aggressiveness 1` | Safe: exceptionalized fixes are commented out by default. |
| 2 | `--aggressiveness 2` | Moderate: exceptionalized fixes are included but clearly flagged with warnings/comments. |
| 3 | `--aggressiveness 3` | Aggressive: include fixes for non-exceptional checks. Use with caution. |

**Default**: level 1 (safe).

## Core Requirements
- R1: Exception-aware generation — findings with valid exceptions must be excluded from generated fixes.
- R2: Hybrid remediation approach — use T-SQL for DB-level fixes and PSRemote (PowerShell) for OS-level remediation on Windows. No PSRemote on Linux/Docker.
- R3: Service restart policy — when a config change requires a restart: gracefully stop (60s timeout), allow connections to drain, restart with retry (3 attempts), then verify service is running.
- R4: Data priority/fallback chain — when determining current state: Manual user input > PSRemote live data (if available) > Cached data > T-SQL fallback.
- R5: Docker/Linux exemptions — no OS-level remediation via PSRemote; note differences in implementation and UI messaging.
- R6: Template-driven generation — use Jinja2 templates under `src/autodbaudit/application/remediation/templates/` and produce metadata snapshots per run.

## Implementation notes
- Always write a metadata snapshot for each remediation run (remediation_runs, remediation_items) to ensure auditability and rollback.
- Provide `--dry-run` and `--apply` flows; `--dry-run` must show actionable commands without running them.
- Remediation scripts should include safe-guards (e.g., checks that the target is in an expected state before applying change).

## Tests (suggested)
- Generate scripts at each aggressiveness level and assert the presence/absence of commented vs active fixes.
- Integration test: simulate a service change requiring restart and verify the generated restart script follows R3 sequence.

## Where to find more
For a deeper discussion, see docs/remediation/engine_internals.md and the legacy backup branch for implementation notes and sample templates.