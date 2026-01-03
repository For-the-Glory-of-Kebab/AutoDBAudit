"""
Local policy/GPO tweaks for WinRM enablement.

Applies minimal WinRM auth/unencrypted allowances and captures prior values so
revert scripts can restore them.
"""

import json
import logging
from typing import Callable, Dict, Any, Tuple

logger = logging.getLogger(__name__)


def apply_winrm_policy(
    server_name: str,
    runner: Callable[[str], Any],
) -> Tuple[bool, Dict[str, Any]]:
    """
    Enable WinRM auth options and allow unencrypted traffic, returning previous values.

    Returns:
        (success, previous_settings)
    """
    previous: Dict[str, Any] = {}
    try:
        capture_script = f"""
        $auth = Get-WSManInstance -ResourceURI winrm/config/service/auth -ComputerName '{server_name}'
        $service = Get-WSManInstance -ResourceURI winrm/config/service -ComputerName '{server_name}'
        $obj = [PSCustomObject]@{{
            Basic = $auth.Basic
            Kerberos = $auth.Kerberos
            Negotiate = $auth.Negotiate
            CredSSP = $auth.CredSSP
            AllowUnencrypted = $service.AllowUnencrypted
        }}
        $obj | ConvertTo-Json -Compress
        """
        capture_result = runner(capture_script)
        stdout = getattr(capture_result, "stdout", None)
        if stdout:
            previous = json.loads(stdout.strip())
    except Exception as exc:  # pylint: disable=broad-except
        logger.debug("Unable to capture prior WinRM policy on %s: %s", server_name, exc)

    try:
        apply_script = f"""
        Set-WSManInstance -ResourceURI winrm/config/service/auth -ComputerName '{server_name}' -Value @{{Basic=\"true\"; Kerberos=\"true\"; Negotiate=\"true\"; CredSSP=\"true\"}}
        Set-WSManInstance -ResourceURI winrm/config/service -ComputerName '{server_name}' -Value @{{AllowUnencrypted=\"true\"}}
        gpupdate /target:computer /force | Out-Null
        """
        result = runner(apply_script)
        success = getattr(result, "returncode", 1) == 0
        return success, previous
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Failed to apply WinRM policy on %s: %s", server_name, exc)
        return False, previous


def build_revert_script(server_name: str, previous: Dict[str, Any]) -> str:
    """Construct a revert script using captured prior values (or defaults)."""
    prev_basic = str(previous.get("Basic", "false")).lower()
    prev_kerb = str(previous.get("Kerberos", "true")).lower()
    prev_neg = str(previous.get("Negotiate", "true")).lower()
    prev_credssp = str(previous.get("CredSSP", "false")).lower()
    prev_unenc = str(previous.get("AllowUnencrypted", "false")).lower()

    return f"""
# Revert WinRM auth/unencrypted policy on {server_name}
Set-WSManInstance -ResourceURI winrm/config/service/auth -ComputerName '{server_name}' -Value @{{Basic=\"{prev_basic}\"; Kerberos=\"{prev_kerb}\"; Negotiate=\"{prev_neg}\"; CredSSP=\"{prev_credssp}\"}}
Set-WSManInstance -ResourceURI winrm/config/service -ComputerName '{server_name}' -Value @{{AllowUnencrypted=\"{prev_unenc}\"}}
"""
