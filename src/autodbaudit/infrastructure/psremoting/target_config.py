# pylint: disable=line-too-long,duplicate-code,R0801
"""
Target-side WinRM configuration helpers.

These functions encapsulate the PowerShell needed to bring a target server
into a remoting-ready state. Each helper delegates execution to the caller
via a provided runner so credentials and logging remain centralized.
"""

import logging
from typing import Callable

logger = logging.getLogger(__name__)

class TargetConfigurator:
    """Apply WinRM-related settings on a target host."""

    def ensure_winrm_service_running(self, server_name: str, runner: Callable[[str], object]) -> bool:
        """Set WinRM to Automatic and start the service."""
        script = f"""
Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{
    Set-Service -Name WinRM -StartupType Automatic -ErrorAction SilentlyContinue
    if ((Get-Service -Name WinRM).Status -ne 'Running') {{
        Start-Service -Name WinRM -ErrorAction Stop
    }}
    Enable-PSRemoting -Force
}}
"""
        return self._run_with_logging("winrm_service", server_name, script, runner)

    def configure_firewall_rules(self, server_name: str, runner: Callable[[str], object]) -> bool:
        """Open firewall rules for HTTP/HTTPS WinRM traffic."""
        script = f"""
Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{
    # Create or enable the default WinRM rules
    $httpRule = Get-NetFirewallRule -Name "WINRM-HTTP-In-TCP" -ErrorAction SilentlyContinue
    if (-not $httpRule) {{
        New-NetFirewallRule -Name "WINRM-HTTP-In-TCP" -DisplayName "Windows Remote Management (HTTP-In)" `
            -Enabled True -Direction Inbound -Protocol TCP -LocalPort 5985 -Action Allow
    }} else {{
        Enable-NetFirewallRule -Name "WINRM-HTTP-In-TCP"
    }}

    $httpsRule = Get-NetFirewallRule -Name "WINRM-HTTPS-In-TCP" -ErrorAction SilentlyContinue
    if (-not $httpsRule) {{
        New-NetFirewallRule -Name "WINRM-HTTPS-In-TCP" -DisplayName "Windows Remote Management (HTTPS-In)" `
            -Enabled True -Direction Inbound -Protocol TCP -LocalPort 5986 -Action Allow
    }} else {{
        Enable-NetFirewallRule -Name "WINRM-HTTPS-In-TCP"
    }}
}}
"""
        return self._run_with_logging("firewall_rules", server_name, script, runner)

    def configure_registry_settings(self, server_name: str, runner: Callable[[str], object]) -> bool:
        """Apply registry keys that unblock remote administrative actions."""
        script = f"""
Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{
    New-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" `
        -Name "LocalAccountTokenFilterPolicy" -Value 1 -PropertyType DWORD -Force
    New-ItemProperty -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa" `
        -Name "DisableLoopbackCheck" -Value 1 -PropertyType DWORD -Force
}}
"""
        return self._run_with_logging("registry_settings", server_name, script, runner)

    def ensure_winrm_listeners(self, server_name: str, runner: Callable[[str], object]) -> bool:
        """Create HTTP/HTTPS listeners if missing."""
        script = f"""
Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{
    $listeners = Get-WSManInstance -ResourceURI winrm/config/Listener -Enumerate
    $httpExists = $listeners | Where-Object {{ $_.Transport -eq 'HTTP' }}
    $httpsExists = $listeners | Where-Object {{ $_.Transport -eq 'HTTPS' }}

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
}}
"""
        return self._run_with_logging("winrm_listeners", server_name, script, runner)

    def configure_target_trustedhosts(
        self,
        server_name: str,
        client_ip: str,
        runner: Callable[[str], object]
    ) -> bool:
        """Add the client IP into the target's TrustedHosts list."""
        script = f"""
Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{
    Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value '{client_ip}' -Concatenate -Force
}}
"""
        return self._run_with_logging("target_trustedhosts", server_name, script, runner)

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
