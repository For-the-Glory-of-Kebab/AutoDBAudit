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
  - [ ] Create connection health monitoring and rediscovery

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

Last Updated: 2025-12-31

