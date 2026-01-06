"""
SSH-based PowerShell fallback.
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


def try_ssh_powershell(
    server_name: str,
    bundle: CredentialBundle,
    attempts: List[ConnectionAttempt],
    credential_handler: credentials.CredentialHandler,
    timestamp_provider: Callable[[], str],
) -> PSRemotingResult:
    """Attempt SSH-based PowerShell connectivity."""
    if not _is_ssh_available():
        return missing_tool_result(
            "ssh client",
            attempts,
            manual=[
                "# Install OpenSSH client on Windows:",
                "Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0",
                "# Or install via winget: winget install --id Microsoft.OpenSSH.Beta -e",
            ],
        )

    attempt = base_attempt(
        server_name,
        layer="fallback_ssh",
        method=ConnectionMethod.POWERSHELL_REMOTING,
        auth=AuthMethod.BASIC.value,
        protocol=Protocol.SSH.value,
        port=22,
        credential_type=cred_to_str(credential_handler.get_credential_type(bundle)),
        timestamp_provider=timestamp_provider,
    )

    start = time.time()
    variants = cred_variants(bundle, credential_handler)
    for username, password, _ in variants:
        error = _test_ssh(server_name, username, password)
        if error is None:
            attempt.success = True
            attempt.error_message = None
            break
        attempt.error_message = error

    attempt.duration_ms = int((time.time() - start) * 1000)
    attempts.append(attempt)
    return result_from_attempt(attempts, attempt)


def _is_ssh_available() -> bool:
    """Check if SSH client is available."""
    try:
        result = subprocess.run(["ssh", "-V"], capture_output=True, check=False)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _test_ssh(server_name: str, username: str | None, password: str | None) -> str | None:
    """Attempt SSH connectivity and simple command execution."""
    ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
    target = f"{username}@{server_name}" if username else server_name
    ssh_cmd.extend([target, "echo OK"])

    try:
        if password:
            proc = subprocess.run(
                ssh_cmd,
                input=password,
                text=True,
                capture_output=True,
                timeout=20,
                check=False,
            )
        else:
            proc = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        if proc.returncode == 0 and "OK" in (proc.stdout or ""):
            return None
        return proc.stderr.strip() or proc.stdout.strip() or "SSH command failed"
    except FileNotFoundError:
        return "ssh client not found"
    except subprocess.SubprocessError as exc:  # pylint: disable=broad-except
        return str(exc)
