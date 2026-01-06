"""
Firewall configuration for WinRM on target hosts.
"""

import json
import logging
from typing import Callable, Tuple, Optional

from .utils import run_and_capture

logger = logging.getLogger(__name__)


def configure_firewall_rules(server_name: str, runner: Callable[[str], object]) -> Tuple[bool, Optional[str]]:
    """Open firewall rules for HTTP/HTTPS WinRM traffic and return revert."""
    script = f"""
Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{
    $httpRule = Get-NetFirewallRule -Name "WINRM-HTTP-In-TCP" -ErrorAction SilentlyContinue
    $httpsRule = Get-NetFirewallRule -Name "WINRM-HTTPS-In-TCP" -ErrorAction SilentlyContinue
    $prev = [ordered]@{{
        httpExists = $null -ne $httpRule
        httpsExists = $null -ne $httpsRule
        httpEnabled = $httpRule.Enabled
        httpsEnabled = $httpsRule.Enabled
    }}
    if (-not $httpRule) {{
        New-NetFirewallRule -Name "WINRM-HTTP-In-TCP" -DisplayName "Windows Remote Management (HTTP-In)" `
            -Enabled True -Direction Inbound -Protocol TCP -LocalPort 5985 -Action Allow
    }} else {{
        Enable-NetFirewallRule -Name "WINRM-HTTP-In-TCP"
    }}

    if (-not $httpsRule) {{
        New-NetFirewallRule -Name "WINRM-HTTPS-In-TCP" -DisplayName "Windows Remote Management (HTTPS-In)" `
            -Enabled True -Direction Inbound -Protocol TCP -LocalPort 5986 -Action Allow
    }} else {{
        Enable-NetFirewallRule -Name "WINRM-HTTPS-In-TCP"
    }}
    return ($prev | ConvertTo-Json -Compress)
}}
"""
    previous = run_and_capture(server_name, script, runner)
    success = previous is not None
    revert = None
    if success:
        try:
            state = json.loads(previous or "{}")
            http_exists = state.get("httpExists")
            https_exists = state.get("httpsExists")
            http_enabled = state.get("httpEnabled")
            https_enabled = state.get("httpsEnabled")
            http_toggle = "Enable" if http_enabled else "Disable"
            https_toggle = "Enable" if https_enabled else "Disable"
            revert = (
                f"Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{ "
                f"if ($true -ne {http_exists}) {{ Remove-NetFirewallRule -Name 'WINRM-HTTP-In-TCP' -ErrorAction SilentlyContinue }} else {{ "
                f"{http_toggle}-NetFirewallRule -Name 'WINRM-HTTP-In-TCP' -ErrorAction SilentlyContinue }} "
                f"if ($true -ne {https_exists}) {{ Remove-NetFirewallRule -Name 'WINRM-HTTPS-In-TCP' -ErrorAction SilentlyContinue }} else {{ "
                f"{https_toggle}-NetFirewallRule -Name 'WINRM-HTTPS-In-TCP' -ErrorAction SilentlyContinue }} "
                "}}"
            )
        except json.JSONDecodeError:
            revert = (
                f"Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{ "
                "Disable-NetFirewallRule -DisplayGroup 'Windows Remote Management' -ErrorAction SilentlyContinue; "
                "Remove-NetFirewallRule -Name 'WINRM-HTTP-In-TCP' -ErrorAction SilentlyContinue; "
                "Remove-NetFirewallRule -Name 'WINRM-HTTPS-In-TCP' -ErrorAction SilentlyContinue }}"
            )
    return success, revert
