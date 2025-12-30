# Action Sheet Manual Entries & Logging

## Overview

The Action sheet serves as the append-only audit log for all changes, discrepancies, and notable events—both automated (from Change Tracker logic) and manual (user-entered for external changes). It is the primary historical record, ensuring resilience across multi-day audits.

## Manual Row Insertion

Users can manually add rows to log changes that occur outside the app's detection (e.g., server updates by on-premise techs before audit starts, or fixes applied while the app is offline).

- **When to Use**: For events not captured by automated sync, such as pre-audit changes or manual interventions.
- **Process**:
  1. Add a new row in the Action sheet.
  2. Populate required fields: Entity details, change description, date (manually set for accuracy).
  3. Sync will persist the row with a generated `row_uuid` for tracking.
- **Validation**: Only allow additions if they don't conflict with existing automated entries (e.g., no duplicate UUIDs).

## Editable Dates

Dates in the Action sheet are auto-generated based on sync run time, but must be manually editable for accuracy.

- **Why**: Sync might run days after changes occur (e.g., lead auditor logs findings on return). Dates must reflect actual event times, not sync times.
- **Fields**: `Detected Date`, `Action Date`—editable by user.
- **Sync Behavior**: On sync, preserve user-edited dates; log changes in history.

## Append-Only Nature

- **Rule**: No deletions or overwrites—only append new rows.
- **Produced By**: Change Tracker logic for discrepancies, plus manual entries.
- **Includes Non-Discrepant Logables**: Events like user additions, version changes within acceptable ranges, irrelevant tweaks—even if not failures.

## Columns & Data Flow

- **Key Columns**: `Entity UUID`, `Sheet Name`, `Change Type`, `Description`, `Detected Date` (editable), `Action Date` (editable), `Notes`.
- **Persistence**: Synced to SQLite `actions` table with `row_uuid` for stability.
- **Audit Trail**: All changes logged in `annotation_history`.

## Resilience Considerations

Manual entries ensure no external changes are lost. Safeguards prevent corruption: validation on sync, audit trails, and read-only restrictions on automated fields.
