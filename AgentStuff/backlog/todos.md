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
  - [ ] Implement Layer 4: Advanced configuration and fallbacks
  - [ ] Implement Layer 5: Manual override and detailed logging
  - [ ] Add SSH-based PowerShell support
  - [ ] Build WMI/RPC and psexec fallback strategies
  - [ ] Make management surface coverage exhaustive (GPO/registry/firewall/WinRM client+service/listeners/services/TrustedHosts) with gpupdate/no-reboot application and reversible changes (partially done: WinRM policy + CredSSP + client auth baselines)
  - [ ] Add PSRemotingFacade with structured API (get_status/ensure_prepared/run_command/run_script/revert) for downstream modules
  - [ ] Create connection health monitoring and rediscovery
  - [ ] Add parallel runner with prefixed, per-server logging and structured output
  - [ ] Handle mixed-host scenarios on same IP (e.g., Windows + non-Windows SQL on Docker Desktop at different ports) via initial T-SQL or other detection to choose PS remoting vs. alt path

- [ ] **Phase 4: Integration & Testing**
  - [ ] Update prepare command to use new PS remoting engine
  - [ ] Implement shared connection logic for sync/remediate phases
  - [ ] Add comprehensive error handling and Railway-oriented programming
  - [ ] Test end-to-end prepare functionality with real targets
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

Last Updated: 2026-01-05

