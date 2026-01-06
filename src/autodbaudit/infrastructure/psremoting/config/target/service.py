"""
WinRM service management for target hosts.
"""

import json
import logging
from typing import Callable, Tuple, Optional

from .utils import run_and_capture

logger = logging.getLogger(__name__)


def ensure_winrm_service_running(server_name: str, runner: Callable[[str], object]) -> Tuple[bool, Optional[str]]:
    """Set WinRM to Automatic/start and return revert script restoring previous state."""
    script = f"""
Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{
    $svc = Get-Service -Name WinRM -ErrorAction SilentlyContinue
    $startup = (Get-WmiObject -Class Win32_Service -Filter "Name='WinRM'").StartMode
    $prev = @{{ status = $svc.Status; startup = $startup }}
    Set-Service -Name WinRM -StartupType Automatic -ErrorAction SilentlyContinue
    if ((Get-Service -Name WinRM).Status -ne 'Running') {{
        Start-Service -Name WinRM -ErrorAction Stop
    }}
    Enable-PSRemoting -Force
    return ($prev | ConvertTo-Json -Compress)
}}
"""
    previous = run_and_capture(server_name, script, runner)
    success = previous is not None
    revert = None
    if success:
        try:
            state = json.loads(previous or "{}")
            prev_status = state.get("status")
            prev_startup = state.get("startup")
            revert = (
                f"Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{ "
                f"Set-Service -Name WinRM -StartupType {prev_startup or 'Manual'} -ErrorAction SilentlyContinue; "
                f"if ('{prev_status}' -eq 'Stopped') {{ Stop-Service -Name WinRM -ErrorAction SilentlyContinue }} "
                f"}}"
            )
        except json.JSONDecodeError:
            revert = (
                f"Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{ "
                "Stop-Service -Name WinRM -ErrorAction SilentlyContinue; "
                "Set-Service -Name WinRM -StartupType Manual -ErrorAction SilentlyContinue }}"
            )
    return success, revert

