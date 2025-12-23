<#
.SYNOPSIS
    Enable or disable PowerShell remote management with reversible security configurations.
    
.DESCRIPTION
    This script configures a target machine for PowerShell remote management and can revert all changes.
    It handles PSRemoting configuration, WinRM service setup, firewall rules, and permissions.
    All changes are reversible for security.
    
.PARAMETER Enable
    Enable remote PowerShell access. This is the default action if no parameter is specified.
    
.PARAMETER Disable
    Disable remote PowerShell access and revert all security changes made by this script.
    
.PARAMETER Force
    Force the action without confirmation prompts.
    
.EXAMPLE
    .\RemoteAccessConfig.ps1
    Enables remote access (default action)
    
.EXAMPLE
    .\RemoteAccessConfig.ps1 -Disable
    Disables remote access and reverts all changes
    
.NOTES
    Security Considerations:
    - Script automatically elevates to Administrator
    - All firewall rules are tagged and reversible
    - WinRM configuration is backed up before changes
    - Designed for temporary use by authorized administrators only
    
    REQUIREMENTS:
    - Must be run on Windows
    - Requires Administrator privileges for configuration changes
    
    WARNING:
    This script makes security-related changes to your system. Only use in trusted environments
    and revert changes immediately after completing administrative tasks.
#>

param(
    [switch]$Enable,
    [switch]$Disable,
    [switch]$Force
)

# Function to get the correct PowerShell executable path
function Get-PowerShellExecutable {
    if ($PSVersionTable.PSEdition -eq "Core") {
        # PowerShell Core (pwsh.exe)
        return "pwsh.exe"
    } else {
        # Windows PowerShell (powershell.exe)
        return "powershell.exe"
    }
}

# Self-elevation function
function Request-Elevation {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        $psExecutable = Get-PowerShellExecutable
        
        # Build arguments preserving all parameters
        $arguments = @(
            "-NoProfile"
            "-ExecutionPolicy Bypass"
            "-File `"$PSCommandPath`""
        )
        
        if ($Disable) { $arguments += "-Disable" }
        if ($Force) { $arguments += "-Force" }
        if ($Enable -or (-not $Enable -and -not $Disable)) { 
            # Default to Enable if no parameters or explicit Enable
            $arguments += "-Enable" 
        }
        
        $argumentString = $arguments -join " "
        
        try {
            Write-Host "Requesting elevation to Administrator privileges..." -ForegroundColor Yellow
            Write-Host "Command: $psExecutable $argumentString" -ForegroundColor DarkGray
            
            $processInfo = New-Object System.Diagnostics.ProcessStartInfo
            $processInfo.FileName = $psExecutable
            $processInfo.Arguments = $argumentString
            $processInfo.Verb = "runas"  # This triggers the UAC prompt
            $processInfo.UseShellExecute = $true  # Required for Verb to work
            $processInfo.CreateNoWindow = $false
            
            $process = [System.Diagnostics.Process]::Start($processInfo)
            
            # Only wait for exit if we're in an interactive session
            if ([Environment]::UserInteractive) {
                $process.WaitForExit()
                exit $process.ExitCode
            }
        } catch {
            Write-Error "Failed to elevate privileges. Please run this script as Administrator manually."
            exit 1
        }
    }
}

# Request elevation if not running as admin
Request-Elevation

# Set default action to Enable if no parameters specified
if (-not $Enable -and -not $Disable) {
    $Enable = $true
}

# Validate parameters
if ($Enable -and $Disable) {
    Write-Error "Cannot specify both -Enable and -Disable parameters simultaneously."
    exit 1
}

# Script constants
$scriptName = "RemoteAccessConfig"
$logFile = "$env:TEMP\$scriptName-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
$firewallRuleNamePrefix = "PSRemoteAccess_$scriptName"
$winrmServiceName = "WinRM"
$backupPath = "$env:ProgramData\$scriptName"
$backupFile = "$backupPath\config_backup_$(Get-Date -Format 'yyyyMMdd').json"
$trustedHostsBackupFile = "$backupPath\trustedhosts_backup.txt"

# Create backup directory
if (-not (Test-Path $backupPath)) {
    New-Item -Path $backupPath -ItemType Directory -Force -ErrorAction SilentlyContinue | Out-Null
}

# Function to write log entries
function Write-SafeLog {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    
    $color = switch ($Level) {
        "ERROR"   { "Red" }
        "WARNING" { "Yellow" }
        default   { "White" }
    }
    
    Write-Host $logEntry -ForegroundColor $color
    
    try {
        Add-Content -Path $logFile -Value $logEntry -ErrorAction Stop
    } catch {
        Write-Warning "Failed to write to log file: $logFile"
    }
}

# Function to backup current configuration
function Backup-WinRMConfig {
    Write-SafeLog "Creating backup of current WinRM configuration..."
    
    try {
        # Backup trusted hosts
        $trustedHosts = Get-Item WSMan:\localhost\Client\TrustedHosts -ErrorAction SilentlyContinue
        if ($trustedHosts -and $trustedHosts.Value) {
            $trustedHosts.Value | Out-File $trustedHostsBackupFile -Force
            Write-SafeLog "Trusted hosts backed up to: $trustedHostsBackupFile"
        } else {
            # Create empty backup file to indicate no trusted hosts were set
            "" | Out-File $trustedHostsBackupFile -Force
            Write-SafeLog "Created empty trusted hosts backup file"
        }
        
        # Backup WinRM service status
        $winrmService = Get-Service $winrmServiceName -ErrorAction SilentlyContinue
        if ($winrmService) {
            $backupData = @{
                timestamp = Get-Date
                winrmStatus = @{
                    Status = $winrmService.Status
                    StartType = $winrmService.StartType
                }
                firewallRules = @()
            }
            
            # Get existing firewall rules that might be affected
            $existingRules = Get-NetFirewallRule -DisplayName "$firewallRuleNamePrefix*" -ErrorAction SilentlyContinue
            if ($existingRules) {
                $backupData.firewallRules = $existingRules | Select-Object DisplayName, Enabled, Action, Direction
            }
            
            $backupData | ConvertTo-Json -Depth 10 | Out-File $backupFile -Force
            Write-SafeLog "WinRM configuration backed up to: $backupFile"
        }
    } catch {
        Write-SafeLog "Warning: Failed to create complete backup. Continuing anyway." "WARNING"
    }
}

# Function to enable remote access
function Enable-RemoteAccess {
    Write-SafeLog "=== STARTING REMOTE ACCESS ENABLEMENT ==="
    
    # Backup current config
    Backup-WinRMConfig
    
    try {
        # Determine which PowerShell version we're using
        $isWindowsPowerShell = $PSVersionTable.PSVersion.Major -lt 6 -or $PSVersionTable.PSEdition -eq "Desktop"
        
        Write-SafeLog "PowerShell version detected: $($PSVersionTable.PSVersion) ($($isWindowsPowerShell ? 'Windows PowerShell' : 'PowerShell Core'))"
        
        # Enable PSRemoting - handle different PowerShell versions
        Write-SafeLog "Enabling PSRemoting..."
        
        if ($isWindowsPowerShell) {
            # Windows PowerShell - use built-in cmdlet
            if ($Force) {
                Enable-PSRemoting -Force -SkipNetworkProfileCheck 2>&1 | Out-Null
            } else {
                Enable-PSRemoting -SkipNetworkProfileCheck 2>&1 | Out-Null
            }
            Write-SafeLog "PSRemoting enabled successfully in Windows PowerShell"
        } else {
            # PowerShell Core - enable for Windows PowerShell compatibility
            Write-SafeLog "Note: This is PowerShell Core. Using Windows PowerShell to enable remoting for full compatibility..." "WARNING"
            
            $command = {
                param($ForceParam)
                if ($ForceParam) {
                    Enable-PSRemoting -Force -SkipNetworkProfileCheck 2>&1 | Out-Null
                } else {
                    Enable-PSRemoting -SkipNetworkProfileCheck 2>&1 | Out-Null
                }
            }
            
            # Fixed the ArgumentList parameter issue here
            $arguments = @(
                "-Command"
                "& { $command }"
                "-ForceParam"
                $Force.IsPresent.ToString()
            )
            
            $result = Start-Process -FilePath "powershell.exe" -ArgumentList $arguments -Wait -PassThru -NoNewWindow
            
            if ($result.ExitCode -eq 0) {
                Write-SafeLog "PSRemoting enabled successfully via Windows PowerShell"
            } else {
                Write-SafeLog "Warning: PSRemoting enablement returned exit code $($result.ExitCode). Manual verification recommended." "WARNING"
            }
        }
        
        # Configure WinRM service
        Write-SafeLog "Configuring WinRM service..."
        try {
            Set-Service -Name $winrmServiceName -StartupType Automatic -ErrorAction Stop
            Start-Service -Name $winrmServiceName -ErrorAction Stop
            Write-SafeLog "WinRM service configured and started successfully"
        } catch {
            Write-SafeLog "Warning: Failed to configure WinRM service. It may already be configured." "WARNING"
        }
        
        # Configure WinRM listeners
        Write-SafeLog "Configuring WinRM listeners..."
        try {
            $listeners = Get-ChildItem WSMan:\localhost\Listener -ErrorAction Stop
            if (-not $listeners -or $listeners.Count -eq 0) {
                try {
                    New-Item -Path WSMan:\localhost\Listener -Transport HTTP -Address * -Force -ErrorAction Stop | Out-Null
                    Write-SafeLog "Created new HTTP listener"
                } catch {
                    Write-SafeLog "HTTP listener may already exist or was created by Enable-PSRemoting"
                }
            } else {
                Write-SafeLog "WinRM listeners already configured"
            }
        } catch {
            Write-SafeLog "WinRM listeners configuration skipped (may already be configured)"
        }
        
        # Set Trusted Hosts
        Write-SafeLog "Configuring trusted hosts..."
        $currentTrustedHosts = Get-Item WSMan:\localhost\Client\TrustedHosts -ErrorAction SilentlyContinue
        $currentValue = if ($currentTrustedHosts) { $currentTrustedHosts.Value } else { "" }
        
        if ($currentValue -notlike "*" -and $currentValue -notlike "*") {
            if (-not $Force) {
                $confirmation = Read-Host "This will set trusted hosts to accept connections from any host. Continue? (Y/N)"
                if ($confirmation -notlike "Y*") {
                    Write-SafeLog "Operation cancelled by user." "WARNING"
                    return
                }
            }
            Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force -Confirm:$false -ErrorAction Stop
            Write-SafeLog "Trusted hosts configured to accept all connections"
        } else {
            Write-SafeLog "Trusted hosts already configured appropriately"
        }
        
        # Configure firewall rules
        Write-SafeLog "Configuring firewall rules..."
        
        # Remove any existing rules from previous runs
        $existingRules = Get-NetFirewallRule -DisplayName "$firewallRuleNamePrefix*" -ErrorAction SilentlyContinue
        if ($existingRules) {
            $existingRules | Remove-NetFirewallRule -ErrorAction SilentlyContinue
            Write-SafeLog "Removed existing firewall rules from previous runs"
        }
        
        # Create HTTP rule (port 5985)
        try {
            $ruleParams = @{
                DisplayName = "$firewallRuleNamePrefix-HTTP"
                Name = "$firewallRuleNamePrefix-HTTP"
                Direction = "Inbound"
                Protocol = "TCP"
                LocalPort = 5985
                Action = "Allow"
                Enabled = "True"
                Description = "Temporary rule for PowerShell remoting - $scriptName"
                Group = $firewallRuleNamePrefix
                ErrorAction = "Stop"
            }
            
            New-NetFirewallRule @ruleParams | Out-Null
            Write-SafeLog "Firewall rule for HTTP (port 5985) created successfully"
        } catch {
            Write-SafeLog "Warning: Failed to create firewall rule. You may need to configure this manually." "WARNING"
            Write-SafeLog "Error details: $_" "WARNING"
        }
        
        # Test configuration
        Write-SafeLog "Testing WinRM configuration..."
        try {
            $testResult = Test-WsMan -ErrorAction Stop
            Write-SafeLog "WinRM test successful. Remote access should now be available."
        } catch {
            Write-SafeLog "WinRM test failed. Manual verification may be required." "WARNING"
            Write-SafeLog "Test error: $_" "WARNING"
        }
        
        # Display connection information
        $computerName = $env:COMPUTERNAME
        try {
            $ipAddresses = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop | 
                           Where-Object { $_.IPAddress -notmatch '^(127\.0\.0\.1|169\.254)' } | 
                           Select-Object -ExpandProperty IPAddress
        } catch {
            $ipAddresses = $null
        }
        
        Write-SafeLog "=== REMOTE ACCESS CONFIGURATION COMPLETE ==="
        Write-SafeLog "You can now connect using:"
        Write-SafeLog "Enter-PSSession -ComputerName $computerName"
        
        if ($ipAddresses) {
            foreach ($ip in $ipAddresses) {
                if (![string]::IsNullOrWhiteSpace($ip)) {
                    Write-SafeLog "Enter-PSSession -ComputerName $ip"
                }
            }
        }
        
        Write-SafeLog "=== IMPORTANT ==="
        Write-SafeLog "Run this script with -Disable parameter after completing your administrative tasks!"
        Write-SafeLog "Log file location: $logFile"
        
    } catch {
        Write-SafeLog "Error during enablement process: $_" "ERROR"
        Write-SafeLog "Stack trace: $($_.ScriptStackTrace)" "ERROR"
        throw
    }
}

# Function to disable remote access
function Disable-RemoteAccess {
    Write-SafeLog "=== STARTING REMOTE ACCESS DISABLEMENT ==="
    
    try {
        # Remove firewall rules
        Write-SafeLog "Removing firewall rules..."
        $rulesToRemove = Get-NetFirewallRule -DisplayName "$firewallRuleNamePrefix*" -ErrorAction SilentlyContinue
        if ($rulesToRemove) {
            foreach ($rule in $rulesToRemove) {
                Remove-NetFirewallRule -DisplayName $rule.DisplayName -ErrorAction SilentlyContinue
                Write-SafeLog "Removed firewall rule: $($rule.DisplayName)"
            }
        } else {
            Write-SafeLog "No firewall rules found to remove"
        }
        
        # Reset Trusted Hosts
        Write-SafeLog "Resetting trusted hosts..."
        
        if (Test-Path $trustedHostsBackupFile) {
            try {
                # Read the backup file content as a single string
                $backupContent = Get-Content $trustedHostsBackupFile -Raw
                if ([string]::IsNullOrWhiteSpace($backupContent)) {
                    $backupValue = ""
                } else {
                    $backupValue = $backupContent.Trim()
                }
                
                # Set the trusted hosts value (ensure it's a string)
                Set-Item WSMan:\localhost\Client\TrustedHosts -Value $backupValue -Force -Confirm:$false -ErrorAction Stop
                Write-SafeLog "Restored trusted hosts from backup: '$backupValue'"
                
                # Clean up backup file
                Remove-Item $trustedHostsBackupFile -Force -ErrorAction SilentlyContinue
            } catch {
                Write-SafeLog "Warning: Failed to restore trusted hosts from backup. Clearing instead." "WARNING"
                Set-Item WSMan:\localhost\Client\TrustedHosts -Value "" -Force -Confirm:$false -ErrorAction Stop
                Write-SafeLog "Cleared trusted hosts due to backup restoration failure"
            }
        } else {
            # No backup file exists, clear trusted hosts
            Set-Item WSMan:\localhost\Client\TrustedHosts -Value "" -Force -Confirm:$false -ErrorAction Stop
            Write-SafeLog "Cleared trusted hosts (no backup available)"
        }
        
        # Stop and set WinRM service to manual
        Write-SafeLog "Stopping WinRM service..."
        Stop-Service -Name $winrmServiceName -Force -ErrorAction SilentlyContinue
        Set-Service -Name $winrmServiceName -StartupType Manual -ErrorAction Stop
        
        # Clean up backup files older than 30 days
        Write-SafeLog "Cleaning up old backup files..."
        Get-ChildItem -Path $backupPath -Filter "*.json" -ErrorAction SilentlyContinue | 
            Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | 
            Remove-Item -Force -ErrorAction SilentlyContinue
        
        Write-SafeLog "=== REMOTE ACCESS DISABLED ==="
        Write-SafeLog "All temporary firewall rules have been removed"
        Write-SafeLog "Trusted hosts have been reset"
        Write-SafeLog "WinRM service has been stopped and set to manual startup"
        Write-SafeLog "Log file location: $logFile"
        
    } catch {
        Write-SafeLog "Error during disablement process: $_" "ERROR"
        Write-SafeLog "Stack trace: $($_.ScriptStackTrace)" "ERROR"
        throw
    }
}

# Main execution
try {
    Write-SafeLog "=== $scriptName Script Started ==="
    Write-SafeLog "Script path: $PSCommandPath"
    Write-SafeLog "Computer: $env:COMPUTERNAME"
    Write-SafeLog "User: $env:USERNAME"
    Write-SafeLog "PowerShell version: $($PSVersionTable.PSVersion)"
    Write-SafeLog "Running as Administrator: $(([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))"
    Write-SafeLog "Execution Policy: $(Get-ExecutionPolicy)"
    
    if ($Enable) {
        Enable-RemoteAccess
    }
    
    if ($Disable) {
        Disable-RemoteAccess
    }
    
    Write-SafeLog "=== SCRIPT COMPLETED SUCCESSFULLY ==="
    
    # Keep console window open if running interactively
    if ([Environment]::UserInteractive) {
        Write-Host "`nPress Enter to exit..." -ForegroundColor Cyan
        Read-Host | Out-Null
    }
    
} catch {
    Write-SafeLog "SCRIPT FATAL ERROR: $_" "ERROR"
    
    # Keep console window open if running interactively
    if ([Environment]::UserInteractive) {
        Write-Host "`nPress Enter to exit..." -ForegroundColor Red
        Read-Host | Out-Null
    }
    
    exit 1
}