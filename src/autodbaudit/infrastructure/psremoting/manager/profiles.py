"""
Helpers for working with connection profiles (stored profile retry and persistence).
"""

from typing import List, Optional, Callable

from ..models import (
    ConnectionProfile,
    ConnectionAttempt,
    PSRemotingResult,
    CredentialBundle,
    ConnectionMethod,
)
from ..layers.direct_runner import DirectAttemptRunner
from ..credentials import CredentialHandler

# pylint: disable=too-many-arguments,too-many-positional-arguments
def try_stored_profile(
    profile: ConnectionProfile,
    bundle: CredentialBundle,
    attempts: List[ConnectionAttempt],
    profile_id: int,
    direct_runner: DirectAttemptRunner,
    credential_handler: CredentialHandler,
    timestamp_provider: Callable[[], str],
    revert_scripts: List[str] | None,
) -> PSRemotingResult:
    """Attempt to reuse a stored successful profile."""
    ts = timestamp_provider()
    attempt = ConnectionAttempt(
        profile_id=profile_id,
        server_name=profile.server_name,
        auth_method=profile.auth_method,
        protocol=profile.protocol,
        port=profile.port,
        credential_type=_credential_to_str(credential_handler.get_credential_type(bundle)),
        error_message=None,
        attempted_at=ts,
        attempt_timestamp=ts,
        layer="stored_profile",
        connection_method=profile.connection_method,
        created_at=ts,
        duration_ms=0,
        config_changes=None,
        rollback_actions=None,
        manual_script_path=None,
    )

    try:
        session = direct_runner.connect_with_profile(profile, bundle)
        if session:
            attempt.duration_ms = 100  # Minimal duration for stored profile
            attempt.success = True
            attempts.append(attempt)
            return PSRemotingResult(
                success=True,
                session=session,
                attempts_made=attempts,
                error_message=None,
                duration_ms=attempt.duration_ms or 0,
                troubleshooting_report=None,
                manual_setup_scripts=None,
                revert_scripts=revert_scripts,
            )
    except Exception as exc:  # pylint: disable=broad-except
        attempt.error_message = str(exc)
        attempt.duration_ms = 100

    attempts.append(attempt)
    return PSRemotingResult(
        success=False,
        session=None,
        error_message="Stored profile failed",
        attempts_made=attempts,
        duration_ms=attempt.duration_ms or 0,
        troubleshooting_report=None,
        manual_setup_scripts=None,
        revert_scripts=revert_scripts,
    )

def save_successful_profile(
    profile: ConnectionProfile,
    repository,
    timestamp_provider: Callable[[], str],
) -> int:
    """Persist a successful profile with refreshed timestamps."""
    timestamp = timestamp_provider()
    updated_profile = profile.model_copy(
        update={
            "last_successful_attempt": timestamp,
            "last_attempt": timestamp,
            "updated_at": timestamp,
            "successful": True,
        }
    )
    return repository.save_connection_profile(updated_profile)

def save_profile_from_attempt(
    attempt: ConnectionAttempt,
    profile_id: Optional[int],
    server_name: str,
    repository,
    timestamp_provider: Callable[[], str],
) -> int:
    """Persist a connection profile derived from a successful attempt (e.g., fallback)."""
    timestamp = timestamp_provider()
    profile = ConnectionProfile(
        id=profile_id,
        server_name=server_name,
        connection_method=attempt.connection_method or ConnectionMethod.POWERSHELL_REMOTING,
        auth_method=attempt.auth_method,
        protocol=attempt.protocol,
        port=attempt.port,
        credential_type=attempt.credential_type,
        successful=True,
        last_successful_attempt=timestamp,
        last_attempt=timestamp,
        attempt_count=1,
        sql_targets=[],
        baseline_state=None,
        current_state=None,
        created_at=timestamp,
        updated_at=timestamp,
    )
    return repository.save_connection_profile(profile)

def _credential_to_str(value) -> str | None:
    """Normalize credential type to string for persistence/logging."""
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)
