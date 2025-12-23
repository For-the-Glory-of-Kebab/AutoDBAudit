"""
Backups Sheet Test Harness.

Backups KEY_COLS: Server, Instance, Database, Recovery Model
Editable: Review Status, Justification, Last Reviewed, Notes
"""

from __future__ import annotations

import logging
from typing import Any

from tests.atomic_e2e.core.test_harness import AtomicE2ETestHarness, SyncCycleResult

logger = logging.getLogger(__name__)


class BackupsTestHarness(AtomicE2ETestHarness):
    SHEET_NAME = "Backups"
    ENTITY_TYPE = "backup"
    KEY_COLS = ["Server", "Instance", "Database", "Recovery"]
    EDITABLE_COLS = ["Review Status", "Justification", "Last Reviewed", "Notes"]

    def _add_finding_to_writer(self, writer, finding: dict):
        writer.add_backup_info(
            server_name=finding.get("server", "TestServer"),
            instance_name=finding.get("instance", ""),
            database_name=finding.get("database", "TestDB"),
            recovery_model=finding.get("recovery", "FULL"),
            last_backup_date=finding.get("last_backup"),
            days_since=finding.get("days_since", 0),
            backup_size_mb=finding.get("size_mb", 100),
            backup_path=finding.get("path", "C:\\Backup"),
        )

    def create_mock_finding(
        self,
        server: str = "PROD-SQL01",
        instance: str = "",
        database: str = "AdventureWorks",
        recovery: str = "FULL",
        status: str = "FAIL",
        **kwargs,
    ) -> dict[str, Any]:
        key_parts = [server.lower(), instance.lower(), database.lower(), recovery.lower()]
        entity_key = "|".join(key_parts)
        
        finding = {
            "entity_key": entity_key,
            "server": server,
            "instance": instance,
            "database": database,
            "recovery": recovery,
            "status": status,
            "days_since": kwargs.get("days_since", 8 if status == "FAIL" else 1),
            "size_mb": kwargs.get("size_mb", 100),
            "path": kwargs.get("path", "C:\\Backup"),
        }
        finding.update(kwargs)
        return finding

    def create_findings_batch(self, count: int, status: str = "FAIL") -> list[dict]:
        return [
            self.create_mock_finding(database=f"DB_{i+1:02d}", status=status)
            for i in range(count)
        ]

    # Assertion helpers
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
