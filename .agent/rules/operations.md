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
