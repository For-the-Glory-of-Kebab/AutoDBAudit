"""
Registry configuration for WinRM-related access on target hosts.
"""

import json
import logging
from typing import Callable, Tuple, Optional

from .utils import run_and_capture

logger = logging.getLogger(__name__)


def configure_registry_settings(server_name: str, runner: Callable[[str], object]) -> Tuple[bool, Optional[str]]:
    """Apply registry keys that unblock remote administrative actions and return revert."""
    script = f"""
Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{
    $prevLatfp = (Get-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" -Name "LocalAccountTokenFilterPolicy" -ErrorAction SilentlyContinue).LocalAccountTokenFilterPolicy
    $prevLoop = (Get-ItemProperty -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa" -Name "DisableLoopbackCheck" -ErrorAction SilentlyContinue).DisableLoopbackCheck
    New-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" `
        -Name "LocalAccountTokenFilterPolicy" -Value 1 -PropertyType DWORD -Force
    New-ItemProperty -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa" `
        -Name "DisableLoopbackCheck" -Value 1 -PropertyType DWORD -Force
    $prev = [ordered]@{{ latfp = $prevLatfp; loopback = $prevLoop }}
    return ($prev | ConvertTo-Json -Compress)
}}
"""
    previous = run_and_capture(server_name, script, runner)
    success = previous is not None
    revert = None
    if success:
        try:
            state = json.loads(previous or "{}")
            latfp = state.get("latfp")
            loopback = state.get("loopback")
            latfp_cmd = (
                "Remove-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' -Name 'LocalAccountTokenFilterPolicy' -ErrorAction SilentlyContinue"
                if latfp is None else
                f"Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' -Name 'LocalAccountTokenFilterPolicy' -Value {latfp} -Force"
            )
            loop_cmd = (
                "Remove-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa' -Name 'DisableLoopbackCheck' -ErrorAction SilentlyContinue"
                if loopback is None else
                f"Set-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa' -Name 'DisableLoopbackCheck' -Value {loopback} -Force"
            )
            revert = (
                f"Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{ {latfp_cmd}; {loop_cmd} }}"
            )
        except json.JSONDecodeError:
            revert = (
                f"Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{ "
                "Remove-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' -Name 'LocalAccountTokenFilterPolicy' -ErrorAction SilentlyContinue; "
                "Remove-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa' -Name 'DisableLoopbackCheck' -ErrorAction SilentlyContinue }}"
            )
    return success, revert
