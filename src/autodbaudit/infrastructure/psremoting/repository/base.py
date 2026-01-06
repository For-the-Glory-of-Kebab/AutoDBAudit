"""
Base repository utilities (connection handling and schema setup).
"""

import sqlite3
from contextlib import contextmanager
from typing import Optional, Union

from ..models import ConnectionMethod
from . import schema


class RepositoryBase:
    """Shared connection and schema helpers."""

    def __init__(self, db_path: str = "audit_history.db"):
        self.db_path = db_path
        self._ensure_tables()

    @contextmanager
    def _get_connection(self):
        """Get database connection with proper cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _ensure_tables(self) -> None:
        """Ensure schema and columns exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            schema.ensure_tables(cursor)
            schema.ensure_columns(cursor)
            conn.commit()

    @staticmethod
    def _cm_value(method: Optional[Union[ConnectionMethod, str]]) -> Optional[str]:
        """Normalize connection_method to string."""
        if method is None:
            return None
        if hasattr(method, "value"):
            return method.value  # type: ignore[return-value]
        return str(method)
