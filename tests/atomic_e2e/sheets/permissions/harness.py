"""
Permission Grants Sheet Test Harness.

KEY_COLS: Server, Instance, Scope, Database, Grantee, Permission, Entity Name
Editable: Review Status, Justification, Last Reviewed, Notes
"""
from __future__ import annotations
import logging
from typing import Any
from tests.atomic_e2e.core.test_harness import AtomicE2ETestHarness, SyncCycleResult

logger = logging.getLogger(__name__)


class PermissionsTestHarness(AtomicE2ETestHarness):
    SHEET_NAME = "Permission Grants"
    ENTITY_TYPE = "permission"
    KEY_COLS = ["Server", "Instance", "Scope", "Database", "Grantee", "Permission", "Entity Name"]
    EDITABLE_COLS = ["Review Status", "Justification", "Last Reviewed", "Notes"]

    def _add_finding_to_writer(self, writer, finding: dict):
        writer.add_permission(
            server_name=finding.get("server", "TestServer"),
            instance_name=finding.get("instance", ""),
            scope=finding.get("scope", "DATABASE"),
            database_name=finding.get("database", "TestDB"),
            grantee_name=finding.get("grantee", "test_user"),
            permission_name=finding.get("permission", "SELECT"),
            state=finding.get("state", "GRANT"),
            entity_name=finding.get("entity_name", "dbo.Users"),
            class_desc=finding.get("class_desc", "OBJECT"),
        )

    def create_mock_finding(
        self,
        server: str = "PROD-SQL01",
        instance: str = "",
        scope: str = "DATABASE",
        database: str = "TestDB",
        grantee: str = "test_user",
        permission: str = "SELECT",
        entity_name: str = "dbo.Users",
        status: str = "FAIL",
        **kwargs,
    ) -> dict[str, Any]:
        key_parts = [
            server.lower(), instance.lower(), scope.lower(),
            database.lower(), grantee.lower(), permission.lower(), entity_name.lower()
        ]
        entity_key = "|".join(key_parts)
        return {
            "entity_key": entity_key,
            "server": server,
            "instance": instance,
            "scope": scope,
            "database": database,
            "grantee": grantee,
            "permission": permission,
            "entity_name": entity_name,
            "status": status,
            **kwargs,
        }

    def create_findings_batch(self, count: int, status: str = "FAIL") -> list[dict]:
        perms = ["SELECT", "INSERT", "UPDATE", "DELETE", "EXECUTE"]
        return [self.create_mock_finding(permission=perms[i % len(perms)], status=status) for i in range(count)]

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
