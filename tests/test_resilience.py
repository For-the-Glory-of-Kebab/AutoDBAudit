import pytest
from unittest.mock import MagicMock, patch
from autodbaudit.application.sync_service import SyncService
from autodbaudit.infrastructure.sqlite.store import HistoryStore
from pathlib import Path


def test_sync_rollbacks_on_exceptions():
    """Verify that an exception during sync marks the run as failed and acts as a rollback."""
    # Setup Store with in-memory DB
    store = HistoryStore(":memory:")
    store.initialize_schema()

    # Create Baseline
    baseline = store.begin_audit_run("Baseline")
    store.complete_audit_run(baseline.id, "completed")

    service = SyncService(":memory:")
    service.store = store

    # Mock AuditService to simulate crash
    mock_audit_svc = MagicMock()

    # Mock it to create a run BUT then crash
    def crash_run_audit(*args, **kwargs):
        # Create a new run (simulate what AuditService does)
        run = store.begin_audit_run("Sync Attempt 1")
        # Then DIE
        raise RuntimeError("Simulated Crash!!!!")

    mock_audit_svc.run_audit.side_effect = crash_run_audit

    # Execute Sync
    result = service.sync(audit_service=mock_audit_svc)

    # Verify Error Response
    assert "error" in result
    assert "Simulated Crash" in result["error"]

    # Verify DB State: Latest run should be FAILED
    # We allow get_latest_run_id to see failed ones for this check
    failed_id = store.get_latest_run_id(include_failed=True)
    assert failed_id > baseline.id

    run_info = store.get_audit_run(failed_id)
    assert run_info.status == "failed"

    # Verify Logical Rollback: get_latest_run_id() (standard) should return Baseline
    # effectively "forgetting" the failed run
    valid_id = store.get_latest_run_id(include_failed=False)
    assert valid_id == baseline.id


def test_manual_interruption_rollback():
    """Verify KeyboardInterrupt is handled gracefully."""
    store = HistoryStore(":memory:")
    store.initialize_schema()
    baseline = store.begin_audit_run("Baseline")
    store.complete_audit_run(baseline.id, "completed")

    service = SyncService(":memory:")
    service.store = store

    mock_audit_svc = MagicMock()

    def interrupt_audit(*args, **kwargs):
        store.begin_audit_run("Sync Attempt Interrupted")
        raise KeyboardInterrupt()

    mock_audit_svc.run_audit.side_effect = interrupt_audit

    try:
        service.sync(audit_service=mock_audit_svc)
    except KeyboardInterrupt:
        pytest.fail("KeyboardInterrupt should be caught and handled!")

    # Verify status
    failed_id = store.get_latest_run_id(include_failed=True)
    run_info = store.get_audit_run(failed_id)
    assert run_info.status == "failed"
    valid_id = store.get_latest_run_id(include_failed=False)
    assert valid_id
    assert valid_id == baseline.id
