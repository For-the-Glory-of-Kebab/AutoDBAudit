"""
Fallback connection strategies for PS remoting.

Exhausts WMI, PsExec, RPC, and SSH-based PowerShell paths with multiple credential formats.
"""

from typing import Callable, List, Tuple
import subprocess
import time

from ..credentials import CredentialHandler
from ..models import (
    AuthMethod,
    Protocol,
    ConnectionAttempt,
    CredentialBundle,
    PSRemotingResult,
    ConnectionMethod,
)

TimestampProvider = Callable[[], str]
# pylint: disable=line-too-long,too-many-arguments,too-many-positional-arguments,unused-argument


def try_ssh_powershell(
    server_name: str,
    bundle: CredentialBundle,
    attempts: List[ConnectionAttempt],
    credential_handler: CredentialHandler,
    timestamp_provider: TimestampProvider,
) -> PSRemotingResult:
    """Attempt SSH-based PowerShell connectivity."""
    if not _is_ssh_available():
        return PSRemotingResult(
            success=False,
            session=None,
            error_message="SSH not available",
            attempts_made=attempts,
            duration_ms=0,
            troubleshooting_report=None,
            manual_setup_scripts=None,
            revert_scripts=None,
        )

    attempt = _base_attempt(
        server_name,
        layer="fallback_ssh",
        method=ConnectionMethod.POWERSHELL_REMOTING,
        auth=AuthMethod.BASIC.value,
        protocol=Protocol.SSH.value,
        port=22,
        credential_type=_cred_to_str(credential_handler.get_credential_type(bundle)),
        timestamp_provider=timestamp_provider,
    )

    start = time.time()
    cred_variants = _credential_variants(bundle, credential_handler)
    for username, password, _ in cred_variants:
        error = _test_ssh(server_name, username, password)
        if error is None:
            attempt.success = True
            attempt.error_message = None
            break
        attempt.error_message = error

    attempt.duration_ms = int((time.time() - start) * 1000)
    attempts.append(attempt)
    return _result_from_attempt(attempts, attempt)


def try_wmi_connection(
    server_name: str,
    bundle: CredentialBundle,
    attempts: List[ConnectionAttempt],
    credential_handler: CredentialHandler,
    timestamp_provider: TimestampProvider,
) -> PSRemotingResult:
    """Attempt WMI-based connectivity with multiple credential variants."""
    base = _base_attempt(
        server_name,
        layer="fallback_wmi",
        method=ConnectionMethod.WMI,
        auth=AuthMethod.NTLM.value,
        protocol=Protocol.HTTP.value,
        port=135,
        credential_type=_cred_to_str(credential_handler.get_credential_type(bundle)),
        timestamp_provider=timestamp_provider,
    )

    cred_variants = _credential_variants(bundle, credential_handler)
    start = time.time()
    for username, password, ps_cred in cred_variants:
        error = _test_wmi(server_name, username, password, ps_cred)
        if error is None:
            base.success = True
            base.error_message = None
            break
        base.error_message = error

    base.duration_ms = int((time.time() - start) * 1000)
    attempts.append(base)
    return _result_from_attempt(attempts, base)


def try_psexec_connection(
    server_name: str,
    bundle: CredentialBundle,
    attempts: List[ConnectionAttempt],
    credential_handler: CredentialHandler,
    timestamp_provider: TimestampProvider,
) -> PSRemotingResult:
    """Attempt psexec connectivity with credential variants."""
    if not _is_psexec_available():
        return PSRemotingResult(
            success=False,
            session=None,
            error_message="psexec not available",
            attempts_made=attempts,
            duration_ms=0,
            troubleshooting_report=None,
            manual_setup_scripts=None,
            revert_scripts=None,
        )

    base = _base_attempt(
        server_name,
        layer="fallback_psexec",
        method=ConnectionMethod.PSEXEC,
        auth=AuthMethod.NTLM.value,
        protocol=Protocol.HTTP.value,
        port=445,
        credential_type=_cred_to_str(credential_handler.get_credential_type(bundle)),
        timestamp_provider=timestamp_provider,
    )

    start = time.time()
    cred_variants = _credential_variants(bundle, credential_handler)
    for username, password, _ in cred_variants:
        error = _test_psexec(server_name, username, password)
        if error is None:
            base.success = True
            base.error_message = None
            break
        base.error_message = error

    base.duration_ms = int((time.time() - start) * 1000)
    attempts.append(base)
    return _result_from_attempt(attempts, base)


def try_rpc_connection(
    server_name: str,
    bundle: CredentialBundle,
    attempts: List[ConnectionAttempt],
    credential_handler: CredentialHandler,
    timestamp_provider: TimestampProvider,
) -> PSRemotingResult:
    """Attempt RPC reachability check."""
    base = _base_attempt(
        server_name,
        layer="fallback_rpc",
        method=ConnectionMethod.POWERSHELL_REMOTING,
        auth=AuthMethod.NTLM.value,
        protocol=Protocol.HTTP.value,
        port=135,
        credential_type=_cred_to_str(credential_handler.get_credential_type(bundle)),
        timestamp_provider=timestamp_provider,
    )

    start = time.time()
    error = _test_rpc(server_name)
    base.success = error is None
    base.error_message = error
    base.duration_ms = int((time.time() - start) * 1000)
    attempts.append(base)
    return _result_from_attempt(attempts, base)


def _base_attempt(
    server_name: str,
    layer: str,
    method: ConnectionMethod,
    auth: str,
    protocol: str,
    port: int,
    credential_type: str | None,
    timestamp_provider: TimestampProvider,
) -> ConnectionAttempt:
    """Create a populated ConnectionAttempt."""
    ts = timestamp_provider()
    return ConnectionAttempt(
        profile_id=None,
        server_name=server_name,
        auth_method=auth,
        protocol=protocol,
        port=port,
        credential_type=credential_type,
        error_message=None,
        attempted_at=ts,
        layer=layer,
        connection_method=method,
        attempt_timestamp=ts,
        duration_ms=0,
        config_changes=None,
        rollback_actions=None,
        manual_script_path=None,
        created_at=ts,
    )


def _result_from_attempt(attempts: List[ConnectionAttempt], attempt: ConnectionAttempt) -> PSRemotingResult:
    """Return a PSRemotingResult based on a single attempt."""
    return PSRemotingResult(
        success=bool(attempt.success),
        session=None,
        error_message=attempt.error_message,
        attempts_made=attempts,
        duration_ms=attempt.duration_ms or 0,
        troubleshooting_report=None,
        manual_setup_scripts=None,
        revert_scripts=None,
        successful_permutations=[
            {
                "auth_method": attempt.auth_method,
                "protocol": attempt.protocol,
                "port": attempt.port,
                "credential_type": attempt.credential_type,
                "layer": attempt.layer,
            }
        ] if attempt.success else [],
    )


def _credential_variants(bundle: CredentialBundle, handler: CredentialHandler) -> List[Tuple[str | None, str | None, str | None]]:
    """
    Build credential permutations for domain/workgroup contexts.

    Returns list of (username, password, pscredential_expression).
    """
    variants: List[Tuple[str | None, str | None, str | None]] = []
    win = bundle.windows_explicit or {}
    username = win.get("username")
    password = win.get("password")
    ps_cred = handler.create_pscredential(bundle)

    if username and password:
        variants.append((username, password, ps_cred))
        if "\\" in username:
            user_only = username.split("\\", 1)[1]
            variants.append((user_only, password, ps_cred))
        if "@" in username:
            variants.append((username.split("@")[0], password, ps_cred))
    else:
        variants.append((None, None, ps_cred))
    return variants


def _is_ssh_available() -> bool:
    """Check if SSH client is available."""
    try:
        result = subprocess.run(["ssh", "-V"], capture_output=True, check=False)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _is_psexec_available() -> bool:
    """Check if psexec is available."""
    try:
        result = subprocess.run(["psexec", "/?"], capture_output=True, check=False)
        return result.returncode == 0 and "PsExec" in result.stderr.decode()
    except FileNotFoundError:
        return False


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


def _test_psexec(server_name: str, username: str | None, password: str | None) -> str | None:
    """Attempt a psexec noop using provided credentials if available."""  # pylint: disable=unused-argument
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


def _test_rpc(server_name: str) -> str | None:
    """Basic RPC reachability using Test-Connection as a proxy."""
    result = subprocess.run(
        ["powershell", "-Command", f"Test-Connection -ComputerName '{server_name}' -Count 1"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode == 0:
        return None
    return result.stderr.strip() or "RPC reachability failed"


def _test_ssh(server_name: str, username: str | None, password: str | None) -> str | None:
    """Attempt SSH connectivity and simple command execution."""
    ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
    if username:
        target = f"{username}@{server_name}"
    else:
        target = server_name
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


def _cred_to_str(value) -> str | None:
    """Normalize credential type to string for persistence/logging."""
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)
