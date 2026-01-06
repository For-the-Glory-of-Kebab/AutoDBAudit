"""Execute PowerShell direct connection attempts."""

import subprocess
import time
from typing import Optional

from ...models import PSSession, ConnectionProfile, CredentialBundle
from ...credentials import CredentialHandler
from .command_builder import build_connection_command


def execute_connection_attempt(
    profile: ConnectionProfile,
    bundle: CredentialBundle,
    credential_handler: CredentialHandler,
    timestamp_provider,
    is_windows: bool,
    username_override: str | None = None,
    password_override: str | None = None,
) -> Optional[PSSession]:
    """Execute actual PowerShell connection attempt."""
    if not is_windows:
        raise RuntimeError("PS Remoting only supported on Windows")

    ps_command = build_connection_command(
        profile, bundle, credential_handler, username_override, password_override
    )

    result = subprocess.run(
        ["powershell", "-Command", ps_command],
        capture_output=True,
        text=True,
        timeout=12,
        check=False,
    )

    if result.returncode == 0 and "Connected" in result.stdout:
        return PSSession(
            session_id=f"{profile.server_name}_{int(time.time())}",
            server_name=profile.server_name,
            connection_profile=profile,
            created_at=timestamp_provider(),
        )

    raise RuntimeError(f"Connection failed: {result.stderr}")
