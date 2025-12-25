"""
Manual Script Generator - Layer 8.

Generates PowerShell scripts for manual execution when all automated
layers fail. Scripts include embedded state capture and auto-revert.
"""

from __future__ import annotations

import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autodbaudit.infrastructure.config_loader import SqlTarget

logger = logging.getLogger(__name__)


# Template for the manual enable script
ENABLE_SCRIPT_TEMPLATE = """# ============================================================================
# AutoDBAudit - Enable WinRM Script
# Target: {hostname}
# Generated: {timestamp}
# ============================================================================
# 
# INSTRUCTIONS:
# 1. Copy this script to the target server
# 2. Run PowerShell as Administrator
# 3. Execute: .\\EnableWinRM_{safe_hostname}.ps1 -Apply
# 
# TO REVERT:
#   .\\EnableWinRM_{safe_hostname}.ps1 -Revert
#
# ============================================================================

param(
    [switch]$Apply,
    [switch]$Revert,
    [switch]$Status
)

$ErrorActionPreference = "Stop"
$StateDir = "$env:ProgramData\\AutoDBAudit"
$StateFile = "$StateDir\\access_state_{guid}.json"

# ============================================================================
# STATE CAPTURE FUNCTIONS
# ============================================================================

function Get-CurrentState {{
    $state = @{{
        captured_at = (Get-Date).ToString("o")
        hostname = $env:COMPUTERNAME
        
        # WinRM Service
        winrm_service = $null
        
        # Firewall
        firewall_rules = @()
        
        # TrustedHosts (not applicable on target)
        
        # Services
        services = @{{}}
    }}
    
    # Capture WinRM service state
    try {{
        $svc = Get-Service WinRM
        $state.winrm_service = @{{
            name = $svc.Name
            status = $svc.Status.ToString()
            startup_type = $svc.StartType.ToString()
        }}
    }} catch {{
        Write-Warning "Could not capture WinRM service state"
    }}
    
    # Capture firewall rules
    try {{
        $rules = Get-NetFirewallRule -Name "WINRM*","AutoDBAudit*" -ErrorAction SilentlyContinue
        foreach ($rule in $rules) {{
            $state.firewall_rules += @{{
                name = $rule.Name
                display_name = $rule.DisplayName
                enabled = ($rule.Enabled -eq "True")
                existed_before = $true
            }}
        }}
    }} catch {{
        Write-Warning "Could not capture firewall rules"
    }}
    
    # Capture related services
    $servicesToCapture = @("RemoteRegistry", "Schedule", "LanmanServer")
    foreach ($svcName in $servicesToCapture) {{
        try {{
            $svc = Get-Service $svcName -ErrorAction SilentlyContinue
            if ($svc) {{
                $state.services[$svcName] = @{{
                    name = $svc.Name
                    status = $svc.Status.ToString()
                    startup_type = $svc.StartType.ToString()
                }}
            }}
        }} catch {{ }}
    }}
    
    return $state
}}

function Save-State {{
    param($State)
    
    if (-not (Test-Path $StateDir)) {{
        New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
    }}
    
    $State | ConvertTo-Json -Depth 10 | Set-Content $StateFile -Encoding UTF8
    Write-Host "State saved to: $StateFile" -ForegroundColor Green
}}

function Load-State {{
    if (-not (Test-Path $StateFile)) {{
        throw "No saved state found. Run with -Apply first."
    }}
    
    return Get-Content $StateFile -Raw | ConvertFrom-Json
}}

# ============================================================================
# APPLY FUNCTION
# ============================================================================

function Apply-WinRMConfig {{
    Write-Host "\\n=== AutoDBAudit WinRM Enable ===" -ForegroundColor Cyan
    Write-Host "Target: {hostname}"
    Write-Host ""
    
    # Step 1: Capture current state FIRST
    Write-Host "[1/5] Capturing current state..." -ForegroundColor Yellow
    $state = Get-CurrentState
    Save-State -State $state
    
    # Step 2: Enable WinRM service
    Write-Host "[2/5] Enabling WinRM service..." -ForegroundColor Yellow
    try {{
        Set-Service WinRM -StartupType Automatic
        Start-Service WinRM
        Write-Host "  WinRM service started" -ForegroundColor Green
    }} catch {{
        Write-Warning "  Failed to start WinRM: $_"
    }}
    
    # Step 3: Run quickconfig
    Write-Host "[3/5] Running WinRM quickconfig..." -ForegroundColor Yellow
    try {{
        winrm quickconfig -quiet
        Write-Host "  WinRM configured" -ForegroundColor Green
    }} catch {{
        Write-Warning "  Quickconfig failed: $_"
    }}
    
    # Step 4: Enable PSRemoting
    Write-Host "[4/5] Enabling PowerShell Remoting..." -ForegroundColor Yellow
    try {{
        Enable-PSRemoting -Force -SkipNetworkProfileCheck -ErrorAction SilentlyContinue
        Write-Host "  PSRemoting enabled" -ForegroundColor Green
    }} catch {{
        Write-Warning "  PSRemoting failed: $_"
    }}
    
    # Step 5: Configure firewall
    Write-Host "[5/5] Configuring firewall..." -ForegroundColor Yellow
    try {{
        Enable-NetFirewallRule -Name "WINRM-HTTP-In-TCP" -ErrorAction SilentlyContinue
        Write-Host "  Firewall rule enabled" -ForegroundColor Green
    }} catch {{
        # Try to create if doesn't exist
        try {{
            New-NetFirewallRule -Name "AutoDBAudit-WinRM" `
                -DisplayName "AutoDBAudit WinRM Access" `
                -Direction Inbound `
                -Protocol TCP `
                -LocalPort 5985 `
                -Action Allow `
                -Profile Any
            Write-Host "  Created firewall rule" -ForegroundColor Green
        }} catch {{
            Write-Warning "  Firewall configuration failed: $_"
        }}
    }}
    
    # Verification
    Write-Host "\\n=== Verification ===" -ForegroundColor Cyan
    $svc = Get-Service WinRM
    if ($svc.Status -eq "Running") {{
        Write-Host "WinRM Service: RUNNING" -ForegroundColor Green
    }} else {{
        Write-Host "WinRM Service: $($svc.Status)" -ForegroundColor Red
    }}
    
    Write-Host "\\n=== Done ===" -ForegroundColor Cyan
    Write-Host "To revert: .\\EnableWinRM_{safe_hostname}.ps1 -Revert"
    Write-Host ""
}}

# ============================================================================
# REVERT FUNCTION
# ============================================================================

function Revert-WinRMConfig {{
    Write-Host "\\n=== AutoDBAudit WinRM Revert ===" -ForegroundColor Cyan
    
    # Load saved state
    Write-Host "[1/4] Loading saved state..." -ForegroundColor Yellow
    $state = Load-State
    Write-Host "  State from: $($state.captured_at)"
    
    # Remove rules we may have created
    Write-Host "[2/4] Removing created firewall rules..." -ForegroundColor Yellow
    try {{
        Remove-NetFirewallRule -Name "AutoDBAudit-WinRM" -ErrorAction SilentlyContinue
        Write-Host "  Removed AutoDBAudit firewall rule" -ForegroundColor Green
    }} catch {{
        Write-Host "  No AutoDBAudit rule to remove" -ForegroundColor Gray
    }}
    
    # Restore original firewall rules state
    foreach ($rule in $state.firewall_rules) {{
        try {{
            if ($rule.existed_before) {{
                if ($rule.enabled) {{
                    Enable-NetFirewallRule -Name $rule.name -ErrorAction SilentlyContinue
                }} else {{
                    Disable-NetFirewallRule -Name $rule.name -ErrorAction SilentlyContinue
                }}
            }}
        }} catch {{ }}
    }}
    
    # Restore WinRM service
    Write-Host "[3/4] Restoring WinRM service..." -ForegroundColor Yellow
    if ($state.winrm_service) {{
        try {{
            Set-Service WinRM -StartupType $state.winrm_service.startup_type
            if ($state.winrm_service.status -eq "Stopped") {{
                Stop-Service WinRM -Force
                Write-Host "  WinRM stopped and set to $($state.winrm_service.startup_type)" -ForegroundColor Green
            }} else {{
                Write-Host "  WinRM startup type set to $($state.winrm_service.startup_type)" -ForegroundColor Green
            }}
        }} catch {{
            Write-Warning "  Failed to restore WinRM: $_"
        }}
    }}
    
    # Cleanup state file
    Write-Host "[4/4] Cleaning up..." -ForegroundColor Yellow
    try {{
        Remove-Item $StateFile -Force
        Write-Host "  State file removed" -ForegroundColor Green
    }} catch {{ }}
    
    Write-Host "\\n=== Revert Complete ===" -ForegroundColor Cyan
    Write-Host ""
}}

# ============================================================================
# STATUS FUNCTION
# ============================================================================

function Show-Status {{
    Write-Host "\\n=== AutoDBAudit WinRM Status ===" -ForegroundColor Cyan
    
    # Current state
    $svc = Get-Service WinRM
    Write-Host "WinRM Service: $($svc.Status) ($($svc.StartType))"
    
    # Saved state
    if (Test-Path $StateFile) {{
        $state = Load-State
        Write-Host "\\nSaved State: YES (from $($state.captured_at))"
        Write-Host "Original WinRM: $($state.winrm_service.status) ($($state.winrm_service.startup_type))"
    }} else {{
        Write-Host "\\nSaved State: NONE"
    }}
    
    Write-Host ""
}}

# ============================================================================
# MAIN
# ============================================================================

if ($Apply) {{
    Apply-WinRMConfig
}} elseif ($Revert) {{
    Revert-WinRMConfig
}} elseif ($Status) {{
    Show-Status
}} else {{
    Write-Host "Usage:"
    Write-Host "  .\\EnableWinRM_{safe_hostname}.ps1 -Apply   # Enable WinRM (captures state first)"
    Write-Host "  .\\EnableWinRM_{safe_hostname}.ps1 -Revert  # Restore original state"
    Write-Host "  .\\EnableWinRM_{safe_hostname}.ps1 -Status  # Show current status"
}}
"""


class ManualScriptGenerator:
    """Generate manual PowerShell scripts for WinRM enablement."""

    def __init__(self, output_dir: Path):
        """
        Initialize generator.

        Args:
            output_dir: Directory to write scripts to
        """
        self.output_dir = output_dir
        self.scripts_dir = output_dir / "manual_scripts"

    def generate_enable_script(self, target: SqlTarget) -> Path:
        """
        Generate enable script for a target.

        Args:
            target: Target to generate script for

        Returns:
            Path to generated script
        """
        import uuid

        self.scripts_dir.mkdir(parents=True, exist_ok=True)

        # Safe hostname for filename
        safe_hostname = target.server.replace(".", "_").replace("\\", "_")

        script_content = ENABLE_SCRIPT_TEMPLATE.format(
            hostname=target.server,
            safe_hostname=safe_hostname,
            timestamp=datetime.now(timezone.utc).isoformat(),
            guid=str(uuid.uuid4())[:8],
        )

        script_path = self.scripts_dir / f"EnableWinRM_{safe_hostname}.ps1"
        script_path.write_text(script_content, encoding="utf-8")

        logger.info("Generated manual script: %s", script_path)
        return script_path

    def generate_batch_script(self, targets: list[SqlTarget]) -> Path:
        """
        Generate a batch script to run all enable scripts.

        Args:
            targets: List of targets

        Returns:
            Path to batch script
        """
        self.scripts_dir.mkdir(parents=True, exist_ok=True)

        lines = [
            "@echo off",
            "REM AutoDBAudit - Batch WinRM Enable",
            f"REM Generated: {datetime.now(timezone.utc).isoformat()}",
            "REM",
            "REM Run this on each target server",
            "",
        ]

        for target in targets:
            safe_hostname = target.server.replace(".", "_").replace("\\", "_")
            lines.append(f"echo === {target.server} ===")
            lines.append(
                f"powershell -ExecutionPolicy Bypass -File EnableWinRM_{safe_hostname}.ps1 -Apply"
            )
            lines.append("")

        lines.append("pause")

        batch_path = self.scripts_dir / "EnableWinRM_AllTargets.bat"
        batch_path.write_text("\n".join(lines), encoding="utf-8")

        logger.info("Generated batch script: %s", batch_path)
        return batch_path

    def generate_revert_batch(self, targets: list[SqlTarget]) -> Path:
        """Generate batch script to revert all targets."""
        self.scripts_dir.mkdir(parents=True, exist_ok=True)

        lines = [
            "@echo off",
            "REM AutoDBAudit - Batch WinRM Revert",
            f"REM Generated: {datetime.now(timezone.utc).isoformat()}",
            "",
        ]

        for target in targets:
            safe_hostname = target.server.replace(".", "_").replace("\\", "_")
            lines.append(f"echo === Reverting {target.server} ===")
            lines.append(
                f"powershell -ExecutionPolicy Bypass -File EnableWinRM_{safe_hostname}.ps1 -Revert"
            )
            lines.append("")

        lines.append("pause")

        batch_path = self.scripts_dir / "RevertWinRM_AllTargets.bat"
        batch_path.write_text("\n".join(lines), encoding="utf-8")

        return batch_path
