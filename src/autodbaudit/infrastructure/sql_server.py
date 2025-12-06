"""
SQL Server connection and query execution module.

Handles:
- Connection string building
- ODBC driver detection and fallback
- SQL Server version detection
- Query execution and result parsing
- Connection pooling and error handling
"""

import logging
import pyodbc
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class SqlServerInfo:
    """SQL Server instance information."""
    server_name: str
    instance_name: str | None
    version: str
    version_major: int
    edition: str
    product_level: str
    is_clustered: bool


class SqlConnector:
    """
    SQL Server connection manager.
    
    Provides connection pooling, version detection, and query execution
    with support for SQL Server 2008 R2 through 2022+.
    """
    
    def __init__(self, server_instance: str, auth: str = "integrated",
                 username: str | None = None, password: str | None = None,
                 connect_timeout: int = 30):
        """
        Initialize SQL connector.
        
        Args:
            server_instance: Server instance string (e.g., "SERVER\\INSTANCE" or "SERVER,PORT")
            auth: Authentication mode ('integrated' or 'sql')
            username: SQL username (required if auth='sql')
            password: SQL password (required if auth='sql')
            connect_timeout: Connection timeout in seconds
        """
        self.server_instance = server_instance
        self.auth = auth.lower()
        self.username = username
        self.password = password
        self.connect_timeout = connect_timeout
        self._connection_string: str | None = None
        self._server_info: SqlServerInfo | None = None
        
        logger.info("SqlConnector initialized for %s (auth=%s)", server_instance, auth)
    
    def _detect_odbc_driver(self) -> str:
        """
        Detect best available ODBC driver.
        
        Returns:
            ODBC driver name
            
        Raises:
            RuntimeError: If no suitable driver found
        """
        drivers = pyodbc.drivers()
        logger.debug("Available ODBC drivers: %s", drivers)
        
        # Preferred drivers (newest first)
        preferred = [
            "ODBC Driver 18 for SQL Server",
            "ODBC Driver 17 for SQL Server",
            "ODBC Driver 13 for SQL Server",
            "ODBC Driver 11 for SQL Server"
        ]
        
        for driver in preferred:
            if driver in drivers:
                logger.info("Using ODBC driver: %s", driver)
                return driver
        
        # Fallback drivers
        fallback = [
            "SQL Server Native Client 11.0",
            "SQL Server Native Client 10.0",
            "SQL Server"
        ]
        
        for driver in fallback:
            if driver in drivers:
                logger.warning("Using fallback ODBC driver: %s", driver)
                return driver
        
        raise RuntimeError("No SQL Server ODBC driver found. Please install ODBC Driver 17 or 18.")
    
    def build_connection_string(self) -> str:
        """
        Build ODBC connection string.
        
        Returns:
            Connection string
        """
        if self._connection_string:
            return self._connection_string
        
        driver = self._detect_odbc_driver()
        
        parts = [
            f"DRIVER={{{driver}}}",
            f"SERVER={self.server_instance}",
            "DATABASE=master",
            f"TIMEOUT={self.connect_timeout}",
            "Encrypt=no",  # Disable encryption for compatibility
            "TrustServerCertificate=yes"
        ]
        
        if self.auth == "integrated":
            parts.append("Trusted_Connection=yes")
        else:
            if not self.username or not self.password:
                raise ValueError("Username and password required for SQL authentication")
            parts.append(f"UID={self.username}")
            parts.append(f"PWD={self.password}")
        
        self._connection_string = ";".join(parts)
        logger.debug("Connection string built (credentials masked)")
        return self._connection_string
    
    def test_connection(self) -> bool:
        """
        Test SQL Server connectivity.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            conn_str = self.build_connection_string()
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT @@VERSION")
                version = cursor.fetchone()[0]
                logger.info("Connection test successful: %s", self.server_instance)
                logger.debug("SQL Server version: %s...", version[:50])
                return True
        except Exception as e:
            logger.error("Connection test failed for %s: %s", self.server_instance, e)
            return False
    
    def detect_version(self) -> SqlServerInfo:
        """
        Detect SQL Server version and properties.
        
        Returns:
            SqlServerInfo object
            
        Raises:
            pyodbc.Error: If connection or query fails
        """
        if self._server_info:
            return self._server_info
        
        conn_str = self.build_connection_string()
        
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            
            # Get version information
            # Note: CAST IsClustered to INT to avoid ODBC type -16 error
            # Note: Use PARSENAME to extract major version for SQL 2008 compatibility
            #       (ProductMajorVersion was added in SQL 2012)
            cursor.execute("""
                SELECT 
                    CAST(SERVERPROPERTY('ServerName') AS NVARCHAR(256)) AS ServerName,
                    CAST(SERVERPROPERTY('InstanceName') AS NVARCHAR(256)) AS InstanceName,
                    CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128)) AS Version,
                    CAST(PARSENAME(CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128)), 4) AS INT) AS VersionMajor,
                    CAST(SERVERPROPERTY('Edition') AS NVARCHAR(256)) AS Edition,
                    CAST(SERVERPROPERTY('ProductLevel') AS NVARCHAR(128)) AS ProductLevel,
                    CAST(SERVERPROPERTY('IsClustered') AS INT) AS IsClustered
            """)
            
            row = cursor.fetchone()
            
            self._server_info = SqlServerInfo(
                server_name=row.ServerName or "",
                instance_name=row.InstanceName,
                version=row.Version or "",
                version_major=row.VersionMajor or 0,
                edition=row.Edition or "",
                product_level=row.ProductLevel or "",
                is_clustered=bool(row.IsClustered)
            )
            
            logger.info(
                "Detected SQL Server %s (%s)",
                self._server_info.version, self._server_info.edition
            )
            return self._server_info
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results as list of dictionaries.
        
        Args:
            query: SQL query string
            
        Returns:
            List of dictionaries (column name -> value)
            
        Raises:
            pyodbc.Error: If query execution fails
        """
        conn_str = self.build_connection_string()
        
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            
            # Get column names
            columns = [column[0] for column in cursor.description] if cursor.description else []
            
            # Fetch all rows
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            results = []
            for row in rows:
                row_dict = {}
                for i, column in enumerate(columns):
                    value = row[i]
                    # Handle special types
                    if value is None:
                        row_dict[column] = None
                    elif isinstance(value, (str, int, float, bool)):
                        row_dict[column] = value
                    else:
                        row_dict[column] = str(value)
                results.append(row_dict)
            
            logger.debug("Query returned %d rows, %d columns", len(results), len(columns))
            return results
    
    def execute_scalar(self, query: str) -> Any:
        """
        Execute query and return single scalar value.
        
        Args:
            query: SQL query string
            
        Returns:
            Single value from first row, first column
        """
        results = self.execute_query(query)
        if results and len(results) > 0:
            first_row = results[0]
            return list(first_row.values())[0] if first_row else None
        return None
