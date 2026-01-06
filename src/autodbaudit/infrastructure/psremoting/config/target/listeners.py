"""
WinRM listener management for target hosts.
"""

import json
import logging
from typing import Callable, Tuple, Optional

from .utils import run_and_capture

logger = logging.getLogger(__name__)


def ensure_winrm_listeners(server_name: str, runner: Callable[[str], object]) -> Tuple[bool, Optional[str]]:
    """Create HTTP/HTTPS listeners if missing and return revert."""
    script = f"""
Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{
    $listeners = Get-WSManInstance -ResourceURI winrm/config/Listener -Enumerate
    $httpExists = $listeners | Where-Object {{ $_.Transport -eq 'HTTP' }}
    $httpsExists = $listeners | Where-Object {{ $_.Transport -eq 'HTTPS' }}
    $prev = [ordered]@{{ http=$null -ne $httpExists; https=$null -ne $httpsExists }}

    if (-not $httpExists) {{
        New-WSManInstance -ResourceURI winrm/config/Listener -SelectorSet @{{
            Address = 'IP';
            Transport = 'HTTP'
        }} -ValueSet @{{
            Port = '5985';
            Hostname = '';
            Enabled = 'true'
        }}
    }}

    if (-not $httpsExists) {{
        New-WSManInstance -ResourceURI winrm/config/Listener -SelectorSet @{{
            Address = 'IP';
            Transport = 'HTTPS'
        }} -ValueSet @{{
            Port = '5986';
            Hostname = '';
            Enabled = 'true'
        }}
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
            http_prev = state.get("http")
            https_prev = state.get("https")
            revert = (
                f"Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{ "
                f"if ($true -ne {http_prev}) {{ "
                "Remove-WSManInstance -ResourceURI winrm/config/Listener -SelectorSet @{Address='IP';Transport='HTTP'} -ErrorAction SilentlyContinue }} "
                f"if ($true -ne {https_prev}) {{ "
                "Remove-WSManInstance -ResourceURI winrm/config/Listener -SelectorSet @{Address='IP';Transport='HTTPS'} -ErrorAction SilentlyContinue }} "
                "}}"
            )
        except json.JSONDecodeError:
            revert = (
                f"Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{ "
                "Remove-WSManInstance -ResourceURI winrm/config/Listener -SelectorSet @{Address='IP';Transport='HTTP'} -ErrorAction SilentlyContinue; "
                "Remove-WSManInstance -ResourceURI winrm/config/Listener -SelectorSet @{Address='IP';Transport='HTTPS'} -ErrorAction SilentlyContinue }}"
            )
    return success, revert
