"""
Databases Sheet Test Harness.

KEY_COLS: Server, Instance, Database
Editable: Review Status, Justification, Last Reviewed, Notes
"""
from __future__ import annotations
import logging
from typing import Any
from tests.atomic_e2e.core.test_harness import AtomicE2ETestHarness, SyncCycleResult

logger = logging.getLogger(__name__)


class DatabasesTestHarness(AtomicE2ETestHarness):
    SHEET_NAME = "Databases"
    ENTITY_TYPE = "database"
    KEY_COLS = ["Server", "Instance", "Database"]
    EDITABLE_COLS = ["Review Status", "Justification", "Last Reviewed", "Notes"]

    def _add_finding_to_writer(self, writer, finding: dict):
        writer.add_database(
            server_name=finding.get("server", "TestServer"),
            instance_name=finding.get("instance", ""),
            database_name=finding.get("database", "TestDB"),
            owner=finding.get("owner", "sa"),
            recovery_model=finding.get("recovery_model", "FULL"),
            state=finding.get("state", "ONLINE"),
            data_size_mb=finding.get("size_mb", 100),
            is_trustworthy=finding.get("is_trustworthy", True),
        )

    def create_mock_finding(
        self,
        server: str = "PROD-SQL01",
        instance: str = "",
        database: str = "TestDB",
        status: str = "FAIL",
        **kwargs,
    ) -> dict[str, Any]:
        key_parts = [server.lower(), instance.lower(), database.lower()]
        entity_key = "|".join(key_parts)
        return {
            "entity_key": entity_key,
            "server": server,
            "instance": instance,
            "database": database,
            "status": status,
            "is_trustworthy": kwargs.get("is_trustworthy", status == "FAIL"),
            **kwargs,
        }

    def create_findings_batch(self, count: int, status: str = "FAIL") -> list[dict]:
        return [self.create_mock_finding(database=f"DB_{i+1:02d}", status=status) for i in range(count)]

    def assert_action_logged(self, result: SyncCycleResult, action_type: str, count: int = 1, msg: str = "") -> list[dict]:
        matches = [a for a in result.actions_logged if action_type.lower() in a.get("action_type", "").lower()]
        if count == 0:
            assert len(matches) == 0, f"{msg or 'Expected NO'} {action_type}, found {len(matches)}"
        else:
            assert len(matches) >= count, f"{msg or 'Expected'} {count} {action_type}, got {len(matches)}"
        return matches

    def assert_no_action_logged(self, result: SyncCycleResult, action_type: str, msg: str = ""):
        self.assert_action_logged(result, action_type, count=0, msg=msg)

    def assert_annotation_in_db(self, entity_key: str, field: str, contains: str = None) -> dict:
        annotation = self.get_db_annotation(entity_key)
        assert annotation is not None, f"Annotation not found for {entity_key}"
        if contains:
            assert contains.lower() in str(annotation.get(field, "")).lower()
        return annotation
