"""
Configuration Sheet Test Harness.

KEY_COLS: Server, Instance, Setting
Editable: Review Status, Exception Reason (justification), Last Reviewed
"""
from __future__ import annotations
import logging
from typing import Any
from tests.atomic_e2e.core.test_harness import AtomicE2ETestHarness, SyncCycleResult

logger = logging.getLogger(__name__)


class ConfigurationTestHarness(AtomicE2ETestHarness):
    SHEET_NAME = "Configuration"
    ENTITY_TYPE = "config"
    KEY_COLS = ["Server", "Instance", "Setting"]
    EDITABLE_COLS = ["Review Status", "Exception Reason", "Last Reviewed"]

    def _add_finding_to_writer(self, writer, finding: dict):
        writer.add_config_setting(
            server_name=finding.get("server", "TestServer"),
            instance_name=finding.get("instance", ""),
            setting_name=finding.get("setting", "xp_cmdshell"),
            current_value=finding.get("current_value", "1"),
            recommended_value=finding.get("recommended_value", "0"),
            status=finding.get("status", "FAIL"),
        )

    def create_mock_finding(
        self,
        server: str = "PROD-SQL01",
        instance: str = "",
        setting: str = "xp_cmdshell",
        status: str = "FAIL",
        **kwargs,
    ) -> dict[str, Any]:
        key_parts = [server.lower(), instance.lower(), setting.lower()]
        entity_key = "|".join(key_parts)
        return {
            "entity_key": entity_key,
            "server": server,
            "instance": instance,
            "setting": setting,
            "status": status,
            "current_value": kwargs.get("current_value", "1"),
            "recommended_value": kwargs.get("recommended_value", "0"),
            **kwargs,
        }

    def create_findings_batch(self, count: int, status: str = "FAIL") -> list[dict]:
        settings = ["xp_cmdshell", "clr_enabled", "ole_automation", "remote_admin_connections", "cross_db_ownership"]
        return [self.create_mock_finding(setting=settings[i % len(settings)], status=status) for i in range(count)]

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
