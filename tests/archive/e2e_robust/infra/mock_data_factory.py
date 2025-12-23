"""
Mock Data Factory for E2E Tests.
Generates 'findings' dictionaries mimicking the AuditDataCollector output.
"""

from typing import Any
from tests.e2e_robust import config, scenarios


class MockDataFactory:
    @staticmethod
    def get_data_for_state(state_name: str) -> dict[str, Any]:
        """
        Returns the data dictionary expected by AuditService._process_target
        But we probably need to mock at a lower level: SqlConnector.fetch_all
        Or better: mock AuditDataCollector.collect_all to return findings directly.

        Let's assume we mock AuditDataCollector.collect_all.
        """

        # Base Data
        data = {
            "instances": 1,
            "logins": 0,
            "roles": 0,
            "databases": 0,
            "services": 0,
            # We add raw findings here? No, collect_all saves to DB directly using collector.
            # This is tricky without SqlConnector mock.
            # We will use this factory to serve rows to the MockConnector.
        }

        return {}

    @staticmethod
    def get_rows_for_query(query: str, state_name: str) -> list[tuple]:
        """
        Returns list of rows (tuples) for a given SQL query based on state.
        This is what SqlConnector.fetch_all will return.
        """
        query_upper = query.upper()

        # 1. Properties
        if "SERVERPROPERTY" in query_upper:
            return [
                (
                    config.SERVER_NAME,
                    config.INSTANCE_NAME,
                    "15.0.2000",
                    "Developer",
                    "Windows 10",
                    "15.0",
                    "1234",
                )
            ]

        # 2. Logins
        if "FROM SYS.SERVER_PRINCIPALS" in query_upper:
            # We need to match the columns expected by AccessControlCollector
            # LoginName, LoginType, IsDisabled, CreateDate, ModifyDate,
            # DefaultDatabase, PasswordPolicyEnforced, IsExpirationChecked, IsSA (9 cols)

            # FAIL USER
            fail_user = (
                scenarios.ENTITY_FAIL,
                "SQL_LOGIN",
                1,  # 1 = Disabled (Triggers FAIL logic in AccessControlCollector)
                "2023-01-01",
                "2023-01-01",
                "master",
                0,  # Policy Passed? 0=False -> FAIL
                0,
                0,  # IsSA
            )

            # PASS USER
            pass_user = (
                scenarios.ENTITY_PASS,
                "WINDOWS_LOGIN",  # Windows Login = No WARN for enabled
                0,
                "2023-01-01",
                "2023-01-01",
                "master",
                1,  # Policy Checked? 1=True -> PASS
                1,
                0,  # IsSA
            )

            if state_name == "FIXED":
                # Make FAIL user PASS
                fail_user = (
                    scenarios.ENTITY_FAIL,
                    "SQL_LOGIN",
                    1,
                    "2023-01-01",
                    "2023-01-01",
                    "master",
                    1,  # Policy Checked -> PASS
                    1,
                    0,
                )

            return [fail_user, pass_user]

        # 3. Roles / Members
        if "FROM SYS.SERVER_ROLE_MEMBERS" in query_upper:
            # role, member, member_type, is_disabled

            # SENSITIVE ROLE MEMBER
            role_row = ("sysadmin", scenarios.ENTITY_ROLE, "SQL_LOGIN", 0)  # Enabled

            return [role_row]

        # Default empty
        return []
