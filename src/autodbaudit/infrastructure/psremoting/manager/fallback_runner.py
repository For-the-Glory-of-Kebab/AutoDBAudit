"""
Layer 4: Advanced fallback execution.
"""

from typing import List, Callable

from ..models import CredentialBundle, ConnectionAttempt, PSRemotingResult
from ..credentials import CredentialHandler
from ..layers.fallbacks import (
    try_psexec_connection,
    try_rpc_connection,
    try_ssh_powershell,
    try_wmi_connection,
)

# pylint: disable=too-many-arguments,too-many-positional-arguments
def run_advanced_fallbacks(
    server_name: str,
    bundle: CredentialBundle,
    attempts: List[ConnectionAttempt],
    credential_handler: CredentialHandler,
    timestamp_provider: Callable[[], str],
    revert_scripts: List[str] | None,
) -> PSRemotingResult:
    """
    Try SSH, WMI, psexec, then RPC fallbacks.

    Returns the first successful PSRemotingResult, or a consolidated failure.
    """
    result = try_ssh_powershell(
        server_name,
        bundle,
        attempts,
        credential_handler,
        timestamp_provider,
    )
    if result.is_success():
        return result

    result = try_wmi_connection(
        server_name,
        bundle,
        attempts,
        credential_handler,
        timestamp_provider,
    )
    if result.is_success():
        return result

    result = try_psexec_connection(
        server_name,
        bundle,
        attempts,
        credential_handler,
        timestamp_provider,
    )
    if result.is_success():
        return result

    result = try_rpc_connection(
        server_name,
        bundle,
        attempts,
        credential_handler,
        timestamp_provider,
    )
    if result.is_success():
        return result

    return PSRemotingResult(
        success=False,
        session=None,
        error_message="Layer 4: All advanced fallbacks failed",
        attempts_made=attempts,
        duration_ms=0,
        troubleshooting_report=None,
        manual_setup_scripts=None,
        revert_scripts=revert_scripts,
    )
