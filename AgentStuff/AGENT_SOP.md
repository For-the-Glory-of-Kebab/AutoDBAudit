# Agent Session SOP

Follow this protocol every time you work on the project to prevent regressions and lost context.

## Start/Resume Checklist
1) Open `AGENT_HUB.md` and follow the read order.
2) Read `memory.md` (state snapshot) and the latest `sessions/YYYY-MM-DD.md`.
3) Review `decisions/log.md` (active constraints) and `backlog/todos.md` (priorities).
4) Skim `docs/DOCUMENTATION_HUB.md` if making behavior changes that affect docs/API.

## During Work
- Keep files small and feature-grouped; avoid duplicating implementations already present.
- When changing behavior or APIs, note it for doc updates and cross-links.
- Run lint/type/tests for touched areas; record status in the session log and adjust memory if outcomes change the plan.

## End-of-Work Updates
1) Update `memory.md` (recent changes, open gaps, next actions, tooling status).
2) Update the day’s `sessions/YYYY-MM-DD.md` with actions taken and next steps.
3) Adjust `backlog/todos.md` if priorities shift; add/remove items explicitly.
4) Sync docs: ensure `docs/DOCUMENTATION_HUB.md` (and related pages) reflect changes.
5) If architectural constraints change, append to `decisions/log.md`.
6) Keep all state files concise, comprehensive, and current—no stale entries.

## Hygiene Rules
- Never delete prior session/decision history; append instead.
- Keep links between AgentStuff and docs coherent (both directions when applicable).
- Prefer factual, concise entries; avoid ambiguity.
