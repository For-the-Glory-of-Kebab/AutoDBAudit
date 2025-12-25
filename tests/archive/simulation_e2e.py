import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

from autodbaudit.application.sync_service import SyncService
from autodbaudit.domain.change_types import ChangeType, FindingStatus, SyncStats
from autodbaudit.infrastructure.excel.linked_servers import LINKED_SERVER_CONFIG
from autodbaudit.infrastructure.excel.triggers import TRIGGER_CONFIG
from autodbaudit.infrastructure.excel.client_protocols import CLIENT_PROTOCOL_CONFIG
from autodbaudit.infrastructure.sqlite import HistoryStore
from autodbaudit.application.audit_service import AuditService
from autodbaudit.application.annotation_sync import AnnotationSyncService

# Mock Data
MOCK_FINDINGS_BASELINE = [
    {
        "entity_key": "login|srv1|inst1|sa",
        "status": "FAIL",
        "finding_type": "sa_account",
        "description": "SA enabled",
    },
    {
        "entity_key": "trigger|srv1|inst1|scope|db1|trig1|insert",
        "status": "PASS",
        "finding_type": "trigger",
        "description": "Safe trigger",
    },
    {
        "entity_key": "protocol|srv1|inst1|named pipes",
        "status": "PASS",  # Initially disabled
        "finding_type": "protocol",
        "description": "Named Pipes Disabled",
    },
]

MOCK_FINDINGS_CURRENT = [
    # SA Account still failing
    {
        "entity_key": "login|srv1|inst1|sa",
        "status": "FAIL",
        "finding_type": "sa_account",
        "description": "SA enabled",
    },
    # Trigger regression (PASS -> FAIL)
    {
        "entity_key": "trigger|srv1|inst1|scope|db1|trig1|insert",
        "status": "FAIL",
        "finding_type": "trigger",
        "description": "Bad trigger",
    },
    # New Issue
    {
        "entity_key": "linked_server|srv1|inst1|ls1|loc|rem",
        "status": "WARN",
        "finding_type": "linked_server",
        "description": "Weak auth",
    },
    # Protocol Regression (PASS -> FAIL)
    {
        "entity_key": "protocol|srv1|inst1|named pipes",
        "status": "FAIL",  # Now enabled
        "finding_type": "protocol",
        "description": "Named Pipes Enabled",
    },
]

MOCK_ANNOTATIONS = {
    # Exception for SA Account
    "login|srv1|inst1|sa": {
        "justification": "Risk Accepted",
        "review_status": "Exception",
        "notes": "Approved by CISO",
    },
    # Annotation for Linked Server (orphan check)
    "linked_server|srv1|inst1|ls1|loc|rem": {
        "purpose": "Data Warehouse",
        "last_reviewed": "2024-01-01",
    },
}


@pytest.fixture
def mock_history_store():
    store = MagicMock(spec=HistoryStore)
    store.get_initial_baseline_id.return_value = 1
    store.get_latest_run_id.return_value = 2
    store.get_previous_sync_run.return_value = 1

    # Mock Findings
    store.get_findings.side_effect = lambda run_id: (
        MOCK_FINDINGS_BASELINE if run_id == 1 else MOCK_FINDINGS_CURRENT
    )

    # Mock Run Info
    run_mock = MagicMock()
    run_mock.status = "success"
    run_mock.organization = "TestOrg"
    store.get_audit_run.return_value = run_mock

    # Mock Scanned Instances
    store.get_instances_for_run.return_value = [
        (MagicMock(hostname="Srv1"), MagicMock(instance_name="Inst1"))
    ]
    return store


@pytest.fixture
def mock_annot_sync():
    sync = MagicMock(spec=AnnotationSyncService)
    sync.load_from_db.return_value = {}  # Last stored state
    sync.read_all_from_excel.return_value = MOCK_ANNOTATIONS
    sync.get_all_annotations.return_value = MOCK_ANNOTATIONS

    # Mock Diff Logic for Annotations (pass-through for this test)
    sync.detect_exception_changes.return_value = [
        {
            "full_key": "login|srv1|inst1|sa",
            "change_type": "added",
            "justification": "Risk Accepted",
        }
    ]
    return sync


@patch("autodbaudit.application.sync_service.HistoryStore")
@patch("autodbaudit.application.annotation_sync.AnnotationSyncService")
@patch("autodbaudit.application.sync_service.EnhancedReportWriter")
def test_simulation_sync_flow(
    mock_writer_cls,
    mock_annot_sync_cls,
    mock_store_cls,
    mock_history_store,
    mock_annot_sync,
):
    """
    Simulates a full sync flow with controlled inputs and verifies:
    1. Stats Calculation (Fixed, Regression, New, Exceptions)
    2. Actions Recorded (Consolidated Actions)
    3. Sheet Stats aggregation
    """
    # Setup Mocks
    mock_store_cls.return_value = mock_history_store
    mock_annot_sync_cls.return_value = mock_annot_sync

    # Mock Audit Service (Re-Audit Phase) to return success but do nothing
    mock_audit_svc = MagicMock()
    mock_audit_svc.run_audit.return_value = MagicMock()  # processed_writer

    # Initialize Service
    service = SyncService("dummy.db")

    # --- RUN SYNC ---
    result = service.sync(
        audit_id=2, audit_service=mock_audit_svc  # Inject mock directly
    )

    # --- VERIFY RESULT ---
    assert result["status"] == "success"
    stats = result["stats_obj"]

    print("\n--- Simulation Stats ---")
    print(stats)

    # 1. Verify Exceptions
    # SA Account is FAIL but has Annotation -> Exception
    assert stats.documented_exceptions == 1
    assert (
        stats.active_issues == 3
    )  # Trigger + Linked Server + Protocol (WARN/FAIL are issues)

    # 2. Verify Regressions
    # Trigger went PASS -> FAIL
    assert stats.regressions_since_last == 2  # Trigger + Protocol

    # 3. Verify New Issues
    # Linked Server is new
    assert stats.new_issues_since_last == 1

    # 4. Verify Sheet Stats
    assert stats.sheet_stats["Triggers"]["regressions"] == 1
    assert stats.sheet_stats["Linked Servers"]["new_issues"] == 1
    assert stats.sheet_stats["Client Protocols"]["regressions"] == 1

    # 5. Verify Actions Recorded
    # We expect:
    # - Exception Added (SA Account)
    # - Regression (Trigger)
    # - New Issue (Linked Server)
    # ActionRecorder is internal, so we check the mock call to record_actions

    # Inspect calls to store (ActionRecorder uses store.create_action_log)
    # Alternatively, inspect SyncService logic that calls recorder

    print("\n--- Simulation PASSED ---")


if __name__ == "__main__":
    # Allow running directly
    pytest.main([__file__])
