"""
Database Users Sheet Test Harness.

KEY_COLS: Server, Instance, Database, User Name
Editable: Review Status, Justification, Last Reviewed, Notes
"""
from __future__ import annotations
import logging
from typing import Any
from tests.atomic_e2e.core.test_harness import AtomicE2ETestHarness, SyncCycleResult

logger = logging.getLogger(__name__)


class DatabaseUsersTestHarness(AtomicE2ETestHarness):
    SHEET_NAME = "Database Users"
    ENTITY_TYPE = "db_user"
    KEY_COLS = ["Server", "Instance", "Database", "User Name"]
    EDITABLE_COLS = ["Review Status", "Justification", "Last Reviewed", "Notes"]

    def _add_finding_to_writer(self, writer, finding: dict):
        writer.add_db_user(
            server_name=finding.get("server", "TestServer"),
            instance_name=finding.get("instance", ""),
            database_name=finding.get("database", "TestDB"),
            user_name=finding.get("user_name", "test_user"),
            user_type=finding.get("user_type", "SQL_USER"),
            mapped_login=finding.get("mapped_login"),
            is_orphaned=finding.get("is_orphaned", False),
            has_connect=finding.get("has_connect", True),
        )

    def create_mock_finding(
        self,
        server: str = "PROD-SQL01",
        instance: str = "",
        database: str = "TestDB",
        user_name: str = "test_user",
        status: str = "FAIL",
        **kwargs,
    ) -> dict[str, Any]:
        key_parts = [server.lower(), instance.lower(), database.lower(), user_name.lower()]
        entity_key = "|".join(key_parts)
        return {
            "entity_key": entity_key,
            "server": server,
            "instance": instance,
            "database": database,
            "user_name": user_name,
            "status": status,
            **kwargs,
        }

    def create_findings_batch(self, count: int, status: str = "FAIL") -> list[dict]:
        return [self.create_mock_finding(user_name=f"user_{i+1:02d}", status=status) for i in range(count)]

    def assert_action_logged(self, result: SyncCycleResult, action_type: str, count: int = 1, msg: str = "") -> list[dict]:
        matches = [a for a in result.actions_logged if action_type.lower() in a.get("action_type", "").lower()]
        if count == 0:
            assert len(matches) == 0, f"{msg or 'Expected NO'} {action_type}, found {len(matches)}"
        else:
            assert len(matches) >= count, f"{msg or 'Expected'} {count} {action_type}, got {len(matches)}"
        return matches

    def assert_no_action_logged(self, result: SyncCycleResult, action_type: str, msg: str = ""):
        self.assert_action_logged(result, action_type, count=0, msg=msg)
