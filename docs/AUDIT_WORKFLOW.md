# AutoDBAudit - Complete Workflow Design

> **Purpose**: Definitive reference for the audit lifecycle. Read this first.

---

## Overview

AutoDBAudit is a SQL Server security audit tool with a complete remediation workflow:

1. **Audit** → Collect current state from SQL Server instances
2. **Remediate** → Generate and execute fix scripts
3. **Sync** → Track progress, log actions with real timestamps
4. **Finalize** → Persist final state + all annotations to database

**Key Principle**: Excel is the UI for human input. SQLite is the source of truth for reproducibility.

---

## Workflow Phases

### Phase 1: Initial Audit (`--audit`)

```bash
python main.py --audit --targets sql_targets.json
```

**What it does**:
- Connects to all SQL Server instances in targets file
- Collects security data (logins, configs, databases, etc.)
- Identifies findings (PASS/FAIL/WARN) with risk levels
- Writes to **Excel** (human-readable report)
- Writes to **SQLite** (baseline for diff)

**Repeatable**: Yes. Can add instances, re-run on failures. Incremental.

**Output**:
- `output/sql_audit_YYYYMMDD_HHMMSS.xlsx`
- `output/audit_history.db` (SQLite)

---

### Phase 2: Remediation Scripts (`--generate-remediation`)

```bash
python main.py --generate-remediation
```

**What it does**:
- Reads findings from SQLite
- Generates per-instance TSQL scripts
- Scripts include:
  - **Commented-out fixes** (uncomment to apply)
  - **Manual intervention notes** (updates, backups, etc.)

**Output**:
- `output/remediation_scripts/remediate_<server>_<instance>_<timestamp>.sql`

**Script format**:
```sql
-- ============================================================
-- REMEDIATION SCRIPT FOR: localhost\SQLEXPRESS
-- Generated: 2025-12-09
-- ============================================================

-- === SA Account ===
-- Status: FAIL | Risk: critical
-- 
-- -- Disable SA account
-- ALTER LOGIN [sa] DISABLE;
-- GO

-- === Manual Interventions ===
-- [ ] Install latest SQL Server cumulative update
-- [ ] Configure backup jobs for missing databases
-- [ ] Review linked server permissions with DBA team
```

---

### Phase 3: Execute Remediation

**Option A**: Manual execution in SSMS
- Open generated script
- Uncomment desired fixes
- Execute

**Option B**: Via the app (future)
```bash
python main.py --run-remediation --script remediate_xxx.sql
```

---

### Phase 4: Sync Progress (`--sync`)

```bash
python main.py --sync
```

**What it does**:
1. Runs a new audit (current state)
2. Diffs against **initial baseline** (not previous sync)
3. Detects:
   - **Fixed**: FAIL → PASS (logs action with **current timestamp**)
   - **Potential Exception**: Still FAIL (needs justification)
   - **Regression**: PASS → FAIL (new problem!)
4. Updates **Excel Action Sheet** with action log
5. Marks potential exceptions in Excel for user input

**Repeatable**: Yes. Run after each fix or batch of fixes.

**Timestamp Behavior**:
- New fixes get **today's timestamp** when first detected
- Previously logged fixes keep their **original timestamp**
- This creates an accurate audit trail of when fixes occurred

**Example Action Log**:
| Entity | Action | Date | Description |
|--------|--------|------|-------------|
| localhost\SA | Fixed | 2025-12-03 | Disabled SA account |
| xp_cmdshell | Fixed | 2025-12-05 | Set to 0 |
| PRODDB | Exception | - | Needs justification |

---

### Phase 5: Add Justifications (Manual in Excel)

User opens Excel and fills in:

| Column | Purpose | Example |
|--------|---------|---------|
| **Notes** | Technical explanation | "Required for legacy app X" |
| **Reason** | Business justification | "Approved by CTO per ticket #1234" |
| **Status Override** | Accept/Reject/Exception | "Exception" |

This applies to:
- **Exceptions**: Items that can't be fixed
- **Users/Logins**: Why they exist, who approved
- **Any finding**: Additional context for auditors

---

### Phase 6: Finalize (`--finalize`)

```bash
python main.py --finalize --excel output/sql_audit_edited.xlsx
```

**What it does**:
1. Reads all annotations from Excel (Notes, Reasons, Status Overrides)
2. Runs final audit snapshot
3. Computes final diff (initial → final)
4. Persists to SQLite:
   - **Final audit state** (all findings)
   - **Action log** (with real timestamps)
   - **Exceptions** (with justifications)
   - **All annotations** (even non-exception notes)
5. Marks audit run as "finalized"

**Irreversible**: This is the "commit" of the audit cycle.

**DB becomes source of truth**: The entire audit is reproducible from SQLite, even if Excel is lost.

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SQL Server Instances                         │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                          --audit
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SQLite (audit_history.db)              │  Excel (sql_audit.xlsx)   │
│  ─────────────────────────              │  ─────────────────────    │
│  • audit_runs                           │  • Summary sheet          │
│  • findings (baseline)                  │  • SA Account sheet       │
│  • servers, instances                   │  • Logins sheet           │
│                                         │  • Config Settings sheet  │
│                                         │  • etc.                   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                    --generate-remediation
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Remediation Scripts                                                │
│  • Per-instance TSQL                                                │
│  • Commented fixes + manual notes                                   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                       [User executes fixes]
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  --sync (repeatable)                                                │
│  • Re-audit current state                                           │
│  • Diff vs baseline                                                 │
│  • Log actions with REAL timestamps                                 │
│  • Mark potential exceptions                                        │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                       [User adds Notes/Reasons in Excel]
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  --finalize                                                         │
│  • Read Excel annotations                                           │
│  • Final audit snapshot                                             │
│  • Persist everything to SQLite                                     │
│  • DB = complete audit record                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## What Gets Persisted (Final State)

| Table | Content | Purpose |
|-------|---------|---------|
| `audit_runs` | Run metadata, status=finalized | Audit lifecycle |
| `findings` (baseline) | Initial FAIL/WARN items | What we started with |
| `findings` (final) | Final state | What we ended with |
| `action_log` | Fixed items + timestamps | Audit trail |
| `annotations` | All Notes/Reasons | Context for everything |
| `annotation_history` | Change history | Who changed what when |

---

## Key Design Decisions

### 1. Initial + Final Only
We don't persist every `--sync` run. Only:
- Initial baseline (first `--audit`)
- Final state (`--finalize`)

The action log captures **when** fixes happened.

### 2. Real Timestamps
Actions are logged with the timestamp when `--sync` first detects them, not when `--finalize` runs. This creates an accurate audit trail.

### 3. Excel = UI, SQLite = Truth
Excel is for human interaction (input Notes/Reasons). SQLite is the permanent record. The audit is reproducible from SQLite alone.

### 4. Everything Annotated
Not just exceptions. Every user, login, linked server can have Notes explaining why it exists. This context is persisted for future auditors.

---

## File Structure

```
AutoDBAudit/
├── main.py                          # Entry point
├── sql_targets.json                 # Target instances
├── config/
│   └── security_settings.json       # What to check
├── output/
│   ├── sql_audit_*.xlsx             # Excel reports
│   ├── audit_history.db             # SQLite database
│   └── remediation_scripts/         # Generated TSQL
├── src/autodbaudit/
│   ├── application/
│   │   ├── audit_service.py         # Main audit logic
│   │   ├── data_collector.py        # Collects from SQL Server
│   │   ├── remediation_service.py   # Generates TSQL
│   │   ├── finalize_service.py      # Diff + finalize
│   │   └── exception_service.py     # Excel → SQLite
│   ├── infrastructure/
│   │   ├── sqlite/
│   │   │   ├── schema.py            # All tables + helpers
│   │   │   └── history_store.py     # CRUD operations
│   │   └── excel/
│   │       └── report_writer.py     # Excel generation
│   └── interface/
│       └── cli.py                   # CLI commands
└── docs/
    ├── AUDIT_WORKFLOW.md            # This file
    ├── SCHEMA_DESIGN.md             # SQLite schema reference
    └── CLI_REFERENCE.md             # Command reference
```

---

## Quick Start

```bash
# 1. Initial audit
python main.py --audit

# 2. Generate remediation scripts
python main.py --generate-remediation

# 3. Execute fixes (in SSMS or via app)

# 4. Sync progress (repeat as needed)
python main.py --sync

# 5. Add Notes/Reasons in Excel

# 6. Finalize
python main.py --finalize --excel output/sql_audit_edited.xlsx
```

---

*Document Version: 1.0 | Last Updated: 2025-12-09*
