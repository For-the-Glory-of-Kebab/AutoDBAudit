Audit lifecycle and data integrity

Make the audit a state machine in SQLite
Statuses like DRAFT/IN_PROGRESS/FINALIZED (plus optional ABANDONED). Enforce transitions: no --sync after --finalize unless explicit --reopen that creates a new revision/run.

Treat SQLite as the source of truth; Excel is a view + annotation layer
DB owns facts, timestamps, results, action log. Excel owns only human annotations (notes/exception rationale/approvals/ticket IDs). On sync, import only whitelisted fields.

Stable row identifiers are mandatory (Excel round-trip safety)
Never rely on row numbers or ordering. Every result row needs a stable key (best: UUID result_id). Write it to Excel (hidden column) and use it for syncing notes back.

Make --sync idempotent and resumable
Safe to run repeatedly; no duplicated action logs. Record per-target sync outcomes. Partial sync is normal (servers down / access issues). Track last_synced_at and per-row last_checked_at.

“Actions taken” and audit trail realism

Classify actions explicitly
DETECTED (system inferred), EXECUTED (tool ran something), ATTESTED (human marked done). Each action record includes who/when/how + evidence.

Evidence matters
Store before/after values (build numbers, config values), query output snippets or references, installer exit codes/log paths. Avoid “trust me bro” audit logs.

Finalize is a locking event
On --finalize: freeze run, generate final Excel, store output path + hash, and prevent further modifications. If changes are needed later, create a new run/revision tied to the original.

Operational safety and robustness

Define what can be edited in Excel and enforce it
Use protected sheets/locked cells for computed fields. Leave only annotation columns unlocked. Sync code should ignore any edits outside whitelisted columns.

Concurrency with guardrails
For multi-server operations (audit + hotfix): bounded concurrency (e.g., 3–5 workers), per-target timeouts, retries with backoff, and “do not overwhelm the domain/network”.

Crash-safe progress tracking
Persist “step status” to DB frequently (RUNNING/SUCCEEDED/FAILED). On restart, resume from DB state. This is critical for hotfix orchestration.

Versioning and evolution (you will thank yourself later)

Schema versioning
Add schema_version table. Prefer additive migrations. Never silently change schema without a version bump/migration path.

Config hashing for reproducibility
Store a hash of the config + query set used for an audit run (config_hash, maybe queries_hash) so you can prove what you ran.

Requirement versioning
Your db-requirements.md evolves. Track requirement IDs and a requirement_version or last_modified_hash so old audits remain interpretable when requirements change.

Hotfix-specific must-haves (since it’s risky)

Plan vs execute modes
--hotfix-plan produces a plan + report without running anything. Only --deploy executes. Always keep a dry-run.

Remote execution abstraction
One module owns remote execution (WinRM/PowerShell remoting). Everything else calls it. Central logging + consistent exit code handling.

Safety checks
Verify connectivity, disk space, pending reboot status, maintenance window flags (if you can), and confirm expected SQL build after patch.