"""
Infrastructure layer package.

Contains all I/O and external system integrations:
- SQL Server connectivity (sql/)
- Configuration file loading
- Logging setup
- ODBC driver detection
- SQLite history store (sqlite/)
- Excel report generation (excel/)
- Version-specific query providers
"""

from autodbaudit.infrastructure.config_loader import (
    ConfigLoader,
    SqlTarget,
    AuditConfig,
)
from autodbaudit.infrastructure.sql import (
    SqlConnector,
    QueryProvider,
    get_query_provider,
)
from autodbaudit.infrastructure.sql.connector import SqlServerInfo
from autodbaudit.infrastructure.logging_config import setup_logging
from autodbaudit.infrastructure.odbc_check import check_odbc_drivers
from autodbaudit.infrastructure.sqlite import HistoryStore

__all__ = [
    # Config
    "ConfigLoader",
    "SqlTarget",
    "AuditConfig",
    # SQL Server
    "SqlConnector",
    "SqlServerInfo",
    # Queries
    "QueryProvider",
    "get_query_provider",
    # Logging
    "setup_logging",
    # ODBC
    "check_odbc_drivers",
    # History
    "HistoryStore",
]
