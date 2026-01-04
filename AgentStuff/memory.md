# 🤖 AI Agent Memory & State Snapshot

**Last Updated**: 2026-01-04 (later in session)  
**Agent Session**: PS Remoting Engine Implementation / Prepare API / Policy Exhaustion  
**Project**: AutoDBAudit SQL Server Security Auditing Tool

---

> Start at `AGENT_HUB.md` → `AGENT_SOP.md` before using this snapshot.

## 🎯 Current Mission
Production-ready, offline-first PS remoting for the prepare command, with a clean status/persistence API consumed by audit/remediate/sync. Maintain ultra-granular modules (<100 lines when feasible) without duplicating implementations.

## ✅ Recent Changes (2026-01-04)
- Persistence: `psremoting` repository now matches models (protocol/port/credential_type/server_name persisted); auto-ALTER for existing DBs; resilient parsing when connection_method is missing.
- Auth: `AuthMethod.CREDSSP` casing fixed; direct runner permutations updated.
- Status API: PrepareStatusService now returns richer snapshots (deduped available_methods, priority preferred_method, protocol/port/auth/credential_type surfaced) without relying on private timestamps.
- Tooling: Line endings normalized; unused args cleaned. `pyright` clean and `pylint` 10/10 for prepare + psremoting. `.pylintrc` disables only C0103/R0903/W0718/R0801 (duplicate-code noise).
- Fallbacks: WMI/psexec/RPC attempts logged with credential permutations; SSH still stubbed but records attempt metadata.

## ❌ Open Gaps / Risks
- TrustedHosts + Revert Fidelity: Add explicit client/target TrustedHosts handling (IP/hostname), capture baselines, and emit revert scripts; capture/restore registry/GPO/firewall/listener state and surface revert scripts in PSRemotingResult.
- Attempt Logging Completeness: Persist which auth/protocol permutations succeeded and expose them in available_methods/persistence.
- Fallback Coverage: Implement SSH path and make manual layer emit actionable scripts/report; log fallback successes into available methods.
- API Consumption: Wire PrepareStatusService into audit/remediate/sync entrypoints; align preferred_method choice with the method selector.
- Structure: Continue feature-based grouping for non-prepare modules; avoid duplicate implementations while keeping files small/clear.
- Docs: DOCUMENTATION_HUB/status/prepare are out-of-sync with current engine/persistence; several hub links missing files. Update to reflect the new SOP and schema.

## 📂 Key Files (prepare/remoting focus)
- `src/autodbaudit/infrastructure/psremoting/connection_manager.py`
- `src/autodbaudit/infrastructure/psremoting/direct_runner.py`
- `src/autodbaudit/infrastructure/psremoting/layer2_client.py`
- `src/autodbaudit/infrastructure/psremoting/layer3_target.py`
- `src/autodbaudit/infrastructure/psremoting/fallbacks.py`
- `src/autodbaudit/infrastructure/psremoting/gpo_enforcer.py`
- `src/autodbaudit/infrastructure/psremoting/credentials.py`
- `src/autodbaudit/application/prepare/status_service.py`
- `docs/DOCUMENTATION_HUB.md`, `docs/sync/prepare.md`

## ▶️ Next Actions
1) Implement TrustedHosts + revert fidelity (client + target) and capture/restore registry/GPO/firewall/listeners; include revert scripts in PSRemotingResult.
2) Record successful auth/protocol permutations into available_methods/persistence; make manual/SSH fallbacks actionable and captured.
3) Expose PrepareStatusService to audit/remediate/sync consumers; align preferred_method with the method selector and continue feature-based grouping outside prepare.
4) Refresh docs (hub/status/prepare) to match the current remoting engine, persistence schema, and SOP/lint posture.
