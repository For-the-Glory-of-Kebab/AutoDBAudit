# Key Decisions Log

## Decision: Core PS Remoting Engine Architecture

- **Date**: 2025-12-31
- **Context**: Prepare functionality assessment revealed missing core PS remoting engine. Current implementation has CLI scaffolding but lacks actual connection establishment capabilities.
- **Decision**: Implement robust, resilient 5-layer PS remoting infrastructure with ultra-granular, modular components following Railway-oriented programming principles.
- **Rationale**: The documented prepare command is "currently broken" due to missing connection logic. Need comprehensive solution that handles all authentication methods, configuration management, and state persistence.
- **Consequences**: Major implementation effort required, but essential for functional prepare command and subsequent sync/remediate phases.

## Decision: 5-Layer Connection Strategy

- **Date**: 2025-12-31
- **Context**: Need extremely resilient connection establishment that tries every possible method before failing.
- **Decision**: Implement 5-layer approach: (1) Direct attempts, (2) Client-side config, (3) Target config, (4) Advanced fallbacks, (5) Manual override.
- **Rationale**: Exhaustive approach ensures maximum compatibility across diverse Windows environments and configurations.
- **Consequences**: Complex implementation but guarantees highest success rate for PS remoting setup.

## Decision: Ultra-Granular Component Architecture

- **Date**: 2025-12-31
- **Context**: Previous CLI implementation used <50 line micro-components successfully.
- **Decision**: Apply same ultra-granular principle to PS remoting engine with single-responsibility components.
- **Rationale**: Maintains code quality, testability, and maintainability while following established patterns.
- **Consequences**: More files but each extremely focused and easy to understand/modify.

## Decision: Railway-Oriented Error Handling

- **Date**: 2025-12-31
- **Context**: Complex connection logic requires robust error handling and recovery.
- **Decision**: Use Railway-oriented programming with Success/Failure variants throughout the PS remoting pipeline.
- **Rationale**: Provides clear error propagation, recovery strategies, and prevents silent failures.
- **Consequences**: More verbose code but extremely reliable and debuggable.

## Decision: State Persistence Strategy

- **Date**: 2025-12-31
- **Context**: Need to remember successful connection parameters and avoid repeated discovery.
- **Decision**: Database-backed persistence with connection profiles and attempt logging, no TTL-based caching.
- **Rationale**: Ensures reliability across sessions and provides learning capability for future connections.
- **Consequences**: Requires database schema changes but provides long-term value.

## Decision: Shell Elevation Integration

- **Date**: 2025-12-31
- **Context**: Many PS remoting operations require elevated privileges.
- **Decision**: Integrate elevation detection with user guidance and automatic elevation requests.
- **Rationale**: Prevents cryptic permission errors and guides users through privilege escalation.
- **Consequences**: Better UX but requires careful privilege handling.

## Decision: Comprehensive Credential Handling

- **Date**: 2025-12-31
- **Context**: Multiple authentication methods require different credential formats and passing mechanisms.
- **Decision**: Unified credential pipeline supporting all auth types (Kerberos, NTLM, Negotiate, Basic, CredSSP) with proper PSCredential conversion.
- **Rationale**: Eliminates credential handling inconsistencies between prepare/sync/remediate phases.
- **Consequences**: Complex implementation but ensures consistent authentication across all operations.

## Decision: Fallback Strategy Hierarchy

- **Date**: 2025-12-31
- **Context**: Standard WinRM may fail in various environments.
- **Decision**: Implement SSH-based PowerShell, WMI/RPC, and psexec fallbacks in order of preference.
- **Rationale**: Maximizes compatibility with diverse server configurations and security policies.
- **Consequences**: Broad compatibility but requires multiple implementation approaches.

## Decision: Exhaustive Windows Management Coverage & Admin-Level Remoting

- **Date**: 2026-01-04
- **Context**: Prepare must succeed in offline Windows/AD environments with domain-admin credentials.
- **Decision**: Prepare will exhaust all relevant Windows management surfaces (GPO, registry, firewall, WinRM client/service/listeners, services, TrustedHosts, gpupdate) to enable PS remoting, and will ensure remoting sessions end with admin privileges. All changes must be captured with baselines and reversible without reboot where possible.
- **Rationale**: Domain-admin context allows aggressive but reversible configuration to make PS remoting virtually guaranteed; downstream modules need reliable admin sessions.
- **Consequences**: Requires comprehensive state capture, gpupdate triggers, and revert automation; increases implementation surface but improves reliability.

## Decision: Ultra-Granular File/Folder Structure & Tooling Standards

- **Date**: 2026-01-04
- **Context**: Past regressions and unreadable blobs in PS remoting and other modules.
- **Decision**: Enforce ultra-granular files (<100 lines when feasible) with feature-based folder cascades (e.g., `models/`, `config/`, `layers/`, `facade/`, `repo/`). No shims/legacy co-existence; breaking imports should surface so refactors complete. Use Python 3.14+/modern patterns, Pydantic v2 for runtime validation, and keep code “god-tier” readable/robust. Always run/align with pyright+pylint (config in repo), type hints everywhere.
- **Consequences**: More files but far clearer structure; easier agent handoffs; lint/type hygiene maintained by default. Legacy callers must be rewired, not papered over.

## Decision: No Interactive Prompts for Credentials

- **Date**: 2026-01-05
- **Context**: PS remoting attempts were triggering PowerShell credential prompts, breaking automation and IDEs.
- **Decision**: All PS remoting paths must supply explicit credentials programmatically; credential-less attempts are disallowed. If no usable credentials are present, fail fast with a clear error. Never invoke `Get-Credential` or allow PowerShell to prompt.
- **Consequences**: Removes accidental interactive loops; requires explicit credential configuration for targets; improves reproducibility and offline automation.

Last Updated: 2026-01-05

