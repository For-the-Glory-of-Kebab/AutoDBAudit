import pytest
from unittest.mock import MagicMock
from autodbaudit.application.remediation.handlers.access_control import (
    AccessControlHandler,
)
from autodbaudit.application.remediation.handlers.base import RemediationContext


def test_wrap_lockout_warning_connected_as_sa():
    """Verify that being connected as SA wraps the script in a warning."""
    context = RemediationContext(
        server_name="test_srv",
        instance_name="default",
        inst_id=1,
        port=1433,
        conn_user="sa",  # Connected as SA
        aggressiveness=1,
    )
    handler = AccessControlHandler(context)

    original_script = "ALTER LOGIN [sa] DISABLE;"
    wrapped = handler._wrap_lockout_warning(original_script, "sa")

    assert "!!! LOCKOUT RISK" in wrapped
    assert "-- ALTER LOGIN [sa] DISABLE;" in wrapped  # Should be commented out
    assert "connected as 'sa'" in wrapped.lower()


def test_wrap_lockout_warning_connected_as_other():
    """Verify standard users don't trigger warning (called manually for test)."""
    # The method _wrap_lockout_warning is a helper, logic to CALL it is inside handle().
    # This test just verifies the string formatting helper works.
    context = RemediationContext(
        server_name="test_srv",
        instance_name="default",
        inst_id=1,
        port=1433,
        conn_user="other_admin",
        aggressiveness=1,
    )
    handler = AccessControlHandler(context)

    script = "ALTER LOGIN [sa] DISABLE;"
    # Actually, the check happens inside handle(), let's test handle()

    finding = {
        "finding_type": "sa_account",
        "entity_name": "sa",
        "finding_description": "SA enabled",
    }

    # Test NOT SA
    actions = handler.handle(finding)
    assert len(actions) == 1
    # Check if category is "CAUTION" (standard) vs "REVIEW" (locked out)
    assert actions[0].category == "CAUTION"
    assert "LOCKOUT RISK" not in actions[0].script

    # Test SA
    context.conn_user = "sa"  # switch to SA
    handler = AccessControlHandler(context)  # re-init
    actions = handler.handle(finding)
    assert len(actions) == 1
    assert actions[0].category == "REVIEW"
    assert "LOCKOUT RISK" in actions[0].script
    assert "-- ALTER LOGIN" in actions[0].script
