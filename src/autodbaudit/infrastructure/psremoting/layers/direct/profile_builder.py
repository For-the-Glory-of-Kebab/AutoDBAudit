"""Builder for connection profiles used in direct attempts."""

from datetime import datetime

from ...models import ConnectionMethod, ConnectionProfile, CredentialBundle
from ...credentials import CredentialHandler
from .utils import enum_to_value


def build_connection_profile(plan, bundle: CredentialBundle, credential_handler: CredentialHandler) -> ConnectionProfile:
    """Construct a connection profile from plan and credentials."""
    timestamp = datetime.now().isoformat()
    return ConnectionProfile(
        id=None,
        server_name=plan.server_name,
        connection_method=ConnectionMethod.POWERSHELL_REMOTING,
        auth_method=enum_to_value(plan.auth_method),
        protocol=enum_to_value(plan.protocol),
        port=plan.port,
        credential_type=enum_to_value(credential_handler.get_credential_type(bundle)),
        successful=False,
        last_successful_attempt=None,
        last_attempt=timestamp,
        attempt_count=0,
        sql_targets=[],
        baseline_state=None,
        current_state=None,
        created_at=timestamp,
        updated_at=timestamp,
    )
