# Agent Knowledge Hub

Single entry point for all agents/IDEs. Follow this to avoid drift or missing context.

## Read/Update Order (every session)
1) `AGENT_SOP.md` — protocol and update rules.
2) `memory.md` — current state snapshot (mission, recent changes, gaps, key files, next actions).
3) `decisions/log.md` — binding architecture/strategy decisions.
4) `sessions/README.md` + latest dated log — narrative/timeline for continuity.
5) `backlog/todos.md` — prioritized work.
6) `docs/DOCUMENTATION_HUB.md` — project-wide docs entry (sync when behavior changes).

## What goes where (and priority if conflicting)
- **Decisions (`decisions/log.md`)**: authoritative constraints/architectural choices. Overrides older notes.
- **Memory (`memory.md`)**: current truth on state/gaps/next actions. If conflict with sessions, prefer memory unless decisions override.
- **Sessions (`sessions/*.md`)**: chronological narrative; never edit past entries.
- **Backlog (`backlog/todos.md`)**: prioritized work items; keep in sync with memory’s next actions.
- **Docs (`docs/DOCUMENTATION_HUB.md` + links)**: user/dev-facing source of truth; update when behavior/API changes.

## Change/Sync Checklist
- After code/doc changes: update memory → today’s session log → backlog (if priorities shift) → docs (if behavior/API changes) → decisions (if constraints change).
- Record lint/type/test status for touched areas in session log and memory.
- Keep all state files concise, comprehensive, and current—no stale entries.

## Quick Links
- Protocol: `AGENT_SOP.md`
- State snapshot: `memory.md`
- Decisions: `decisions/log.md`
- Sessions index: `sessions/README.md`
- Backlog: `backlog/todos.md`
- Project docs entry: `docs/DOCUMENTATION_HUB.md`
