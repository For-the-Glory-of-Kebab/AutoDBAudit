"""
PowerShell script generation utilities for remoting enablement.

This module provides ultra-granular utilities for generating PowerShell scripts
that can manually enable remoting on target servers when automatic methods fail.
"""

import logging
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from autodbaudit.domain.config import SqlTarget

logger = logging.getLogger(__name__)
console = Console()


class PowerShellScriptGenerator:
    """
    Service for generating PowerShell scripts to enable remoting on target servers.

    Provides fallback scripts when automatic remoting enablement fails.
    """

    def generate_remoting_script(
        self,
        target: SqlTarget,
        username: Optional[str] = None,
        include_credentials: bool = False
    ) -> str:
        """
        Generate a PowerShell script to enable remoting on a target server.

        Args:
            target: The SQL target to generate script for
            username: Optional username for credential setup
            include_credentials: Whether to include credential setup in the script

        Returns:
            Complete PowerShell script as string
        """
        script_parts = [
            self._generate_header(target),
            self._generate_remoting_enablement(),
            self._generate_firewall_rules(),
            self._generate_trusted_hosts(target.server),
        ]

        if include_credentials and username:
            script_parts.append(self._generate_credential_setup(username))

        script_parts.extend([
            self._generate_validation_tests(target),
            self._generate_footer()
        ])

        return "\n\n".join(script_parts)

    def save_script_to_file(
        self,
        target: SqlTarget,
        output_dir: Optional[Path] = None,
        username: Optional[str] = None
    ) -> Path:
        """
        Generate and save a PowerShell script to a file.

        Args:
            target: The SQL target to generate script for
            output_dir: Directory to save the script (default: current directory)
            username: Optional username for credential setup

        Returns:
            Path to the saved script file
        """
        if output_dir is None:
            output_dir = Path.cwd()

        output_dir.mkdir(parents=True, exist_ok=True)

        # Create safe filename from target name
        safe_name = (target.name.replace(' ', '_')
                    .replace('(', '').replace(')', ''))
        script_name = f"enable_remoting_{safe_name}.ps1"
        script_path = output_dir / script_name

        script_content = self.generate_remoting_script(target, username, include_credentials=True)

        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)

        logger.info("Generated remoting script: %s", script_path)
        return script_path

    def display_script_info(self, target: SqlTarget, script_path: Optional[Path] = None) -> None:
        """
        Display information about the generated script to the user.

        Args:
            target: The target server
            script_path: Path to the generated script
        """
        panel_content = f"""
[yellow]⚠️  Automatic remoting enablement failed for:[/yellow] [red]{target.name}[/red]

[blue]📄 Generated PowerShell script for manual execution:[/blue]

Run this script on the target server [bold]{target.server}[/bold] with administrator privileges:

[green]1.[/green] Copy the script to the target server
[green]2.[/green] Open PowerShell as Administrator
[green]3.[/green] Execute: [cyan].\\{script_path.name if script_path
                                      else 'enable_remoting_script.ps1'}[/cyan]
[green]4.[/green] Restart the application

[red]⚠️  This should only be used as a last resort![/red]
[red]⚠️  Manual script execution indicates configuration issues![/red]
"""

        if script_path:
            panel_content += f"\n[blue]📍 Script location:[/blue] {script_path}"

        console.print(Panel.fit(
            panel_content,
            title="🔧 Manual Remoting Enablement Required",
            border_style="red"
        ))

    def _generate_header(self, target: SqlTarget) -> str:
        """Generate the script header with metadata."""
        return f'''# PowerShell Script to Enable Remoting for AutoDBAudit
# Target: {target.name}
# Server: {target.server}
# Generated for manual execution when automatic enablement fails
#
# WARNING: This script should only be used as a fallback!
# Automatic remoting enablement should be the preferred method.

Write-Host "🔧 Enabling PowerShell Remoting for AutoDBAudit..." -ForegroundColor Yellow
Write-Host "Target Server: {target.server}" -ForegroundColor Cyan
Write-Host "Target Name: {target.name}" -ForegroundColor Cyan
Write-Host ""'''

    def _generate_remoting_enablement(self) -> str:
        """Generate commands to enable PowerShell remoting."""
        return '''# Enable PowerShell Remoting
Write-Host "📡 Enabling PowerShell Remoting..." -ForegroundColor Yellow
try {
    Enable-PSRemoting -Force -SkipNetworkProfileCheck
    Write-Host "✅ PowerShell Remoting enabled successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to enable PowerShell Remoting: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}'''

    def _generate_firewall_rules(self) -> str:
        """Generate firewall rule creation for remoting."""
        return '''# Configure Windows Firewall for Remoting
Write-Host "🔥 Configuring Windows Firewall..." -ForegroundColor Yellow
try {
    # Enable WinRM firewall rules
    Enable-NetFirewallRule -DisplayGroup "Windows Remote Management" -ErrorAction Stop
    Write-Host "✅ Firewall rules configured" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Firewall configuration failed (may already be configured): $($_.Exception.Message)" -ForegroundColor Yellow
}'''

    def _generate_trusted_hosts(self, server: str) -> str:
        """Generate trusted hosts configuration."""
        return f'''# Configure Trusted Hosts (if needed)
Write-Host "🤝 Configuring Trusted Hosts..." -ForegroundColor Yellow
$currentTrustedHosts = Get-Item WSMan:\\localhost\\Client\\TrustedHosts -ErrorAction SilentlyContinue

if ($currentTrustedHosts.Value -notlike "*{server}*") {{
    try {{
        Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value "{server}" -Concatenate -Force
        Write-Host "✅ Trusted hosts configured for {server}" -ForegroundColor Green
    }} catch {{
        Write-Host "⚠️  Trusted hosts configuration failed: $($_.Exception.Message)" -ForegroundColor Yellow
        $msg = ("You may need to run: Set-Item WSMan:\\localhost\\Client\\TrustedHosts "
                "-Value '{server}' -Force")
        Write-Host $msg -ForegroundColor Yellow
    }}
}} else {{
    Write-Host "ℹ️  Trusted hosts already configured for {server}" -ForegroundColor Blue
}}'''

    def _generate_credential_setup(self, username: str) -> str:
        """Generate credential setup commands."""
        return f'''# Setup Credentials (if needed)
Write-Host "🔐 Setting up credentials for {username}..." -ForegroundColor Yellow
try {{
    # Test credential access
    $cred = Get-Credential -UserName "{username}" -Message "Enter credentials for {username}"
    if ($cred) {{
        Write-Host "✅ Credentials configured for {username}" -ForegroundColor Green
    }}
}} catch {{
    Write-Host "⚠️  Credential setup failed: $($_.Exception.Message)" -ForegroundColor Yellow
}}'''

    def _generate_validation_tests(self, target: SqlTarget) -> str:
        """Generate validation tests to verify remoting works."""
        return f'''# Validation Tests
Write-Host "🧪 Running validation tests..." -ForegroundColor Yellow

# Test 1: Basic connectivity
Write-Host "Testing basic connectivity..." -ForegroundColor Cyan
try {{
    Test-Connection -ComputerName "{target.server}" -Count 1 -ErrorAction Stop
    Write-Host "✅ Basic connectivity test passed" -ForegroundColor Green
}} catch {{
    Write-Host "❌ Basic connectivity test failed: $($_.Exception.Message)" -ForegroundColor Red
}}

# Test 2: WinRM service
Write-Host "Testing WinRM service..." -ForegroundColor Cyan
try {{
    $winrmService = Get-Service -Name WinRM -ErrorAction Stop
    if ($winrmService.Status -eq "Running") {{
        Write-Host "✅ WinRM service is running" -ForegroundColor Green
    }} else {{
        Write-Host "⚠️  WinRM service is not running" -ForegroundColor Yellow
    }}
}} catch {{
    Write-Host "❌ WinRM service check failed: $($_.Exception.Message)" -ForegroundColor Red
}}

# Test 3: Remoting connectivity
Write-Host "Testing remoting connectivity..." -ForegroundColor Cyan
try {{
    $session = New-PSSession -ComputerName "{target.server}" -ErrorAction Stop
    if ($session) {{
        Write-Host "✅ Remoting connectivity test passed" -ForegroundColor Green
        Remove-PSSession $session
    }}
}} catch {{
    Write-Host "❌ Remoting connectivity test failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "You may need to run this script directly on the target server" -ForegroundColor Yellow
}}'''

    def _generate_footer(self) -> str:
        """Generate the script footer."""
        return '''# Completion
Write-Host ""
Write-Host "🎉 Remoting enablement script completed!" -ForegroundColor Green
Write-Host "You can now retry the AutoDBAudit prepare operation." -ForegroundColor Green
Write-Host ""
Write-Host "If issues persist, check:" -ForegroundColor Yellow
Write-Host "1. Windows Firewall settings" -ForegroundColor Yellow
Write-Host "2. User permissions and credentials" -ForegroundColor Yellow
Write-Host "3. Network connectivity" -ForegroundColor Yellow
Write-Host "4. WinRM service status" -ForegroundColor Yellow

Read-Host "Press Enter to exit"'''
