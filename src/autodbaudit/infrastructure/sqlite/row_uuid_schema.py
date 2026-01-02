"""
Row UUID Schema Migration for SQLite.

Adds support for Row UUID-based annotation tracking.
This replaces entity_key-based matching with stable UUID identifiers.

Schema Version: 3 (adds row_annotations table)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ============================================================================
# New Schema for Row UUID Support
# ============================================================================

SCHEMA_V3_TABLES = """
-- ============================================================================
-- Row Annotations (UUID-based tracking)
-- ============================================================================
--
-- This table stores annotations keyed by row_uuid (stable identifier)
-- instead of entity_key (which changes when data changes).
--
-- One row per sheet row, storing all annotation fields together.
-- ============================================================================

CREATE TABLE IF NOT EXISTS row_annotations (
    id INTEGER PRIMARY KEY,

    -- Stable identifier (never changes)
    row_uuid TEXT UNIQUE NOT NULL,       -- 8-char hex from Excel Column A

    -- Entity reference (for debugging/display, NOT for matching)
    sheet_name TEXT NOT NULL,            -- Which sheet: 'Linked Servers', etc.
    entity_type TEXT NOT NULL,           -- 'linked_server', 'login', etc.
    entity_key TEXT,                     -- Legacy reference, for display only

    -- Lifecycle tracking
    status TEXT DEFAULT 'active',        -- 'active', 'resolved', 'orphaned'
    first_seen_at TEXT NOT NULL,         -- When row first appeared
    last_seen_at TEXT,                   -- Last sync that saw this row
    resolved_at TEXT,                    -- When marked resolved (row removed)

    -- Annotation fields (user-editable in Excel)
    purpose TEXT,                        -- Req: Purpose/Description
    notes TEXT,                          -- Req: Additional notes
    justification TEXT,                  -- Req: Exception justification
    review_status TEXT,                  -- '✓ Exception', '⏳ Needs Review', etc.
    last_reviewed TEXT,                  -- Date auditor last reviewed

    -- Metadata
    created_at TEXT NOT NULL,
    modified_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_row_annotations_uuid ON row_annotations(row_uuid);
CREATE INDEX IF NOT EXISTS idx_row_annotations_sheet ON row_annotations(sheet_name);
CREATE INDEX IF NOT EXISTS idx_row_annotations_status ON row_annotations(status);
CREATE INDEX IF NOT EXISTS idx_row_annotations_entity_key ON row_annotations(entity_key);

-- ============================================================================
-- Row Annotation History (Track Changes per UUID)
-- ============================================================================

CREATE TABLE IF NOT EXISTS row_annotation_history (
    id INTEGER PRIMARY KEY,
    row_uuid TEXT NOT NULL,              -- References row_annotations.row_uuid

    field_name TEXT NOT NULL,            -- Which field changed
    old_value TEXT,
    new_value TEXT,

    changed_at TEXT NOT NULL,
    sync_run_id INTEGER REFERENCES audit_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_row_annotation_history_uuid
    ON row_annotation_history(row_uuid);
"""


# ============================================================================
# Migration Functions
# ============================================================================


def migrate_to_v3(connection) -> None:
    """
    Migrate database to schema v3 (Row UUID support).

    Steps:
    1. Create new row_annotations table
    2. Migrate existing annotations to new table (if any)
    3. Update schema version

    Args:
        connection: SQLite connection
    """
    logger.info("Migrating to schema v3 (Row UUID support)...")

    # Check current version
    try:
        row = connection.execute(
            "SELECT value FROM schema_meta WHERE key = 'version'"
        ).fetchone()
        current_version = int(row["value"]) if row else 1
    except Exception:
        current_version = 1

    if current_version >= 3:
        logger.info("Already at schema v3, skipping migration")
        return

    # Create new tables
    connection.executescript(SCHEMA_V3_TABLES)

    # Update schema version
    connection.execute("""
        INSERT OR REPLACE INTO schema_meta (key, value)
        VALUES ('version', '3')
    """)

    connection.commit()
    logger.info("Schema v3 migration complete")


def check_schema_version(connection) -> int:
    """
    Check current schema version.

    Args:
        connection: SQLite connection

    Returns:
        Current schema version (1, 2, or 3)
    """
    try:
        row = connection.execute(
            "SELECT value FROM schema_meta WHERE key = 'version'"
        ).fetchone()
        return int(row["value"]) if row else 1
    except Exception:
        return 1


# ============================================================================
# Row Annotation CRUD Operations
# ============================================================================


def get_row_annotation(connection, row_uuid: str) -> dict | None:
    """
    Get annotation data for a row by UUID.

    Args:
        connection: SQLite connection
        row_uuid: 8-char hex UUID

    Returns:
        Dict with annotation fields or None if not found
    """
    row = connection.execute("""
        SELECT
            row_uuid, sheet_name, entity_type, entity_key,
            status, first_seen_at, last_seen_at, resolved_at,
            purpose, notes, justification, review_status, last_reviewed,
            created_at, modified_at
        FROM row_annotations
        WHERE row_uuid = ?
    """, (row_uuid.upper(),)).fetchone()

    if not row:
        return None

    return {
        "row_uuid": row["row_uuid"],
        "sheet_name": row["sheet_name"],
        "entity_type": row["entity_type"],
        "entity_key": row["entity_key"],
        "status": row["status"],
        "first_seen_at": row["first_seen_at"],
        "last_seen_at": row["last_seen_at"],
        "resolved_at": row["resolved_at"],
        "purpose": row["purpose"],
        "notes": row["notes"],
        "justification": row["justification"],
        "review_status": row["review_status"],
        "last_reviewed": row["last_reviewed"],
        "created_at": row["created_at"],
        "modified_at": row["modified_at"],
    }


def upsert_row_annotation(
    connection,
    row_uuid: str,
    sheet_name: str,
    entity_type: str,
    entity_key: str | None = None,
    purpose: str | None = None,
    notes: str | None = None,
    justification: str | None = None,
    review_status: str | None = None,
    last_reviewed: str | None = None,
    status: str = "active",
    sync_run_id: int | None = None,
) -> int:
    """
    Insert or update a row annotation.

    Args:
        connection: SQLite connection
        row_uuid: Stable 8-char hex UUID
        sheet_name: Sheet name (e.g., 'Linked Servers')
        entity_type: Entity type (e.g., 'linked_server')
        entity_key: Legacy entity key for reference
        purpose, notes, justification, review_status, last_reviewed: Annotation fields
        status: 'active', 'resolved', or 'orphaned'
        sync_run_id: Current sync run ID for history tracking

    Returns:
        Row ID
    """
    now = datetime.now(timezone.utc).isoformat()
    row_uuid = row_uuid.upper()

    # Check if exists
    existing = connection.execute("""
        SELECT id, purpose, notes, justification, review_status, last_reviewed
        FROM row_annotations
        WHERE row_uuid = ?
    """, (row_uuid,)).fetchone()

    if existing:
        # Update existing
        # Track changes in history
        changes = []
        if purpose != existing["purpose"]:
            changes.append(("purpose", existing["purpose"], purpose))
        if notes != existing["notes"]:
            changes.append(("notes", existing["notes"], notes))
        if justification != existing["justification"]:
            changes.append(("justification", existing["justification"], justification))
        if review_status != existing["review_status"]:
            changes.append(("review_status", existing["review_status"], review_status))
        if last_reviewed != existing["last_reviewed"]:
            changes.append(("last_reviewed", existing["last_reviewed"], last_reviewed))

        # Record history
        for field_name, old_val, new_val in changes:
            connection.execute("""
                INSERT INTO row_annotation_history
                (row_uuid, field_name, old_value, new_value, changed_at, sync_run_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (row_uuid, field_name, old_val, new_val, now, sync_run_id))

        # Update record
        connection.execute("""
            UPDATE row_annotations
            SET entity_key = COALESCE(?, entity_key),
                purpose = ?,
                notes = ?,
                justification = ?,
                review_status = ?,
                last_reviewed = ?,
                status = ?,
                last_seen_at = ?,
                modified_at = ?
            WHERE row_uuid = ?
        """, (
            entity_key, purpose, notes, justification, review_status, last_reviewed,
            status, now, now, row_uuid
        ))

        connection.commit()
        return existing["id"]

    # Insert new
    cursor = connection.execute("""
        INSERT INTO row_annotations
        (row_uuid, sheet_name, entity_type, entity_key,
         purpose, notes, justification, review_status, last_reviewed,
         status, first_seen_at, last_seen_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        row_uuid, sheet_name, entity_type, entity_key,
        purpose, notes, justification, review_status, last_reviewed,
        status, now, now, now
    ))

    connection.commit()
    return cursor.lastrowid


def get_all_row_annotations(connection, sheet_name: str | None = None) -> dict[str, dict]:
    """
    Get all row annotations, optionally filtered by sheet.

    Args:
        connection: SQLite connection
        sheet_name: Optional sheet filter

    Returns:
        Dict of row_uuid -> annotation data
    """
    if sheet_name:
        rows = connection.execute("""
            SELECT * FROM row_annotations WHERE sheet_name = ? AND status = 'active'
        """, (sheet_name,)).fetchall()
    else:
        rows = connection.execute("""
            SELECT * FROM row_annotations WHERE status = 'active'
        """).fetchall()

    result = {}
    for row in rows:
        result[row["row_uuid"]] = {
            "row_uuid": row["row_uuid"],
            "sheet_name": row["sheet_name"],
            "entity_type": row["entity_type"],
            "entity_key": row["entity_key"],
            "purpose": row["purpose"],
            "notes": row["notes"],
            "justification": row["justification"],
            "review_status": row["review_status"],
            "last_reviewed": row["last_reviewed"],
            "status": row["status"],
            "first_seen_at": row["first_seen_at"],
            "last_seen_at": row["last_seen_at"],
        }

    return result


def mark_row_resolved(connection, row_uuid: str) -> None:
    """
    Mark a row as resolved (no longer in Excel).

    Args:
        connection: SQLite connection
        row_uuid: UUID to mark as resolved
    """
    now = datetime.now(timezone.utc).isoformat()

    connection.execute("""
        UPDATE row_annotations
        SET status = 'resolved', resolved_at = ?, modified_at = ?
        WHERE row_uuid = ? AND status = 'active'
    """, (now, now, row_uuid.upper()))

    connection.commit()


def mark_rows_orphaned_if_missing(
    connection,
    sheet_name: str,
    seen_uuids: set[str],
) -> int:
    """
    Mark rows as orphaned if they weren't seen in current sync.

    Called after reading all rows from Excel to detect deleted rows.

    Args:
        connection: SQLite connection
        sheet_name: Sheet being synced
        seen_uuids: Set of UUIDs seen in Excel

    Returns:
        Number of rows marked as resolved
    """
    now = datetime.now(timezone.utc).isoformat()

    # Get all active UUIDs for this sheet
    active = connection.execute("""
        SELECT row_uuid FROM row_annotations
        WHERE sheet_name = ? AND status = 'active'
    """, (sheet_name,)).fetchall()

    count = 0
    for row in active:
        uuid = row["row_uuid"]
        if uuid not in seen_uuids and uuid.upper() not in seen_uuids:
            # Not seen in Excel = row was deleted/fixed
            connection.execute("""
                UPDATE row_annotations
                SET status = 'resolved', resolved_at = ?, modified_at = ?
                WHERE row_uuid = ?
            """, (now, now, uuid))
            count += 1

    if count > 0:
        connection.commit()
        logger.info("Marked %d rows as resolved in sheet %s", count, sheet_name)

    return count
