"""
Infrastructure layer package.

Contains all I/O and external system integrations:
- SQL Server connectivity (pyodbc)
- Configuration file loading
- Logging setup
- ODBC driver detection
- Query file loading
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
    # Logging
    "setup_logging",
    # ODBC
    "check_odbc_drivers",
]
