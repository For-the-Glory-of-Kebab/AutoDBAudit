"""
TrustedHosts configuration on target hosts.
"""

import logging
from typing import Callable, Tuple, Optional

from .utils import run_and_capture

logger = logging.getLogger(__name__)


def configure_target_trustedhosts(
    server_name: str,
    client_ip: str,
    runner: Callable[[str], object]
) -> Tuple[bool, Optional[str]]:
    """Add the client IP into the target's TrustedHosts list and build revert."""
    script = f"""
Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{
    $prev = (Get-Item WSMan:\\localhost\\Client\\TrustedHosts).Value
    Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value '{client_ip}' -Concatenate -Force
    return $prev
}}
"""
    previous = run_and_capture(server_name, script, runner)
    success = previous is not None
    revert = None
    if success:
        prev_value = str(previous or "")
        escaped = prev_value.replace("'", "''")
        revert = (
            f"Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{ "
            f"$prev = '{escaped}'; "
            "Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value $prev -Force }}"
        )
    return success, revert
