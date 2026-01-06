"""
RPC reachability fallback.
"""

import time
from typing import List, Callable

from ... import credentials
from ...models import (
    AuthMethod,
    Protocol,
    ConnectionAttempt,
    CredentialBundle,
    PSRemotingResult,
    ConnectionMethod,
)
from .utils import base_attempt, result_from_attempt, cred_to_str, test_rpc


def try_rpc_connection(
    server_name: str,
    bundle: CredentialBundle,
    attempts: List[ConnectionAttempt],
    credential_handler: credentials.CredentialHandler,
    timestamp_provider: Callable[[], str],
) -> PSRemotingResult:
    """Attempt RPC reachability check."""
    base = base_attempt(
        server_name,
        layer="fallback_rpc",
        method=ConnectionMethod.POWERSHELL_REMOTING,
        auth=AuthMethod.NTLM.value,
        protocol=Protocol.HTTP.value,
        port=135,
        credential_type=cred_to_str(credential_handler.get_credential_type(bundle)),
        timestamp_provider=timestamp_provider,
    )

    start = time.time()
    error = test_rpc(server_name)
    base.success = error is None
    base.error_message = error
    base.duration_ms = int((time.time() - start) * 1000)
    attempts.append(base)
    return result_from_attempt(attempts, base)
