"""
Server Logins Sheet Test Harness.

KEY_COLS: Server, Instance, Login Name
Editable: Review Status, Justification, Last Reviewed, Notes
"""
from __future__ import annotations
import logging
from typing import Any
from tests.atomic_e2e.core.test_harness import AtomicE2ETestHarness, SyncCycleResult

logger = logging.getLogger(__name__)


class ServerLoginsTestHarness(AtomicE2ETestHarness):
    SHEET_NAME = "Server Logins"
    ENTITY_TYPE = "login"
    KEY_COLS = ["Server", "Instance", "Login Name"]
    EDITABLE_COLS = ["Review Status", "Justification", "Last Reviewed", "Notes"]

    def _add_finding_to_writer(self, writer, finding: dict):
        writer.add_login(
            server_name=finding.get("server", "TestServer"),
            instance_name=finding.get("instance", ""),
            login_name=finding.get("login_name", "TestLogin"),
            login_type=finding.get("login_type", "SQL_LOGIN"),
            is_disabled=finding.get("is_disabled", False),
            default_db=finding.get("default_db", "master"),
            password_policy=finding.get("password_policy", True),
            password_expiry=finding.get("password_expiry", True),
        )

    def create_mock_finding(
        self,
        server: str = "PROD-SQL01",
        instance: str = "",
        login_name: str = "test_login",
        status: str = "FAIL",
        **kwargs,
    ) -> dict[str, Any]:
        key_parts = [server.lower(), instance.lower(), login_name.lower()]
        entity_key = "|".join(key_parts)
        return {
            "entity_key": entity_key,
            "server": server,
            "instance": instance,
            "login_name": login_name,
            "status": status,
            "login_type": kwargs.get("login_type", "SQL_LOGIN"),
            "is_disabled": kwargs.get("is_disabled", False),
            **kwargs,
        }

    def create_findings_batch(self, count: int, status: str = "FAIL") -> list[dict]:
        return [self.create_mock_finding(login_name=f"login_{i+1:02d}", status=status) for i in range(count)]

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
