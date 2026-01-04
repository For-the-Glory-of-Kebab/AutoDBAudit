"""
Helpers for manual PS remoting troubleshooting artifacts.
"""

from typing import Callable, List

from ..models import ConnectionAttempt

TimestampProvider = Callable[[], str]


def generate_troubleshooting_report(
    server_name: str,
    attempts: List[ConnectionAttempt],
    timestamp_provider: TimestampProvider
) -> str:
    """Build a troubleshooting report for failed connection attempts."""
    report_lines = [
        f"# PS Remoting Troubleshooting Report for {server_name}",
        f"Generated: {timestamp_provider()}",
        "",
        "## Connection Attempts Summary",
        f"Total attempts: {len(attempts)}",
        "",
        "## Detailed Attempts:"
    ]

    for index, attempt in enumerate(attempts, 1):
        report_lines.extend([
            f"### Attempt {index}",
            f"- Server: {attempt.server_name}",
            f"- Auth Method: {getattr(attempt.auth_method, 'value', attempt.auth_method)}",
            f"- Protocol: {getattr(attempt.protocol, 'value', attempt.protocol)}",
            f"- Port: {attempt.port}",
            f"- Duration: {attempt.duration_ms}ms",
            f"- Error: {attempt.error_message or 'None'}",
            ""
        ])

    report_lines.extend([
        "## Common Issues Checklist",
        "",
        "### Network Connectivity",
        "- [ ] Can ping target server?",
        "- [ ] Are WinRM ports (5985/5986) open?",
        "- [ ] Is Windows Firewall blocking connections?",
        "",
        "### Authentication Issues",
        "- [ ] Are credentials correct?",
        "- [ ] Is account locked/disabled?",
        "- [ ] Does account have remote access permissions?",
        "- [ ] Is Kerberos working (domain joined)?",
        "",
        "### WinRM Configuration",
        "- [ ] Is WinRM service running?",
        "- [ ] Are WinRM listeners configured?",
        "- [ ] Is server in TrustedHosts (if using IP)?",
        "",
        "### Registry Settings",
        "- [ ] LocalAccountTokenFilterPolicy set (workgroup)?",
        "- [ ] DisableLoopbackCheck set (localhost)?",
        "",
        "### Group Policy",
        "- [ ] Is WinRM blocked by GPO?",
        "- [ ] Are firewall rules overridden by GPO?",
        "",
        "## Manual Setup Commands",
        "",
        "### On Target Server (run as Administrator):",
        "```powershell",
        "# Enable PS Remoting",
        "Enable-PSRemoting -Force -SkipNetworkProfileCheck",
        "",
        "# Configure WinRM service",
        "Set-Service -Name WinRM -StartupType Automatic",
        "Start-Service -Name WinRM",
        "",
        "# Add firewall rules",
        "Enable-NetFirewallRule -DisplayGroup 'Windows Remote Management'",
        "",
        "# Configure TrustedHosts (replace with actual IPs)",
        "Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value '*' -Force",
        "",
        "# Registry settings for workgroup scenarios",
        (
            "New-ItemProperty -Path "
            "'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' "
            "-Name 'LocalAccountTokenFilterPolicy' -Value 1 -PropertyType DWORD -Force"
        ),
        "",
        "# Registry settings for localhost scenarios",
        (
            "New-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa' "
            "-Name 'DisableLoopbackCheck' -Value 1 -PropertyType DWORD -Force"
        ),
        "```"
    ])

    return "\n".join(report_lines)


def generate_manual_setup_scripts(server_name: str) -> List[str]:
    """Return manual remediation scripts for target and client."""
    target_script = (
        f"# Manual PS Remoting Setup for {server_name}\n"
        f"# Run this script on {server_name} as Administrator\n\n"
        f"Write-Host \"Setting up PowerShell Remoting on {server_name}...\"\n\n"
        "# Enable PS Remoting\n"
        "Enable-PSRemoting -Force -SkipNetworkProfileCheck\n\n"
        "# Configure WinRM service\n"
        "Set-Service -Name WinRM -StartupType Automatic\n"
        "Start-Service -Name WinRM\n\n"
        "# Add firewall rules\n"
        "Enable-NetFirewallRule -DisplayGroup \"Windows Remote Management\"\n\n"
        "# Configure TrustedHosts (allow all for testing - restrict in production)\n"
        "Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value \"*\" -Force\n\n"
        "# Registry settings for workgroup scenarios\n"
        "New-ItemProperty -Path "
        "\"HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System\" "
        "-Name \"LocalAccountTokenFilterPolicy\" -Value 1 -PropertyType DWORD -Force\n\n"
        "# Registry settings for localhost scenarios\n"
        "New-ItemProperty -Path \"HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa\" "
        "-Name \"DisableLoopbackCheck\" -Value 1 -PropertyType DWORD -Force\n\n"
        "# Verify configuration\n"
        "Get-WSManInstance -ResourceURI winrm/config/listener "
        "-SelectorSet @{Address=\"*\";Transport=\"HTTP\"}\n\n"
        f"Write-Host \"PS Remoting setup complete on {server_name}\"\n"
    )

    client_script = (
        f"# Manual Client Setup for connecting to {server_name}\n"
        f"# Run this script on the client machine as Administrator\n\n"
        f"Write-Host \"Setting up client for PS Remoting to {server_name}...\"\n\n"
        "# Add target to TrustedHosts\n"
        "Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value "
        f"\"{server_name}\" -Concatenate -Force\n\n"
        "# Test connection\n"
        f"Test-WSMan -ComputerName {server_name}\n\n"
        f"Write-Host \"Client setup complete for {server_name}\"\n"
    )

    return [target_script, client_script]


def generate_revert_scripts(revert_scripts: List[str]) -> List[str]:
    """Return a copy of accumulated revert scripts."""
    return revert_scripts.copy()
