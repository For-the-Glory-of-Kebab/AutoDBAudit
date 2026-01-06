"""
PsExec fallback connectivity.
"""

import subprocess
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
from .utils import (
    base_attempt,
    result_from_attempt,
    cred_variants,
    cred_to_str,
    missing_tool_result,
)


def try_psexec_connection(
    server_name: str,
    bundle: CredentialBundle,
    attempts: List[ConnectionAttempt],
    credential_handler: credentials.CredentialHandler,
    timestamp_provider: Callable[[], str],
) -> PSRemotingResult:
    """Attempt psexec connectivity with credential variants."""
    if not _is_psexec_available():
        return missing_tool_result(
            "psexec",
            attempts,
            manual=[
                "# Download PsExec from Sysinternals and ensure it is on PATH.",
                "# Example: https://download.sysinternals.com/files/PSTools.zip",
            ],
        )

    base = base_attempt(
        server_name,
        layer="fallback_psexec",
        method=ConnectionMethod.PSEXEC,
        auth=AuthMethod.NTLM.value,
        protocol=Protocol.HTTP.value,
        port=445,
        credential_type=cred_to_str(credential_handler.get_credential_type(bundle)),
        timestamp_provider=timestamp_provider,
    )

    start = time.time()
    for username, password, _ in cred_variants(bundle, credential_handler):
        error = _test_psexec(server_name, username, password)
        if error is None:
            base.success = True
            base.error_message = None
            break
        base.error_message = error

    base.duration_ms = int((time.time() - start) * 1000)
    attempts.append(base)
    return result_from_attempt(attempts, base)


def _is_psexec_available() -> bool:
    """Check if psexec is available."""
    try:
        result = subprocess.run(["psexec", "/?"], capture_output=True, check=False)
        return result.returncode == 0 and "PsExec" in result.stderr.decode()
    except FileNotFoundError:
        return False


def _test_psexec(server_name: str, username: str | None, password: str | None) -> str | None:
    """Attempt a psexec noop using provided credentials if available."""
    if not _is_psexec_available():
        return "psexec not available"

    cmd = ["psexec", f"\\\\{server_name}", "cmd", "/c", "echo", "OK"]
    if username and password:
        cmd = ["psexec", f"\\\\{server_name}", "-u", username, "-p", password, "cmd", "/c", "echo", "OK"]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode == 0:
        return None
    return result.stderr.strip() or "psexec failed"
