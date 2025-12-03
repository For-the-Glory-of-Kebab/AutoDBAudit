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
        
        logger.info(f"SqlConnector initialized for {server_instance} (auth={auth})")
    
    def _detect_odbc_driver(self) -> str:
        """
        Detect best available ODBC driver.
        
        Returns:
            ODBC driver name
            
        Raises:
            RuntimeError: If no suitable driver found
        """
        drivers = pyodbc.drivers()
        logger.debug(f"Available ODBC drivers: {drivers}")
        
        # Preferred drivers (newest first)
        preferred = [
            "ODBC Driver 18 for SQL Server",
            "ODBC Driver 17 for SQL Server",
            "ODBC Driver 13 for SQL Server",
            "ODBC Driver 11 for SQL Server"
        ]
        
        for driver in preferred:
            if driver in drivers:
                logger.info(f"Using ODBC driver: {driver}")
                return driver
        
        # Fallback drivers
        fallback = [
            "SQL Server Native Client 11.0",
            "SQL Server Native Client 10.0",
            "SQL Server"
        ]
        
        for driver in fallback:
            if driver in drivers:
                logger.warning(f"Using fallback ODBC driver: {driver}")
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
                logger.info(f"Connection test successful: {self.server_instance}")
                logger.debug(f"SQL Server version: {version[:50]}...")
                return True
        except Exception as e:
            logger.error(f"Connection test failed for {self.server_instance}: {e}")
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
            cursor.execute("""
                SELECT 
                    SERVERPROPERTY('ServerName') AS ServerName,
                    SERVERPROPERTY('InstanceName') AS InstanceName,
                    SERVERPROPERTY('ProductVersion') AS Version,
                    SERVERPROPERTY('ProductMajorVersion') AS VersionMajor,
                    SERVERPROPERTY('Edition') AS Edition,
                    SERVERPROPERTY('ProductLevel') AS ProductLevel,
                    SERVERPROPERTY('IsClustered') AS IsClustered
            """)
            
            row = cursor.fetchone()
            
            self._server_info = SqlServerInfo(
                server_name=row.ServerName,
                instance_name=row.InstanceName,
                version=row.Version,
                version_major=int(row.VersionMajor) if row.VersionMajor else 0,
                edition=row.Edition,
                product_level=row.ProductLevel,
                is_clustered=bool(row.IsClustered)
            )
            
            logger.info(f"Detected SQL Server {self._server_info.version} "
                       f"({self._server_info.edition})")
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
            
            logger.debug(f"Query returned {len(results)} rows, {len(columns)} columns")
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
