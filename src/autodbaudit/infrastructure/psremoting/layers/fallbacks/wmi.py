"""
WMI fallback connectivity.
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
)


def try_wmi_connection(
    server_name: str,
    bundle: CredentialBundle,
    attempts: List[ConnectionAttempt],
    credential_handler: credentials.CredentialHandler,
    timestamp_provider: Callable[[], str],
) -> PSRemotingResult:
    """Attempt WMI-based connectivity with multiple credential variants."""
    base = base_attempt(
        server_name,
        layer="fallback_wmi",
        method=ConnectionMethod.WMI,
        auth=AuthMethod.NTLM.value,
        protocol=Protocol.HTTP.value,
        port=135,
        credential_type=cred_to_str(credential_handler.get_credential_type(bundle)),
        timestamp_provider=timestamp_provider,
    )

    variants = cred_variants(bundle, credential_handler)
    start = time.time()
    for username, password, ps_cred in variants:
        error = _test_wmi(server_name, username, password, ps_cred)
        if error is None:
            base.success = True
            base.error_message = None
            break
        base.error_message = error

    base.duration_ms = int((time.time() - start) * 1000)
    attempts.append(base)
    return result_from_attempt(attempts, base)


def _test_wmi(server_name: str, username: str | None, password: str | None, ps_cred: str | None) -> str | None:
    """Attempt a simple WMI query using PowerShell with optional credentials."""
    cred_part = f"-Credential ({ps_cred})" if ps_cred else ""
    script = (
        f"Get-WmiObject -Class Win32_OperatingSystem -ComputerName '{server_name}' "
        f"{cred_part} -ErrorAction Stop"
    )
    result = subprocess.run(
        ["powershell", "-Command", script],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode == 0:
        return None
    return result.stderr.strip() or "WMI query failed"
