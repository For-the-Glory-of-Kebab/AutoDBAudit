# AutoDBAudit Documentation Hub

Welcome to the comprehensive documentation for the **AutoDBAudit** project.
This documentation is structured to be the **Single Source of Truth** for all functionalities, schemas, and workflows.

> **Navigation**: Use the breadcrumbs at the top of each page and cross-references throughout.
> **For AI/Developers**: Each document includes prerequisites, related docs, and implementation standards.
> **Version**: This documentation is for AutoDBAudit v1.0.0
> **Offline-first**: AutoDBAudit must run fully offline on Windows hosts. Avoid external network calls (e.g., public IP probes) in tooling and scripts.

## 🔒 Prepare & Remoting API
- The Prepare service exposes a status API (see `application/prepare/status_service.py`) to query or trigger PS remoting readiness, returning `ServerConnectionInfo` snapshots (OS type, available methods, attempts, cache/persistence-backed).
- PS remoting persistence lives in infra `psremoting/repository.py`; cache layer in `application/prepare/cache/cache_manager.py`. Other layers (audit/remediate/sync/hotfix) should consume this API rather than re-running prep logic.
- Facade implemented: `psremoting/facade.py` provides `get_status`, `ensure_prepared`, `run_command`, `run_script`, and `revert`, returning structured `CommandResult`/`PSRemotingResult` data (auth/protocol/port/credential_type used, stdout/stderr/exit_code, revert scripts, troubleshooting). It reuses persisted profiles/successful permutations and targets admin-level sessions; consumers must not parse ad-hoc strings.
- Automation is non-interactive: all PS remoting attempts must supply explicit credentials; credential-less/`Get-Credential` prompts are forbidden. If no usable creds are configured, the engine fails fast with a clear error.
- Current status: localhost prep still failing pending elevated re-test; past failures show PowerShell credential construction issues (ConvertTo-SecureString autoload). Run prepare in an elevated shell to allow client/target config layers.

---

## 🚀 [Getting Started](getting-started/README.md)

Everything you need to set up and start using AutoDBAudit.

* **[System Requirements](getting-started/requirements.md)**: Hardware, software, and permission prerequisites
* **[Installation Guide](getting-started/installation.md)**: Step-by-step setup for different environments
* **[Quick Start](getting-started/quick-start.md)**: Get auditing in 10 minutes
* **[Configuration Guide](getting-started/configuration.md)**: All configuration options explained

## 👥 [User Guide](user-guide/README.md)

Complete end-to-end workflows for all user roles.

* **[Audit Lifecycle](user-guide/audit-lifecycle.md)**: Complete audit process from start to finish
* **[Excel Interface Guide](user-guide/excel-interface.md)**: Using the Excel report interface
* **[Remediation Workflows](user-guide/remediation-workflows.md)**: Generating and applying fixes
* **[Multi-Audit Management](user-guide/multi-audit-management.md)**: Managing multiple audit cycles

## 🔧 [Reference Documentation](reference/README.md)

Technical reference for implementation and integration.

* **[CLI Reference](cli/reference.md)**: Complete command reference with examples
* **[API Reference](reference/api.md)**: Developer API documentation
* **[Configuration Schema](reference/configuration-schema.md)**: All config file specifications
* **[Database Schema](database/schema_comprehensive.md)**: SQLite schema reference
* **[Error Codes](reference/error-codes.md)**: Exit codes and error handling

## 🏗️ [Architecture & Design](architecture/README.md)

System architecture, design patterns, and standards.

* **[Architecture Overview](architecture/overview.md)**: High-level system design
* **[Design Standards](architecture/standards.md)**: Coding standards and patterns
* **[Domain Models](architecture/domain-models.md)**: Core business logic models
* **[ADRs](adrs/)**: Architecture Decision Records

## 🧪 [Testing & Quality](testing/README.md)

Testing strategies, simulation tools, and quality assurance.

* **[Testing Strategy](testing/strategy.md)**: Overall testing approach
* **[Discrepancy Simulation](testing/discrepancy_simulation.md)**: Test data generation
* **[End-to-End Testing](testing/e2e-testing.md)**: Full workflow validation

## 🚀 [Deployment & Operations](deployment/README.md)

Production deployment, monitoring, and maintenance.

* **[Deployment Guide](deployment/guide.md)**: Production deployment procedures
* **[Monitoring](deployment/monitoring.md)**: Health checks and alerting
* **[Troubleshooting](deployment/troubleshooting.md)**: Common issues and solutions
* **[Backup & Recovery](deployment/backup-recovery.md)**: Data protection strategies
* **[Performance Guide](deployment/performance.md)**: Performance optimization and scaling

## 🤝 [Contributing](contributing/README.md)

Guidelines for contributors and maintainers.

* **[Development Setup](contributing/development-setup.md)**: Setting up development environment
* **[Coding Standards](contributing/coding-standards.md)**: Code style and conventions
* **[Testing Guidelines](contributing/testing.md)**: Writing and running tests
* **[Release Process](contributing/release-process.md)**: Versioning and releases

## 📚 [Appendices](appendices/README.md)

Supporting information and resources.

* **[Glossary](appendices/glossary.md)**: All terms, acronyms, and concepts
* **[FAQ](appendices/faq.md)**: Frequently asked questions
* **[Changelog](appendices/changelog.md)**: Version history and changes
* **[License](appendices/license.md)**: Licensing information

---

## 📖 Documentation Standards

### Navigation & Structure

* **Breadcrumbs**: Each page shows its location in the hierarchy
* **Cross-references**: Related documents are linked throughout
* **Table of Contents**: Every document has a TOC
* **Consistent Headers**: Standardized section naming

### Content Standards

* **Prerequisites**: Each document lists what you need to know first
* **Related Documents**: Links to connected information
* **Implementation Standards**: References to coding standards
* **Version Information**: When content was last updated

### For AI/Developers

* **Single Source of Truth**: No duplicate information
* **Cascading Information**: Standards flow from general to specific
* **Machine-readable**: Structured for automated processing
* **Complete Coverage**: Nothing left to imagination

### 🤖 For AI Agents

#### 🚨 CRITICAL: Session Continuity Protocol

If you are an AI agent working on this project, start at `AgentStuff/AGENT_HUB.md` (navigation + SOP), then read `AgentStuff/memory.md` before making changes. These files contain:

* **Complete Working Copy of Agent Brain**: Current status, thought history, implementation plans
* **Session Resume Instructions**: Step-by-step protocol for seamless continuation
* **Architectural Decisions**: All key decisions and constraints
* **Current Implementation State**: What's complete, what's in progress, what's missing
* **Quality Gates**: Code standards, testing requirements, linting rules

**Memory Sync Rule**: The `AgentStuff/memory.md` file is kept synchronized with the current session state. If this file exists, it takes precedence over any assumptions about project status.

**Before Starting Work**:

1. Open `AgentStuff/AGENT_HUB.md` and follow its read order.
2. Read `AgentStuff/memory.md` completely.
3. Check `AgentStuff/sessions/` for recent activity.
4. Review `AgentStuff/decisions/` for architectural decisions.
5. Update memory + session log after any significant changes.

---

## 🔍 Quick Navigation

| I want to... | Go to... |
| --- | --- |
| Start using AutoDBAudit | [Quick Start](getting-started/quick-start.md) |
| Understand the system | [Architecture Overview](architecture/overview.md) |
| Run commands | [CLI Reference](cli/reference.md) |
| Configure the system | [Configuration Guide](getting-started/configuration.md) |
| Fix issues | [Troubleshooting](deployment/troubleshooting.md) |
| Contribute code | [Contributing](contributing/README.md) |

---

Last updated: 2025-12-30 | AutoDBAudit v1.0.0
