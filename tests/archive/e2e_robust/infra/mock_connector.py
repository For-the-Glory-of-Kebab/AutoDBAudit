"""
Mock SQL Connector.
Intercepts fetch_all and delegates to MockDataFactory.
"""

from typing import Any, List, Optional
from .mock_data_factory import MockDataFactory


class MockSqlConnector:
    """Mock replacement for autodbaudit.infrastructure.sql.connector.SqlConnector."""

    # Static state to control which cycle we are in
    CURRENT_STATE = "BASELINE"

    def __init__(self, *args, **kwargs):
        pass

    def connect(self):
        pass

    def test_connection(self) -> bool:
        return True

    def detect_version(self):
        """Return a dummy version info object."""

        class VersionInfo:
            version = "15.0.2000"
            edition = "Developer"
            version_major = 15
            product_level = "RTM"
            instance_name = "TEST-INSTANCE"

        return VersionInfo()

    def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[Any]:
        """
        Delegate to MockDataFactory based on CURRENT_STATE.
        Return list of sqlite3.Row-like objects (dictionaries okay? No, usually tuples or Row objects).
        The real connector returns lists of tuples/Rows.
        """
        rows = MockDataFactory.get_rows_for_query(query, self.CURRENT_STATE)

        # We need to ensure the consuming code (Collectors) can handle regular tuples.
        # Most collectors use row['column'] (dict access) or row.column.
        # The real SqlConnector uses pyodbc Rows which support both.
        # We should wrap them in a simple dict-like class if needed, or just tuples if the code uses index.

        # Looking at AccessControlCollector:
        # row.name, row.type_desc ... property access.

        class MockRow:
            def __init__(self, data, columns):
                self._data = data
                self._columns = columns
                for i, col in enumerate(columns):
                    setattr(self, col, data[i])

            def __getitem__(self, key):
                if isinstance(key, int):
                    return self._data[key]
                return getattr(self, key)

        # We need to map queries to expected columns for this to work perfectly.
        # This is the tricky part. For "God Tier" robustness, we define columns in factory.

        # REFACTOR FACTORY TO RETURN COLUMNS TOO
        rows_and_cols = self._get_rows_with_columns(query, self.CURRENT_STATE)

        return [MockRow(r, cols) for r, cols in rows_and_cols]

    def _get_rows_with_columns(self, query: str, state: str):
        query_upper = query.upper()

        if "SERVERPROPERTY" in query_upper:
            cols = [
                "ServerName",
                "InstanceName",
                "ProductVersion",
                "Edition",
                "OS",
                "MajorVersion",
                "Build",
            ]
            rows = MockDataFactory.get_rows_for_query(query, state)
            return [(r, cols) for r in rows]

        if "FROM SYS.SERVER_PRINCIPALS" in query_upper:
            cols = [
                "LoginName",
                "LoginType",
                "IsDisabled",
                "CreateDate",
                "ModifyDate",
                "DefaultDatabase",
                "PasswordPolicyEnforced",
                "IsExpirationChecked",
                "IsSA",
            ]
            rows = MockDataFactory.get_rows_for_query(query, state)
            return [(r, cols) for r in rows]

        if "FROM SYS.SERVER_ROLE_MEMBERS" in query_upper:
            cols = ["RoleName", "MemberName", "MemberType", "MemberDisabled"]
            rows = MockDataFactory.get_rows_for_query(query, state)
            return [(r, cols) for r in rows]

        return []

    def execute_query(self, query: str) -> List[Any]:
        """
        Mock execute_query to return list of dictionaries.
        Matches SqlConnector.execute_query signature and return type.
        """
        # Get raw data and column names from factory
        rows_and_cols = self._get_rows_with_columns(query, self.CURRENT_STATE)

        results = []
        for row_data, columns in rows_and_cols:
            row_dict = {}
            for i, col in enumerate(columns):
                row_dict[col] = row_data[i]
            results.append(row_dict)

        return results

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
