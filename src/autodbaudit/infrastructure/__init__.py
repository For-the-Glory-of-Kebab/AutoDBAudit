"""
Infrastructure layer package.

Contains all I/O and external system integrations:
- SQL Server connectivity (pyodbc)
- Configuration file loading
- Logging setup
- ODBC driver detection
- Query file loading
- SQLite history store
- Excel report generation
- Version-specific query providers
"""

from autodbaudit.infrastructure.config_loader import (
    ConfigLoader,
    SqlTarget,
    AuditConfig,
)
from autodbaudit.infrastructure.sql_server import (
    SqlConnector,
    SqlServerInfo,
)
from autodbaudit.infrastructure.sql_queries import load_queries_for_version
from autodbaudit.infrastructure.logging_config import setup_logging
from autodbaudit.infrastructure.odbc_check import check_odbc_drivers
from autodbaudit.infrastructure.history_store import HistoryStore
from autodbaudit.infrastructure.excel_report import write_instance_inventory
from autodbaudit.infrastructure.query_provider import (
    QueryProvider,
    Sql2008Provider,
    Sql2019PlusProvider,
    get_query_provider,
)

__all__ = [
    # Config
    "ConfigLoader",
    "SqlTarget",
    "AuditConfig",
    # SQL Server
    "SqlConnector",
    "SqlServerInfo",
    # Queries
    "load_queries_for_version",
    "QueryProvider",
    "Sql2008Provider",
    "Sql2019PlusProvider",
    "get_query_provider",
    # Logging
    "setup_logging",
    # ODBC
    "check_odbc_drivers",
    # History
    "HistoryStore",
    # Excel
    "write_instance_inventory",
]
