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

## Sync Rules (during work + end-of-work)
- Sync whenever you hit a milestone, make notable changes, or the user asks—don’t wait until session end.
- For each sync: update `memory.md` (state snapshot) → current `sessions/YYYY-MM-DD.md` (narrative) → `backlog/todos.md` (priorities) → docs (`docs/DOCUMENTATION_HUB.md` + relevant pages) if behavior/API/requirements changed → `decisions/log.md` only when constraints/architecture change.
- Keep entries concise, comprehensive, and current—no stale or conflicting notes.

## Code/Posture Standards
- Default to ultra-granular files (<100 lines when feasible) and feature-based folder cascades; no big blobs or shims/legacy co-existence. Breaking imports should surface so refactors complete.
- Use Python 3.14+ patterns, Pydantic v2 for runtime modeling, and keep code “god-tier” readable and robust.
- Maintain lint/type hygiene: pyright + pylint (repo config) for touched areas; add type hints everywhere practical.

## Hygiene Rules
- Never delete prior session/decision history; append instead.
- Keep links between AgentStuff and docs coherent (both directions when applicable).
- Prefer factual, concise entries; avoid ambiguity.
