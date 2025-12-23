"""
Services Sheet Test Harness.

KEY_COLS: Server, Instance, Service Name
Editable: Review Status, Justification, Last Reviewed
"""
from __future__ import annotations
import logging
from typing import Any
from tests.atomic_e2e.core.test_harness import AtomicE2ETestHarness, SyncCycleResult

logger = logging.getLogger(__name__)


class ServicesTestHarness(AtomicE2ETestHarness):
    SHEET_NAME = "Services"
    ENTITY_TYPE = "service"
    KEY_COLS = ["Server", "Instance", "Service Name"]
    EDITABLE_COLS = ["Review Status", "Justification", "Last Reviewed"]

    def _add_finding_to_writer(self, writer, finding: dict):
        writer.add_service(
            server_name=finding.get("server", "TestServer"),
            instance_name=finding.get("instance", ""),
            service_name=finding.get("service_name", "SQL Server"),
            service_type=finding.get("service_type", "Database Engine"),
            status=finding.get("svc_status", "Running"),
            startup_type=finding.get("startup_type", "Auto"),
            service_account=finding.get("service_account", "NT AUTHORITY\\SYSTEM"),
        )

    def create_mock_finding(
        self,
        server: str = "PROD-SQL01",
        instance: str = "",
        service_name: str = "SQL Server",
        status: str = "FAIL",
        **kwargs,
    ) -> dict[str, Any]:
        key_parts = [server.lower(), instance.lower(), service_name.lower()]
        entity_key = "|".join(key_parts)
        return {
            "entity_key": entity_key,
            "server": server,
            "instance": instance,
            "service_name": service_name,
            "status": status,
            **kwargs,
        }

    def create_findings_batch(self, count: int, status: str = "FAIL") -> list[dict]:
        svcs = ["SQL Server", "SQL Agent", "SSIS", "SSAS", "SSRS"]
        return [self.create_mock_finding(service_name=svcs[i % len(svcs)], status=status) for i in range(count)]

    def assert_action_logged(self, result: SyncCycleResult, action_type: str, count: int = 1, msg: str = "") -> list[dict]:
        matches = [a for a in result.actions_logged if action_type.lower() in a.get("action_type", "").lower()]
        if count == 0:
            assert len(matches) == 0, f"{msg or 'Expected NO'} {action_type}, found {len(matches)}"
        else:
            assert len(matches) >= count, f"{msg or 'Expected'} {count} {action_type}, got {len(matches)}"
        return matches

    def assert_no_action_logged(self, result: SyncCycleResult, action_type: str, msg: str = ""):
        self.assert_action_logged(result, action_type, count=0, msg=msg)
