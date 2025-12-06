# Excel Report Layout

> **Status**: Excel report generation is **not yet implemented**. This document describes the **planned structure** based on architecture decisions.

---

## Overview

Excel reports are generated from the SQLite history store (`output/history.db`) via `openpyxl`. They serve as human-readable views of audit data—not source-of-truth.

---

## Current Implementation Status

| Component | Status |
|-----------|--------|
| `infrastructure/excel_writer.py` | ❌ Not implemented |
| Sheet generation | ❌ Planned only |
| Conditional formatting | ❌ Planned only |
| Charts | ❌ Planned only |
| Incremental mode | ⚠️ CLI flag exists, logic not implemented |

---

## Planned Sheets

Once implemented, reports will contain these sheets:

### Core Sheets (Every Report)

| Sheet Name | Purpose | Key Columns |
|------------|---------|-------------|
| **Audit Summary** | Multi-year overview (if incremental) | Audit Date, Org, Servers, Violations, Actions, Compliance % |
| **{Year} Cover** | Title page for current audit | Org name, date, auditor, summary stats |
| **{Year} Compliance** | Per-requirement compliance status | Req #, Title, Status (✅/❌/⚠️), Count |
| **{Year} Discrepancies** | All violations found | Server, Instance, Req #, Finding, Severity |
| **{Year} ActionLog** | Remediation actions taken | Script, Server, Status, Timestamp, User |

### Data Sheets

| Sheet Name | Purpose | Key Columns |
|------------|---------|-------------|
| **InstanceInfo** | Server/instance inventory | Hostname, Instance, Version, Edition, Build |
| **ServerLogins** | Login audit | Login, Type, IsDisabled, DefaultDB, Roles |
| **DatabaseUsers** | Per-database users | Database, User, Login, Roles |
| **DisabledFeatures** | Req 10/16/18-21 status | Feature, Expected, Actual, Compliant |
| **TestDatabases** | Req 15 findings | Database, Type, Recommendation |

### Hotfix Sheet (Optional)

| Sheet Name | Purpose | Key Columns |
|------------|---------|-------------|
| **{Year} Hotfix Deployment** | Patch deployment results | Server, Pre-Build, Post-Build, Status, Installers |

### Trend Sheets (Incremental Mode)

| Sheet Name | Purpose | Key Columns |
|------------|---------|-------------|
| **ServerHistory** | Server add/remove timeline | Date, Server, Event, Notes |
| **RequirementTrends** | Compliance over time | Req #, 2023, 2024, 2025, Trend |

---

## Planned Formatting

### Header Row
- Bold, dark blue background (#1F497D), white text
- Frozen pane (first row)
- Auto-filter enabled

### Data Rows
- Alternating row colors (white / light gray)
- Auto-fit column widths
- Date columns formatted as YYYY-MM-DD

### Conditional Formatting

| Element | Rule | Visual |
|---------|------|--------|
| Compliance status | `pass` → green, `fail` → red, `exception` → yellow | Background color |
| Severity | `critical` → red, `warning` → orange, `info` → blue | Font color |
| Icons (planned) | Status columns | ✅ ❌ ⚠️ via `IconSetRule` |

### Charts (Planned)

- **Compliance Pie Chart**: % pass / fail / exception
- **Violations by Category**: Bar chart
- **Trend Line**: Compliance % over time (incremental mode)

---

## Report Modes

### Single-Shot Mode
```bash
AutoDBAudit.exe --audit --config config/audit_config.json
```
- Generates a new workbook with current audit only
- Filename: `{Org}_SQL_Audit_{Date}.xlsx`

### Incremental Mode
```bash
AutoDBAudit.exe --audit --config config/audit_config.json \
  --append-to output/Acme_SQL_Audit_History.xlsx
```
- Opens existing workbook
- Adds new `{Year}` sheets at the front
- Updates **Audit Summary** and trend sheets
- Preserves all historical data

---

## Future Ideas (Not Implemented)

- [ ] Grouped rows by server (collapsible)
- [ ] Sparklines in trend columns
- [ ] Rich text comments linking to remediation scripts
- [ ] PDF export option
- [ ] Executive summary sheet with dashboard-style layout
- [ ] Data validation dropdowns for exception reasons
- [ ] Hyperlinks to SQLite row IDs for drill-down

---

## Implementation Notes

When implementing `infrastructure/excel_writer.py`:

1. Use `openpyxl.Workbook()` for new reports
2. Use `openpyxl.load_workbook()` for incremental mode
3. Query SQLite for data; never read from previous Excel
4. Apply styles consistently via reusable style objects
5. Use `write_only=True` mode for large datasets if needed

---

*Last updated: 2025-12-06*
