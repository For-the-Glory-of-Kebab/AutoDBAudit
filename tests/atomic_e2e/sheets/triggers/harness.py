"""
Triggers Sheet Test Harness.

Extends the base harness with Triggers-specific configuration.
This validates that the test framework is truly extensible.

Triggers Key Differences from Linked Servers:
- Different KEY_COLS: Scope, Database, Trigger Name, Event
- Notes column instead of Purpose  
- SERVER vs DATABASE scope indicator
"""

from __future__ import annotations

import logging
from typing import Any

from tests.atomic_e2e.core.test_harness import AtomicE2ETestHarness, SyncCycleResult

logger = logging.getLogger(__name__)


class TriggersTestHarness(AtomicE2ETestHarness):
    """
    Test harness configured for Triggers sheet.
    
    Key columns for Triggers:
    - Server, Instance, Scope, Database, Trigger Name, Event
    """
    
    # =========================================================================
    # Sheet Configuration
    # =========================================================================
    
    SHEET_NAME = "Triggers"
    ENTITY_TYPE = "trigger"
    
    # Key columns that form the entity_key
    KEY_COLS = [
        "Server",
        "Instance",
        "Scope",        # SERVER or DATABASE
        "Database",     # Empty for SERVER scope
        "Trigger Name",
        "Event",
    ]
    
    # Editable columns (annotations)
    EDITABLE_COLS = [
        "Review Status",
        "Notes",        # This sheet uses Notes, not Purpose
        "Justification",
        "Last Reviewed",
    ]
    
    # =========================================================================
    # Writer Integration
    # =========================================================================

    def _add_finding_to_writer(self, writer, finding: dict):
        """Add a trigger finding using the real Excel writer."""
        writer.add_trigger(
            server_name=finding.get("server", "TestServer"),
            instance_name=finding.get("instance", ""),
            trigger_name=finding.get("trigger_name", "TestTrigger"),
            event_type=finding.get("event", "LOGON"),
            is_enabled=finding.get("is_enabled", True),
            level=finding.get("scope", "SERVER"),
            database_name=finding.get("database", None),
        )

    # =========================================================================
    # Mock Finding Helpers
    # =========================================================================

    def create_mock_finding(
        self,
        server: str = "PROD-SQL01",
        instance: str = "",
        scope: str = "SERVER",
        database: str = "",
        trigger_name: str = "AuditTrigger",
        event: str = "LOGON",
        status: str = "FAIL",
        **kwargs,
    ) -> dict[str, Any]:
        """Create a mock trigger finding."""
        key_parts = [
            server.lower(),
            instance.lower(),
            scope.lower(),
            database.lower(),
            trigger_name.lower(),
            event.lower(),
        ]
        entity_key = "|".join(key_parts)
        
        finding = {
            "entity_key": entity_key,
            "server": server,
            "instance": instance,
            "scope": scope,
            "database": database,
            "trigger_name": trigger_name,
            "event": event,
            "is_enabled": kwargs.get("is_enabled", True),
            "status": status,
        }
        finding.update(kwargs)
        return finding

    def create_findings_batch(
        self,
        count: int,
        status: str = "FAIL",
        server_prefix: str = "SQL",
        scope: str = "SERVER",
    ) -> list[dict[str, Any]]:
        """Create multiple mock findings for bulk testing."""
        findings = []
        for i in range(count):
            findings.append(self.create_mock_finding(
                server=f"{server_prefix}-{i+1:02d}",
                trigger_name=f"Trigger_{i+1:02d}",
                scope=scope,
                status=status,
            ))
        return findings

    # =========================================================================
    # Assertion Helpers (copied from LinkedServersTestHarness)
    # =========================================================================

    def assert_action_logged(
        self,
        result: SyncCycleResult,
        action_type: str,
        count: int = 1,
        msg: str = "",
    ) -> list[dict]:
        """Assert that specific action type was logged."""
        all_actions = result.actions_logged
        matches = [
            a for a in all_actions
            if action_type.lower() in a.get("action_type", "").lower()
        ]
        
        if count == 0:
            assert len(matches) == 0, \
                f"{msg or 'Expected NO'} {action_type} action, but found {len(matches)}"
        else:
            assert len(matches) >= count, \
                f"{msg or 'Expected'} {count} {action_type} action(s), got {len(matches)}. " \
                f"All actions: {[a.get('action_type') for a in all_actions]}"
        
        return matches

    def assert_no_action_logged(self, result: SyncCycleResult, action_type: str, msg: str = ""):
        """Assert that action type was NOT logged."""
        self.assert_action_logged(result, action_type, count=0, msg=msg)

    def assert_annotation_in_db(
        self,
        entity_key: str,
        field: str,
        expected_value: str | None = None,
        contains: str | None = None,
    ) -> dict:
        """Assert annotation exists in database."""
        annotation = self.get_db_annotation(entity_key)
        assert annotation is not None, f"Annotation not found for {entity_key}"
        
        actual = annotation.get(field, "")
        
        if expected_value is not None:
            assert actual == expected_value, \
                f"Expected {field}={expected_value!r}, got {actual!r}"
        
        if contains is not None:
            assert contains.lower() in str(actual).lower(), \
                f"Expected {field} to contain {contains!r}, got {actual!r}"
        
        return annotation

    def assert_exception_detected(self, entity_key: str, should_exist: bool = True):
        """Assert exception status for finding."""
        annotation = self.get_db_annotation(entity_key)
        
        if should_exist:
            assert annotation is not None, \
                f"Expected exception for {entity_key}, but no annotation found"
            has_just = bool(annotation.get("justification", "").strip())
            has_status = "exception" in str(annotation.get("review_status", "")).lower()
            assert has_just or has_status, \
                f"Expected exception for {entity_key}: {annotation}"
        else:
            if annotation:
                has_just = bool(annotation.get("justification", "").strip())
                has_status = "exception" in str(annotation.get("review_status", "")).lower()
                assert not (has_just or has_status), \
                    f"Expected NO exception for {entity_key}, but found: {annotation}"

    def transition_finding_status(
        self,
        from_status: str,
        to_status: str,
        finding: dict | None = None,
    ) -> dict:
        """Helper to transition a finding between statuses."""
        if finding is None:
            finding = self.create_mock_finding(status=from_status)
        
        new_finding = finding.copy()
        new_finding["status"] = to_status
        return new_finding
