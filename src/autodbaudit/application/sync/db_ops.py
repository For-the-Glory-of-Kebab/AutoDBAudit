"""
Database Operations for Annotation Sync.

Handles all SQLite read/write operations for annotations.
Provides clean interface between sync service and storage layer.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlite3 import Connection

logger = logging.getLogger(__name__)


# Database operations have been moved to autodbaudit.utils.database
# to eliminate duplicate code across the codebase.
# Use persist_annotations_to_db and load_annotations_from_db from utils.database instead.
