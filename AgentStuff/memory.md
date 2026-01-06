# 🤖 AI Agent Memory & State Snapshot

**Last Updated**: 2026-01-06  
**Agent Session**: PS Remoting Engine Implementation / Prepare API / Policy Exhaustion / Credential Hardening  
**Project**: AutoDBAudit SQL Server Security Auditing Tool

---

> Start at `AGENT_HUB.md` → `AGENT_SOP.md` before using this snapshot.

## 🎯 Current Mission
Production-ready, offline-first PS remoting for the prepare command, with a clean status/persistence API consumed by audit/remediate/sync. Maintain ultra-granular modules (<100 lines when feasible) without duplicating implementations.

## ✅ Recent Changes (2026-01-04 → 2026-01-06)
- Upgraded runtime to Pydantic 2.12.5; removed the temporary shim and migrated psremoting models to native v2 BaseModel with `model_copy/model_dump` and ConfigDict.
- Connection manager collapsed to a thin shim; orchestration moved to `manager/orchestrator.py` with revert logic extracted to `manager/revert_service.py` and existing profile/fallback helpers.
- Direct runner split with helpers in `layers/direct/` (plan + command builder) to keep Layer 1 logic granular; repository moved under `repository/` package (`core.py`).
- Repository decomposed into `repository/base.py` + schema/columns (`schema.py`) and mixins for profiles (`profiles_reader.py`, `profiles_writer.py`), attempts (`attempts.py`), and server state (`state.py`); `core.py` is now just the facade.
- Split connection manager concerns: stored-profile handling and fallback execution moved into `psremoting/manager/profiles.py` and `psremoting/manager/fallback_runner.py`; connection_manager now delegates instead of inlining logic.
- Target config split into focused helpers under `config/target/` (service/firewall/registry/listeners/trustedhosts + gpupdate) with a light `TargetConfigurator`; gpupdate helper restored so layer3 can force policy application without reboot.
- Fallbacks moved into `layers/fallbacks/` package (SSH/WMI/RPC/PsExec + shared utils) with corrected imports; pyright/pylint clean after refactor.
- WinRM policy coverage expanded: service+client auth/AllowUnencrypted and CredSSP now captured/applied with gpupdate; revert scripts include disabling CredSSP. Client config enables all auth types, CredSSP delegation, captures baselines, and builds full reverts.
- Persistence: `psremoting` repository now matches models (protocol/port/credential_type/server_name persisted); auto-ALTER for existing DBs; resilient parsing when connection_method is missing.
- Auth: `AuthMethod.CREDSSP` casing fixed; direct runner permutations updated.
- Status API: PrepareStatusService now returns richer snapshots (deduped available_methods, priority preferred_method, protocol/port/auth/credential_type surfaced) without relying on private timestamps.
- Facade: Added `PSRemotingFacade` (structured API: get_status/ensure_prepared/run_command/run_script/revert) and `CommandResult`; uses persisted profiles/permutations and returns structured method info.
- Tooling: Line endings normalized; unused args cleaned. `pyright` clean and `pylint` 10/10 for prepare + psremoting. `.pylintrc` disables only C0103/R0903/W0718/R0801 (duplicate-code noise).
- Fallbacks: WMI/psexec/RPC attempts logged with credential permutations; SSH still stubbed but records attempt metadata.
- TrustedHosts/Revert: Client layer now captures previous TrustedHosts/AllowUnencrypted and records revert scripts; target TrustedHosts capture previous list and emit revert.
- Target baseline/revert capture: WinRM service/firewall/registry/listeners capture prior state and emit targeted revert scripts; RevertTracker collects them. Pyright/pylint still clean.
- Docs updated: DOCUMENTATION_HUB AI section now points to `AgentStuff/AGENT_HUB.md`; prepare doc notes state-capture/revert for target config.
- Permutation logging: Successful auth/protocol/port permutations are attached to PSRemotingResult and propagated into prepare/status connection_details.
- Facade package: `psremoting/facade/` now holds `base.py` orchestrator and `executor.py` for command/script execution; small files for readability.
- Removed legacy `psremoting/executor` components to avoid duplication.
- Restructured psremoting into feature folders (`config/`, `layers/`) for readability; imports updated.
- Split monolithic `models.py` into `models/` package (auth, protocol, credential, connection_method/state, profile, attempt, server_state, session, elevation, result); __init__ re-exports for compatibility.
- Added `ParallelRunner` (psremoting/facade/runner.py) to run per-server tasks in parallel with prefixed, ordered logging via a queue/consumer.
- Direct attempts now **require explicit credentials** (no credential-less permutation); prevents interactive prompts. If no creds are present, fail fast with a clear message.
- Direct attempt timeout tightened (12s) and connection command rebuilt into a single-line PS command with module import to avoid parsing issues.
- Direct auth priority set (Kerberos > Negotiate > NTLM > CredSSP > Basic > Default); reverse DNS retry for IP targets before moving to config layers.
- Fallback successes now persist a derived connection profile (auth/protocol/port/credential_type/connection_method) even without a PSSession, ensuring reuse and logging.
- ParallelRunner adds colored/emoji-prefixed console logs and optional per-server log files; pylint/pyright clean for psremoting.
- Added temporary compatibility shims in `psremoting/executor/` (ScriptExecutor, PsRemoteOsDataInvoker) returning failures to keep legacy imports compiling until refactored to the facade.
- Latest attempt logs exported to `AgentStuff/logs/psremoting_attempts_latest.txt` (204 rows from `audit_history.db`) for git-tracked review.
- Older session logs archived in `sessions/archive/`; summaries retained in this file and `sessions/README.md`.
- Fallback tools: SSH/PsExec fallbacks now return actionable guidance when tools are missing (install instructions).

## 🧭 History Snapshot (older sessions)
- 2026-01-06: Target config split + gpupdate helper restored; fallbacks moved to package; lint/type clean; Pydantic upgraded to v2 (shim removed).
- 2026-01-05: Policy coverage, facade/runner, persistence/auth fixes, lint/type clean.
- 2026-01-04: Repo/schema alignment, CREDSSP fix, richer status API, TrustedHosts + target baseline/revert capture, lint/type clean.
- 2025-12-31: PS remoting architecture decisions (5-layer strategy, railway error handling, persistence plan), initial layer implementations.
- 2025-12-29: AgentStuff folder setup and initial tracking structure.

## ❌ Open Gaps / Risks
- Attempt logging completeness: Persist which auth/protocol permutations succeeded and expose them in available_methods/persistence (partially captured; needs consumption/persistence wiring).
- Credential execution still failing on localhost: prior attempts show ConvertTo-SecureString module load errors and command-line parsing errors; needs re-test elevated with fixed single-line command and explicit creds. Ensure credentials from `credentials/local_remote.json` are injected (no interactive prompts allowed).
- Elevation: When not elevated, config layers are skipped (warning emitted). Need an elevated run to validate client/target layers and fallbacks.
- Fallback coverage: Implement SSH path and make manual layer emit actionable scripts/report; log fallback successes into available methods.
- API consumption (defer): Wiring PrepareStatusService/PSRemotingFacade into audit/remediate/sync is deferred until those engines are refactored; note this dependency.
- Config command: current state unclear; plan full reimplementation alongside audit/remediate/sync refactors.
- Structure: Continue feature-based grouping for non-prepare modules; avoid duplicate implementations while keeping files small/clear.
- Docs: DOCUMENTATION_HUB/prepare/status partially refreshed; continue cross-link/feature-group updates and ensure offline-first/no-interactive-prompts remain explicit.
- Large files to split: connection_manager (~600 lines), repository (~670), direct_runner (~380); plan to cascade into smaller feature modules with clear interfaces.
- Pydantic upgrade: Runtime now on Pydantic 2; validate other modules for v2 compatibility when touched. Shim removed.
- Exhaustive management surfaces: Prepare must touch all Windows management interfaces (GPO, registry, firewall, WinRM client/service/listeners, services, TrustedHosts, gpupdate) to guarantee PS remoting, with non-destructive revert and immediate policy application (no reboot). Domain-admin credential is assumed; remoting sessions must end with admin privileges.
- Persistence/API shape: Expose a robust, structured API (not ad-hoc strings) for available methods, permutations, reverts, and troubleshooting so downstream layers can consume without tight coupling.
- Retry semantics: Prepare should re-run non-success servers, detect manual fixes, re-evaluate methods, and persist refreshed availability; fallbacks must be self-contained (enable + revert).

## 📂 Key Files (prepare/remoting focus)
- `src/autodbaudit/infrastructure/psremoting/connection_manager.py`
- `src/autodbaudit/infrastructure/psremoting/direct_runner.py`
- `src/autodbaudit/infrastructure/psremoting/layer2_client.py`
- `src/autodbaudit/infrastructure/psremoting/layer3_target.py`
- `src/autodbaudit/infrastructure/psremoting/layers/fallbacks/`
- `src/autodbaudit/infrastructure/psremoting/gpo_enforcer.py`
- `src/autodbaudit/infrastructure/psremoting/credentials.py`
- `src/autodbaudit/application/prepare/status_service.py`
- `docs/DOCUMENTATION_HUB.md`, `docs/sync/prepare.md`

## ▶️ Next Actions
1) Make fallbacks/manual actionable (SSH/WMI/RPC/psexec scripts), log successes into available_methods/persistence, and support reruns of previously failed servers to detect manual fixes.
2) Refactor large files into smaller modules (connection_manager, repository, direct_runner) while preserving behavior.
3) Expose PSRemotingFacade to audit/remediate/sync/hotfix consumers (method selector + admin enforcement) after those engines are refactored; defer integrations/config command until then.
4) Refresh docs (hub/status/prepare) with the facade contract and feature grouping; keep offline/admin/no-interactive-prompts explicit.
