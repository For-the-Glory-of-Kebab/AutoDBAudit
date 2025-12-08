"""
SQLite infrastructure package.

Provides SQLite history storage for audit data persistence.
"""

from autodbaudit.infrastructure.sqlite.store import HistoryStore
from autodbaudit.infrastructure.sqlite.schema import (
    SCHEMA_V2_TABLES,
    initialize_schema_v2,
)

__all__ = [
    "HistoryStore",
    "SCHEMA_V2_TABLES",
    "initialize_schema_v2",
]
