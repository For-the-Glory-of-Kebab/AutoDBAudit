"""
Shared helpers for fallback connection strategies.
"""

from typing import Callable, List
import subprocess

from ...models import ConnectionAttempt, PSRemotingResult

TimestampProvider = Callable[[], str]


def base_attempt(
    server_name: str,
    layer: str,
    method,
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


def result_from_attempt(attempts: List[ConnectionAttempt], attempt: ConnectionAttempt) -> PSRemotingResult:
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


def cred_variants(bundle, handler) -> List[tuple[str | None, str | None, str | None]]:
    """
    Build credential permutations for domain/workgroup contexts.

    Returns list of (username, password, pscredential_expression).
    """
    variants: List[tuple[str | None, str | None, str | None]] = []
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


def cred_to_str(value) -> str | None:
    """Normalize credential type to string for persistence/logging."""
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def missing_tool_result(
    tool_name: str,
    attempts: List[ConnectionAttempt],
    manual: List[str],
) -> PSRemotingResult:
    """Return a standardized result when a required tool is missing."""
    return PSRemotingResult(
        success=False,
        session=None,
        error_message=f"{tool_name} not available",
        attempts_made=attempts,
        duration_ms=0,
        troubleshooting_report=None,
        manual_setup_scripts=manual,
        revert_scripts=None,
    )


def test_rpc(server_name: str) -> str | None:
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
