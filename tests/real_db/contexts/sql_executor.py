"""
SQLExecutor - Execute SQL scripts on test instances.

Uses config/sql_targets.json to find instances.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import pyodbc


class SQLExecutor:
    """
    Executes SQL scripts on configured instances.

    Follows the pattern from simulate-discrepancies/run_simulation.py
    but simplified for test fixtures.
    """

    def __init__(self, config_dir: Path) -> None:
        self.config_dir = config_dir
        self._connection: pyodbc.Connection | None = None

    def get_connection_string(self) -> str:
        """Build connection string from first enabled target."""
        # Import config loader
        import sys

        project_root = self.config_dir.parent
        sys.path.insert(0, str(project_root / "src"))

        from autodbaudit.infrastructure.config_loader import ConfigLoader

        loader = ConfigLoader(config_dir=str(self.config_dir))
        targets = loader.load_sql_targets()

        if not targets:
            raise RuntimeError("No SQL targets configured")

        # Get first enabled target
        target = next((t for t in targets if t.enabled), None)
        if not target:
            raise RuntimeError("No enabled SQL targets")

        # Find ODBC driver
        drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
        if not drivers:
            raise RuntimeError("No SQL Server ODBC driver found")

        driver = drivers[0]
        for d in drivers:
            if "ODBC Driver 17" in d or "ODBC Driver 18" in d:
                driver = d
                break

        # Build connection string
        try:
            server_str = target.server_instance
        except AttributeError:
            if target.port:
                server_str = f"{target.server},{target.port}"
            else:
                server_str = target.server

        conn_str = f"DRIVER={{{driver}}};SERVER={server_str};"

        if target.auth == "sql" and target.username:
            conn_str += f"UID={target.username};PWD={target.password};"
        else:
            conn_str += "Trusted_Connection=yes;"

        conn_str += "TrustServerCertificate=yes;"
        return conn_str

    def connect(self) -> pyodbc.Connection:
        """Get connection (cached)."""
        if self._connection is None:
            conn_str = self.get_connection_string()
            self._connection = pyodbc.connect(conn_str, autocommit=True)
        return self._connection

    def execute_file(self, sql_path: Path) -> bool:
        """
        Execute SQL file.

        Splits by GO and executes each batch.

        Returns:
            True if all batches succeeded
        """
        if not sql_path.exists():
            return False

        sql_content = sql_path.read_text(encoding="utf-8")
        return self.execute_script(sql_content)

    def execute_script(self, sql_content: str) -> bool:
        """
        Execute SQL script content.

        Splits by GO and executes each batch.
        """
        conn = self.connect()
        cursor = conn.cursor()

        # Split by GO
        batches = re.split(r"(?i)^\s*GO\b.*$", sql_content, flags=re.MULTILINE)

        all_success = True

        for batch in batches:
            clean_batch = batch.strip()
            if not clean_batch:
                continue

            try:
                cursor.execute(clean_batch)
                while cursor.nextset():
                    pass
            except pyodbc.Error as e:
                print(f"SQL Error: {e}")
                all_success = False

        return all_success

    def execute_statement(self, statement: str) -> bool:
        """Execute single SQL statement."""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(statement)
            return True
        except pyodbc.Error as e:
            print(f"SQL Error: {e}")
            return False

    def close(self) -> None:
        """Close connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
