# Backlog & TODOs

## High Priority - Core PS Remoting Engine

- [x] **Phase 1: Core Infrastructure**
  - [x] Create PS remoting domain models (ConnectionProfile, AuthMethod, CredentialType)
  - [x] Implement shell elevation detection and user guidance system
  - [x] Build comprehensive credential handler with PSCredential conversion
  - [x] Create database schema for connection profiles and attempt logging

- [x] **Phase 2: Connection Engine**
  - [x] Implement Layer 1: Direct connection attempts (all auth methods)
  - [x] Implement Layer 2: Client-side configuration (TrustedHosts, WinRM client)
  - [x] Implement Layer 3: Target configuration (WinRM service, firewall, listeners)
  - [x] Add WinRM service control and firewall rule management

- [ ] **Phase 3: Advanced Features**
  - [ ] Implement Layer 4: Advanced configuration and fallbacks (actionable SSH/manual, persist successful permutations)
  - [ ] Implement Layer 5: Manual override and detailed logging (actionable scripts/report)
  - [ ] Add SSH-based PowerShell support (actionable, with revert guidance)
  - [ ] Build WMI/RPC and psexec fallback strategies (persist successful attempts into available_methods/persistence)
  - [ ] Make management surface coverage exhaustive (GPO/registry/firewall/WinRM client+service/listeners/services/TrustedHosts) with gpupdate/no-reboot application and reversible changes (partially done: WinRM policy + CredSSP + client auth baselines + TrustedHosts + gpupdate helper; still need structured baseline/revert capture for services)
  - [ ] Add PSRemotingFacade with structured API (get_status/ensure_prepared/run_command/run_script/revert) for downstream modules (partially done; integration deferred until consumers refactor)
  - [ ] Create connection health monitoring and rediscovery
  - [ ] Add parallel runner with prefixed, per-server logging and structured output (done)
  - [ ] Handle mixed-host scenarios on same IP (e.g., Windows + non-Windows SQL on Docker Desktop at different ports) via initial T-SQL or other detection to choose PS remoting vs. alt path
  - [ ] Refactor large files into smaller feature modules (direct_runner now ~215 lines with helpers; repository split into base/schema/profiles_reader/profiles_writer/attempts/state; consider further slicing connect_flow if desired) — target_config split; connection_manager reduced to shim + manager/orchestrator; fallbacks packaged and helpers added
  - [x] Upgrade runtime to Pydantic 2 and remove compatibility shim (ModelBase) once dependencies are aligned

- [ ] **Phase 4: Integration & Testing**
  - [ ] Update prepare command to use new PS remoting engine (defer until refactors done)
  - [ ] Implement shared connection logic for sync/remediate phases (defer until those engines are refactored)
  - [ ] Add comprehensive error handling and Railway-oriented programming
  - [ ] Test end-to-end prepare functionality with real targets (defer localhost tests until ready)
  - [ ] Validate credential passing across all phases

## Medium Priority

- [ ] Implement core audit engine (audit command)
- [ ] Build sync command with Excel integration
- [ ] Create remediate command with script generation
- [ ] Add finalize/definalize commands
- [ ] Implement util command with diagnostics
- [ ] Ensure PS remoting command construction passes explicit creds without interactive prompts across auth methods (re-test elevated)
- [ ] Capture successful auth/protocol permutations into persistence and expose via status API for downstream consumers
- [ ] Review latest attempt export at `AgentStuff/logs/psremoting_attempts_latest.txt` (from `audit_history.db`) and fix credential/command construction errors
- [ ] Redesign config schema/consumption for credentials/targets; provide clear API for prepare/remediate/sync (after commit of current PS remoting work)

## Low Priority

- [ ] Push progress folder to git (user action).
- [ ] Start rewrite: Plan first module (e.g., Excel interface).
- [ ] Test docs CI workflow.
- [ ] Add more cross-links in docs.
- [ ] Explore codebase for rewrite insights.
- [ ] Migrate from PyInstaller to Nuitka for better performance and native code compilation (deferred for now, as PyInstaller is functional).
- [ ] Archive backup branch if no longer needed.
- [ ] Update project status in docs.

## Completed

- [x] Set up AgentStuff tracking folder.
- [x] Clean up legacy docs.
- [x] Assess prepare functionality completeness (FOUND: Missing core PS remoting engine)
- [x] Design 5-layer resilient connection strategy
- [x] Start implementation of core PS remoting infrastructure

Last Updated: 2026-01-06

