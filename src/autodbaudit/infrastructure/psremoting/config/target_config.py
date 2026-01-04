# pylint: disable=line-too-long,duplicate-code,R0801
"""
Target-side WinRM configuration helpers.

These functions encapsulate the PowerShell needed to bring a target server
into a remoting-ready state. Each helper delegates execution to the caller
via a provided runner so credentials and logging remain centralized.
"""

import json
import logging
from typing import Callable

logger = logging.getLogger(__name__)

class TargetConfigurator:
    """Apply WinRM-related settings on a target host."""

    def ensure_winrm_service_running(
        self, server_name: str, runner: Callable[[str], object]
    ) -> tuple[bool, str | None]:
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
        previous = self._run_and_capture(server_name, script, runner)
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

    def configure_firewall_rules(
        self, server_name: str, runner: Callable[[str], object]
    ) -> tuple[bool, str | None]:
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
        previous = self._run_and_capture(server_name, script, runner)
        success = previous is not None
        revert = None
        if success:
            try:
                state = json.loads(previous or "{}")
                http_exists = state.get("httpExists")
                https_exists = state.get("httpsExists")
                http_enabled = state.get("httpEnabled")
                https_enabled = state.get("httpsEnabled")
                revert = (
                    f"Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{ "
                    "if ($true -ne "
                    f"{http_exists}) {{ Remove-NetFirewallRule -Name 'WINRM-HTTP-In-TCP' -ErrorAction SilentlyContinue }} "
                    "else {{ "
                    f"{'Enable' if http_enabled else 'Disable'}-NetFirewallRule -Name 'WINRM-HTTP-In-TCP' -ErrorAction SilentlyContinue }} "
                    "if ($true -ne "
                    f"{https_exists}) {{ Remove-NetFirewallRule -Name 'WINRM-HTTPS-In-TCP' -ErrorAction SilentlyContinue }} "
                    "else {{ "
                    f"{'Enable' if https_enabled else 'Disable'}-NetFirewallRule -Name 'WINRM-HTTPS-In-TCP' -ErrorAction SilentlyContinue }} "
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

    def configure_registry_settings(
        self, server_name: str, runner: Callable[[str], object]
    ) -> tuple[bool, str | None]:
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
        previous = self._run_and_capture(server_name, script, runner)
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

    def ensure_winrm_listeners(
        self, server_name: str, runner: Callable[[str], object]
    ) -> tuple[bool, str | None]:
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
        previous = self._run_and_capture(server_name, script, runner)
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

    def configure_target_trustedhosts(
        self,
        server_name: str,
        client_ip: str,
        runner: Callable[[str], object]
    ) -> tuple[bool, str | None]:
        """Add the client IP into the target's TrustedHosts list and build revert."""
        script = f"""
Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{
    $prev = (Get-Item WSMan:\\localhost\\Client\\TrustedHosts).Value
    Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value '{client_ip}' -Concatenate -Force
    return $prev
}}
"""
        previous = self._run_and_capture(server_name, script, runner)
        success = previous is not None
        revert = None
        if success:
            prev_value = str(previous)
            escaped = prev_value.replace("'", "''")
            revert = (
                f"Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{ "
                f"$prev = '{escaped}'; "
                "Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value $prev -Force }}"
            )
        return success, revert

    def trigger_gpupdate(
        self,
        server_name: str,
        runner: Callable[[str], object],
    ) -> bool:
        """Force a gpupdate on the target to apply policy changes immediately."""
        script = f"Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{ gpupdate /target:computer /force | Out-Null }}"
        try:
            result = runner(script)
            return getattr(result, "returncode", 1) == 0
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to trigger gpupdate on %s: %s", server_name, exc)
            return False

    def _run_with_logging(self, action: str, server_name: str, script: str, runner: Callable[[str], object]) -> bool:
        """Execute a script via runner and log result."""
        try:
            result = runner(script)
            success = getattr(result, "returncode", 1) == 0
            if success:
                logger.info("Applied %s on %s", action, server_name)
            else:
                logger.warning("Failed to apply %s on %s: %s", action, server_name, getattr(result, "stderr", ""))
            return success
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Error applying %s on %s: %s", action, server_name, exc)
            return False

    def _run_and_capture(self, server_name: str, script: str, runner: Callable[[str], object]) -> str | None:
        """Run a script and return stdout stripped, or None on failure."""
        try:
            result = runner(script)
            if getattr(result, "returncode", 1) != 0:
                logger.warning("Failed to capture state on %s: %s", server_name, getattr(result, "stderr", ""))
                return None
            return (getattr(result, "stdout", "") or "").strip()
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Error capturing state on %s: %s", server_name, exc)
            return None
