# Project Status

**Last Updated**: 2026-01-06
**Current Phase**: Prepare/PS Remoting Hardening

## Overview
AutoDBAudit is strengthening the prepare/PS remoting pipeline to guarantee offline-first, admin-level connectivity with full revert capability. Core audit/sync/remediation remain intact; current focus is exhaustive remoting, persistence, and structured APIs for downstream consumers.

## Recent Milestones
- [x] PS remoting persistence aligned to models (protocol/port/credential_type/server_name; auto-migrations).
- [x] CREDSSP/auth permutations fixed; status API returns richer snapshots.
- [x] Facade + parallel runner added for structured status/command execution; legacy executor shimmed.
- [x] TrustedHosts + baseline capture/revert for WinRM service/firewall/registry/listeners.
- [x] Pyright/pylint clean for prepare + psremoting.
- [x] PS remoting codebase fully modularized: connection manager is a shim over `manager/orchestrator.py` + `manager/connect_flow.py`; direct layer helpers live under `layers/direct/`; repository split into `repository/base.py`, `schema.py`, `profiles_reader.py`, `profiles_writer.py`, `attempts.py`, `state.py`.

## Known Issues (Loose Ends)
- Fallback coverage: SSH/manual not yet actionable; need to log/persist successful fallbacks.
- Prepare consumption: facade/status not yet wired into audit/remediate/sync.
- Credential execution on localhost requires re-validation with explicit creds/elevation.
- Docs still catching up to new facade/grouping.

## Roadmap / Next Steps
1. Make fallbacks/manual actionable; persist successful auth/protocol permutations into available_methods.
2. Wire PrepareStatusService/PSRemotingFacade into audit/remediate/sync (method selector + admin enforcement).
3. Validate elevated runs (client/target layers, fallbacks) and refresh docs accordingly.
4. Continue feature-based grouping and doc cross-links (DOCUMENTATION_HUB/prepare/status).

## Architecture Notes
- PS remoting uses layered approach (direct → client config → target config → fallbacks → manual) with RevertTracker.
- Facade provides structured status/command APIs; persistence stores successful profiles/attempts for reuse.
- Strict offline-first; explicit credentials required (no interactive prompts).
- Code layout (prepare/remoting): `manager/orchestrator.py`, `manager/connect_flow.py`, `manager/revert_service.py`; direct helpers under `layers/direct/`; repository package split into base/schema/profiles_reader/profiles_writer/attempts/state.
