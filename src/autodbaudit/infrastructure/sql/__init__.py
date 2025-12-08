"""
SQL Server infrastructure package.

Provides SQL Server connectivity and version-specific query providers.
"""

from autodbaudit.infrastructure.sql.connector import SqlConnector
from autodbaudit.infrastructure.sql.query_provider import (
    QueryProvider,
    get_query_provider,
)

__all__ = [
    "SqlConnector",
    "QueryProvider",
    "get_query_provider",
]
