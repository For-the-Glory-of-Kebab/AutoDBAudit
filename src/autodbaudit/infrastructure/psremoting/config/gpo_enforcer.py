"""
Local policy/GPO tweaks for WinRM enablement.

Applies minimal WinRM auth/unencrypted allowances and captures prior values so
revert scripts can restore them.
"""
# pylint: disable=line-too-long

import json
import logging
from typing import Callable, Dict, Any, Tuple

logger = logging.getLogger(__name__)


def apply_winrm_policy(
    server_name: str,
    runner: Callable[[str], Any],
) -> Tuple[bool, Dict[str, Any]]:
    """
    Enable WinRM auth options (service + client), allow unencrypted traffic,
    and enable CredSSP. Captures previous values for full revert.

    Returns:
        (success, previous_settings)
    """
    previous: Dict[str, Any] = {}
    try:
        capture_script = f"""
        $serviceAuth = Get-WSManInstance -ResourceURI winrm/config/service/auth -ComputerName '{server_name}'
        $service = Get-WSManInstance -ResourceURI winrm/config/service -ComputerName '{server_name}'
        $clientAuth = Get-WSManInstance -ResourceURI winrm/config/client/auth -ComputerName '{server_name}'
        $client = Get-WSManInstance -ResourceURI winrm/config/client -ComputerName '{server_name}'
        $obj = [PSCustomObject]@{{
            ServiceBasic = $serviceAuth.Basic
            ServiceKerberos = $serviceAuth.Kerberos
            ServiceNegotiate = $serviceAuth.Negotiate
            ServiceCredSSP = $serviceAuth.CredSSP
            ServiceAllowUnencrypted = $service.AllowUnencrypted
            ClientBasic = $clientAuth.Basic
            ClientKerberos = $clientAuth.Kerberos
            ClientNegotiate = $clientAuth.Negotiate
            ClientCredSSP = $clientAuth.CredSSP
            ClientAllowUnencrypted = $client.AllowUnencrypted
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
        Set-WSManInstance -ResourceURI winrm/config/client/auth -ComputerName '{server_name}' -Value @{{Basic=\"true\"; Kerberos=\"true\"; Negotiate=\"true\"; CredSSP=\"true\"}}
        Set-WSManInstance -ResourceURI winrm/config/client -ComputerName '{server_name}' -Value @{{AllowUnencrypted=\"true\"}}
        Enable-WSManCredSSP -Role Server -Force -ErrorAction SilentlyContinue
        Enable-WSManCredSSP -Role Client -DelegateComputer '*' -Force -ErrorAction SilentlyContinue
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
    prev_service_basic = str(previous.get("ServiceBasic", "false")).lower()
    prev_service_kerb = str(previous.get("ServiceKerberos", "true")).lower()
    prev_service_neg = str(previous.get("ServiceNegotiate", "true")).lower()
    prev_service_credssp = str(previous.get("ServiceCredSSP", "false")).lower()
    prev_service_unenc = str(previous.get("ServiceAllowUnencrypted", "false")).lower()

    prev_client_basic = str(previous.get("ClientBasic", "false")).lower()
    prev_client_kerb = str(previous.get("ClientKerberos", "true")).lower()
    prev_client_neg = str(previous.get("ClientNegotiate", "true")).lower()
    prev_client_credssp = str(previous.get("ClientCredSSP", "false")).lower()
    prev_client_unenc = str(previous.get("ClientAllowUnencrypted", "false")).lower()

    return f"""
# Revert WinRM auth/unencrypted policy on {server_name}
Set-WSManInstance -ResourceURI winrm/config/service/auth -ComputerName '{server_name}' -Value @{{Basic=\"{prev_service_basic}\"; Kerberos=\"{prev_service_kerb}\"; Negotiate=\"{prev_service_neg}\"; CredSSP=\"{prev_service_credssp}\"}}
Set-WSManInstance -ResourceURI winrm/config/service -ComputerName '{server_name}' -Value @{{AllowUnencrypted=\"{prev_service_unenc}\"}}
Set-WSManInstance -ResourceURI winrm/config/client/auth -ComputerName '{server_name}' -Value @{{Basic=\"{prev_client_basic}\"; Kerberos=\"{prev_client_kerb}\"; Negotiate=\"{prev_client_neg}\"; CredSSP=\"{prev_client_credssp}\"}}
Set-WSManInstance -ResourceURI winrm/config/client -ComputerName '{server_name}' -Value @{{AllowUnencrypted=\"{prev_client_unenc}\"}}
Disable-WSManCredSSP -Role Server -ErrorAction SilentlyContinue
Disable-WSManCredSSP -Role Client -ErrorAction SilentlyContinue
"""
