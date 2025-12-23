"""
Sensitive Roles Sheet Test Harness.

KEY_COLS: Server, Instance, Role, Member
Editable: Review Status, Justification, Last Reviewed
"""
from __future__ import annotations
import logging
from typing import Any
from tests.atomic_e2e.core.test_harness import AtomicE2ETestHarness, SyncCycleResult

logger = logging.getLogger(__name__)


class SensitiveRolesTestHarness(AtomicE2ETestHarness):
    SHEET_NAME = "Sensitive Roles"
    ENTITY_TYPE = "server_role_member"
    KEY_COLS = ["Server", "Instance", "Role", "Member"]
    EDITABLE_COLS = ["Review Status", "Justification", "Last Reviewed"]

    def _add_finding_to_writer(self, writer, finding: dict):
        writer.add_role_member(
            server_name=finding.get("server", "TestServer"),
            instance_name=finding.get("instance", ""),
            role_name=finding.get("role", "sysadmin"),
            member_name=finding.get("member", "test_user"),
            principal_type=finding.get("principal_type", "SQL_LOGIN"),
        )

    def create_mock_finding(
        self,
        server: str = "PROD-SQL01",
        instance: str = "",
        role: str = "sysadmin",
        member: str = "test_user",
        status: str = "FAIL",
        **kwargs,
    ) -> dict[str, Any]:
        key_parts = [server.lower(), instance.lower(), role.lower(), member.lower()]
        entity_key = "|".join(key_parts)
        return {
            "entity_key": entity_key,
            "server": server,
            "instance": instance,
            "role": role,
            "member": member,
            "status": status,
            **kwargs,
        }

    def create_findings_batch(self, count: int, status: str = "FAIL") -> list[dict]:
        return [self.create_mock_finding(member=f"user_{i+1:02d}", status=status) for i in range(count)]

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
