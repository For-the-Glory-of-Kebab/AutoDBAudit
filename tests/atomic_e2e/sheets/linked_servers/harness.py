"""
Linked Servers Test Harness.

Reusable test harness for Linked Servers sheet E2E testing.
Extends the base AtomicE2ETestHarness with sheet-specific configuration.

To adapt for other sheets:
1. Copy this file
2. Update SHEET_NAME, ENTITY_TYPE, KEY_COLS, EDITABLE_COLS
3. Implement _add_finding_to_writer() for your sheet's writer method
"""

from __future__ import annotations

import logging
from typing import Any

from tests.atomic_e2e.core.test_harness import AtomicE2ETestHarness

logger = logging.getLogger(__name__)


class LinkedServersTestHarness(AtomicE2ETestHarness):
    """
    Test harness configured for Linked Servers sheet.
    
    Provides:
    - Sheet-specific configuration (columns, entity type)
    - Mock finding creation helpers
    - Common assertion helpers
    """
    
    # =========================================================================
    # Sheet Configuration - UPDATE THESE FOR OTHER SHEETS
    # =========================================================================
    
    SHEET_NAME = "Linked Servers"
    ENTITY_TYPE = "linked_server"
    
    # Key columns that form the entity_key (must match SHEET_ANNOTATION_CONFIG)
    KEY_COLS = [
        "Server",
        "Instance",
        "Linked Server",
        "Local Login",
        "Remote Login",
    ]
    
    # Editable columns (annotations we can read/write)
    EDITABLE_COLS = [
        "Review Status",
        "Purpose",  # Notes field for this sheet
        "Justification",
        "Last Reviewed",
    ]
    
    # =========================================================================
    # Writer Integration - UPDATE FOR OTHER SHEETS
    # =========================================================================
    
    def _add_finding_to_writer(self, writer, finding: dict):
        """
        Add a linked server finding using the real Excel writer.
        
        Args:
            writer: EnhancedReportWriter instance
            finding: Dict with finding data
        """
        writer.add_linked_server(
            server_name=finding.get("server", "TestServer"),
            instance_name=finding.get("instance", ""),
            linked_server_name=finding.get("linked_server", "LinkedSrv1"),
            product="",  # Not used in current implementation
            provider=finding.get("provider", "SQLOLEDB"),
            data_source=finding.get("data_source", "remote_server"),
            rpc_out=finding.get("rpc_out", True),
            local_login=finding.get("local_login", ""),
            remote_login=finding.get("remote_login", ""),
            impersonate=finding.get("impersonate", False),
            risk_level=finding.get("risk_level", ""),
        )

    # =========================================================================
    # Mock Finding Helpers - REUSABLE PATTERNS
    # =========================================================================

    def create_mock_finding(
        self,
        server: str = "PROD-SQL01",
        instance: str = "",
        linked_server: str = "LINKED_SRV_01",
        local_login: str = "sa",
        remote_login: str = "remote_user",
        status: str = "FAIL",
        **kwargs,
    ) -> dict[str, Any]:
        """
        Create a mock finding with proper entity_key format.
        
        The entity_key MUST match what the annotation reader builds from Excel columns.
        Format: server|instance|linked_server|local_login|remote_login (all lowercase)
        
        Args:
            server: Server hostname
            instance: SQL instance (empty string for default)
            linked_server: Linked server name
            local_login: Local login for mapping
            remote_login: Remote login for mapping
            status: FAIL, WARN, or PASS
            **kwargs: Additional finding fields
            
        Returns:
            Dict with all finding fields including computed entity_key
        """
        # Build entity_key matching annotation reader format
        key_parts = [
            server.lower(),
            instance.lower(),  
            linked_server.lower(),
            local_login.lower(),
            remote_login.lower(),
        ]
        entity_key = "|".join(key_parts)
        
        finding = {
            "entity_key": entity_key,
            "server": server,
            "instance": instance,
            "linked_server": linked_server,
            "local_login": local_login,
            "remote_login": remote_login,
            "status": status,
            "provider": kwargs.get("provider", "SQLOLEDB"),
            "data_source": kwargs.get("data_source", "remote_server"),
            "rpc_out": kwargs.get("rpc_out", True),
            "impersonate": kwargs.get("impersonate", False),
            "risk_level": "HIGH_PRIVILEGE" if status == "FAIL" else "",
        }
        finding.update(kwargs)
        return finding

    def create_findings_batch(
        self,
        count: int,
        status: str = "FAIL",
        server_prefix: str = "SQL",
    ) -> list[dict[str, Any]]:
        """
        Create multiple mock findings for bulk testing.
        
        Args:
            count: Number of findings to create
            status: Status for all findings
            server_prefix: Prefix for server names
            
        Returns:
            List of mock findings
        """
        findings = []
        for i in range(count):
            findings.append(self.create_mock_finding(
                server=f"{server_prefix}-{i+1:02d}",
                linked_server=f"LINK_{i+1:02d}",
                status=status,
            ))
        return findings

    # =========================================================================
    # Assertion Helpers - REUSABLE ACROSS ALL TESTS
    # =========================================================================

    def assert_action_logged(
        self,
        result,
        action_type: str,
        count: int = 1,
        msg: str = "",
    ) -> list[dict]:
        """
        Assert that specific action type was logged.
        
        Args:
            result: SyncCycleResult from run_sync_cycle()
            action_type: Type to search for (partial match, case-insensitive)
            count: Expected count (use 0 to assert NOT logged)
            msg: Optional assertion message
            
        Returns:
            List of matching actions
        """
        all_actions = result.actions_logged
        matches = [
            a for a in all_actions
            if action_type.lower() in a.get("action_type", "").lower()
        ]
        
        if count == 0:
            assert len(matches) == 0, \
                f"{msg or 'Expected NO'} {action_type} action, but found {len(matches)}: {matches}"
        else:
            assert len(matches) >= count, \
                f"{msg or 'Expected'} {count} {action_type} action(s), got {len(matches)}. " \
                f"All actions: {[a.get('action_type') for a in all_actions]}"
        
        return matches

    def assert_no_action_logged(
        self,
        result,
        action_type: str,
        msg: str = "",
    ):
        """Assert that action type was NOT logged."""
        self.assert_action_logged(result, action_type, count=0, msg=msg)

    def assert_annotation_in_db(
        self,
        entity_key: str,
        field: str,
        expected_value: str | None = None,
        contains: str | None = None,
    ) -> dict:
        """
        Assert annotation exists in database.
        
        Args:
            entity_key: Finding's entity_key (without type prefix)
            field: Annotation field to check
            expected_value: Exact value to match (optional)
            contains: Substring to check (optional)
            
        Returns:
            The annotation dict
        """
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

    def assert_exception_detected(
        self,
        entity_key: str,
        should_exist: bool = True,
    ):
        """
        Assert exception status for finding.
        
        Args:
            entity_key: Finding's entity_key
            should_exist: True if should be exception, False if not
        """
        annotation = self.get_db_annotation(entity_key)
        
        if should_exist:
            assert annotation is not None, \
                f"Expected exception for {entity_key}, but no annotation found"
            has_just = bool(annotation.get("justification", "").strip())
            has_status = "exception" in str(annotation.get("review_status", "")).lower()
            assert has_just or has_status, \
                f"Expected exception for {entity_key}, but no justification/status: {annotation}"
        else:
            if annotation:
                has_just = bool(annotation.get("justification", "").strip())
                has_status = "exception" in str(annotation.get("review_status", "")).lower()
                assert not (has_just or has_status), \
                    f"Expected NO exception for {entity_key}, but found: {annotation}"

    # =========================================================================
    # State Transition Helpers
    # =========================================================================

    def transition_finding_status(
        self,
        from_status: str,
        to_status: str,
        finding: dict | None = None,
    ) -> dict:
        """
        Helper to transition a finding between statuses.
        
        Args:
            from_status: Starting status (FAIL, WARN, PASS)
            to_status: Target status
            finding: Existing finding to modify (or creates new)
            
        Returns:
            New finding dict with updated status
        """
        if finding is None:
            finding = self.create_mock_finding(status=from_status)
        
        # Create new finding with same key but different status
        new_finding = finding.copy()
        new_finding["status"] = to_status
        new_finding["risk_level"] = "HIGH_PRIVILEGE" if to_status == "FAIL" else ""
        return new_finding
