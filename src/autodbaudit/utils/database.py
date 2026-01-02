"""
Database utilities for common operations.

This module provides shared database operations used across the application.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


def persist_annotations_to_db(db_path: Path | str, annotations: Dict[str, Dict]) -> int:
    """
    Persist annotations to SQLite database.

    Args:
        db_path: Path to SQLite database
        annotations: Dict of {entity_type|entity_key: {field_name: value}}

    Returns:
        Number of annotations saved
    """
    from datetime import datetime
    from autodbaudit.infrastructure.sqlite.schema import set_annotation

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    count = 0
    for full_key, fields in annotations.items():
        parts = full_key.split("|", 1)
        if len(parts) != 2:
            continue

        entity_type, entity_key = parts

        for field_name, value in fields.items():
            if value is not None:
                # Convert datetime to string if needed
                if isinstance(value, datetime):
                    value = value.isoformat()

                set_annotation(
                    connection=conn,
                    entity_type=entity_type,
                    entity_key=entity_key,
                    field_name=field_name,
                    field_value=str(value),
                )
                count += 1

    conn.close()
    logger.info("Persisted %d annotations to database", count)
    return count


def load_annotations_from_db(db_path: Path | str) -> Dict[str, Dict]:
    """
    Load all annotations from SQLite database.

    Args:
        db_path: Path to SQLite database

    Returns:
        Dict of {entity_type|entity_key: {field_name: value}}
    """
    annotations: Dict[str, Dict] = {}

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute(
            "SELECT entity_type, entity_key, field_name, field_value FROM annotations"
        ).fetchall()
    except sqlite3.OperationalError:
        # Table may not exist yet
        conn.close()
        return annotations

    for row in rows:
        # Normalize to lowercase for consistent matching
        entity_type = row["entity_type"].lower() if row["entity_type"] else ""
        entity_key = row["entity_key"].lower() if row["entity_key"] else ""
        full_key = f"{entity_type}|{entity_key}"

        if full_key not in annotations:
            annotations[full_key] = {}
        annotations[full_key][row["field_name"]] = row["field_value"]

    conn.close()
    logger.info("Loaded %d annotation entries from database", len(annotations))
    return annotations


def get_db_connection(db_path: Path | str) -> sqlite3.Connection:
    """Get a database connection with row factory set."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn
