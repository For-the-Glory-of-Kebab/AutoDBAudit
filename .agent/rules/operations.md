---
trigger: always_on
---


# Operations Rules
## Commands (see /no-prompts workflow)
- **Trivial ops**: Auto-run via wrapper scripts (tests, linting, file ops within repo)
- **Never**: Pipe commands, 2>&1, semicolons, python -c, direct .exe from venv
- **Always**: Use scripts/run_*.ps1 wrappers for complex commands
- if there's a case that isn't covered by our wrapping scripts, just add one for your usecase.
- remember not to miss venv activation in any of the wrapper scripts.
## Safety
- **NEVER** modify/delete files outside repo root
- Within repo: full freedom (git has our back)
- although before big potentially lossy changes, suggest a commit if we've changed since the last one so we have a history to fallback to.
- No commit commands - ask when ready to commit
## Documentation
- Sync docs/ after every feature/milestone
- the syncs include vision, decisions, observations, documentation on the structure and the modules, the direction, roadmap, progress, questions, ambiguities, basically everything related to this.
- Keep task.md, implementation_plan.md updated
- no out of sync or misleading or deprecated comments, docs or files should be left around.
- Goal: New session resumes with full context at anytime with any AI model.

## VS Code Agent Preferences (Synced)

- **Git Operations**: Never perform server-side git operations like push, pull, merge, or any remote repository actions without explicit user instruction. Always ask the user to execute them. Commits and local operations are fine, but no server-side actions.
- **Commits**: Always ask before committing changes to git unless explicitly requested by the user, to avoid broken or cluttered history.
- **Persistence**: Preferences are stored persistently across sessions.
- **Tracking**: Use AgentStuff/ for session logs, decisions, and backlog.
- **Collaborative Approach**: Proactively suggest improvements, catch bugs, disagree with decisions. This is collaborative engineering, not a "typing machine". Actively use intelligence to critique, suggest, agree or disagree. For major decisions (architecture, new deps, breaking changes), discuss first. When unsure, ask — don't guess on business logic or architecture.
- **Intelligent Suggestions**: Suggest and refine fitting architectures, god-tier veteran modern Python design patterns. Focus on code quality: max file size 400 lines, Python 3.11+ features, clear package hierarchy, well-defined interfaces, no dead code. Domain-driven architecture with single responsibility, dependency injection, robust error handling.
- **Learning-First Collaboration**: For each phase, all changes, decisions, suggestions, and approaches must be explained to the user — from intermediate Pythonic techniques and design patterns to veteran architectural decisions, cutting-edge tooling, and libraries. The goal is a collaborative code-and-learn experience, not just code delivery.
