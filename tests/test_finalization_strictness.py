import pytest
from unittest.mock import MagicMock
from autodbaudit.application.finalize_service import FinalizeService


def test_finalization_blocked_by_fails():
    """Verify finalization is blocked if FAILs exist."""
    # Mock Store
    mock_store = MagicMock()
    mock_store.get_latest_run_id.return_value = 1
    mock_store.get_audit_run.return_value = MagicMock(status="in_progress")

    # Mock Findings: 1 FAIL
    mock_store.get_findings.return_value = [
        {"entity_key": "k1", "finding_type": "ft", "status": "FAIL"},
        {"entity_key": "k2", "finding_type": "ft", "status": "PASS"},
    ]

    service = FinalizeService("output")
    service.store = mock_store

    # Attempt Finalize (No Force)
    result = service.finalize(run_id=1, force=False)

    assert "error" in result
    assert "Strict Finalization Block" in result["error"]
    assert "Cannot finalize: 1 outstanding FAILs" in result["error"]


def test_finalization_allowed_with_force():
    """Verify finalization logic proceeds if force=True despite FAILs."""
    # Mock Store
    mock_store = MagicMock()
    mock_store.get_latest_run_id.return_value = 1
    run_mock = MagicMock(status="in_progress", organization="TestOrg")
    mock_store.get_audit_run.return_value = run_mock

    # Mock Findings: 1 FAIL
    mock_store.get_findings.return_value = [
        {"entity_key": "k1", "finding_type": "ft", "status": "FAIL"}
    ]

    service = FinalizeService("output")
    service.store = mock_store

    # Mock other methods to avoid file I/O
    service._compute_file_hash = MagicMock(return_value="hash123")

    # Mock output path existence check to fail gracefully or pass?
    # Actually, finalize logic checks input file.
    # Let's just create a dummy file just in case or mock Path.exists
    # It's easier to mock the whole method flow, but we want to test the *logic switch*.
    # The key is that it *passed* the strict check.

    # We can inspect that it got past the check by seeing if it hit step 3 (Annotation Import)
    # We'll mock ExceptionService too.
    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "autodbaudit.application.finalize_service.ExceptionService", MagicMock()
        )
        # We also need to mock Path.exists to return False for the input file so it fails/returns early
        # OR just check that it didn't return the "Strict Block" error

        # Actually, let's just run it. It will likely fail at "Output report not found" step
        # but that proves it passed the strict check!

        result = service.finalize(run_id=1, force=True)

        # It should NOT be the strict block error.
        if "error" in result:
            assert "Strict Finalization Block" not in result["error"]
