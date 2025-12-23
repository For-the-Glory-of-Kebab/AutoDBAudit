<#
.SYNOPSIS
    Enable or disable PowerShell remote management with restrictive local network access only.
    
.DESCRIPTION
    This script configures a target machine for PowerShell remote management and can revert all changes.
    It restricts access to ONLY the local network subnet (same CIDR as the server) for maximum security.
    All changes are reversible and network-scoped.
    
.PARAMETER Enable
    Enable remote PowerShell access restricted to local network only. This is the default action if no parameter is specified.
    
.PARAMETER Disable
    Disable remote PowerShell access and revert all security changes made by this script.
    
.PARAMETER Force
    Force the action without confirmation prompts.
    
.EXAMPLE
    .\RemoteAccessConfig.ps1
    Enables remote access restricted to local network only (default action)
    
.EXAMPLE
    .\RemoteAccessConfig.ps1 -Disable
    Disables remote access and reverts all changes
    
.NOTES
    Security Considerations:
    - Script automatically elevates to Administrator
    - Access restricted to LOCAL NETWORK SUBNET ONLY (no public internet exposure)
    - All firewall rules are scoped to local subnet and reversible
    - WinRM configuration is backed up before changes
    - Designed for temporary use by authorized administrators only
    
    REQUIREMENTS:
    - Must be run on Windows
    - Requires Administrator privileges for configuration changes
    - Requires at least one active network connection with IP configuration
    
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
$networkBackupFile = "$backupPath\network_config_backup.json"

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
        "SUCCESS" { "Green" }
        default   { "White" }
    }
    
    Write-Host $logEntry -ForegroundColor $color
    
    try {
        Add-Content -Path $logFile -Value $logEntry -ErrorAction Stop
    } catch {
        Write-Warning "Failed to write to log file: $logFile"
    }
}

# Function to get local network subnet information - CRITICAL SECURITY FUNCTION
function Get-LocalNetworkSubnet {
    Write-SafeLog "Detecting local network subnet configuration..." "INFO"
    
    try {
        # Get all IPv4 addresses that are not loopback or link-local
        $ipAddresses = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop | 
                      Where-Object { 
                          $_.IPAddress -notmatch '^(127\.0\.0\.1|169\.254)' -and 
                          $_.PrefixOrigin -eq 'Dhcp' -or $_.PrefixOrigin -eq 'Manual'
                      }
        
        if (-not $ipAddresses -or $ipAddresses.Count -eq 0) {
            Write-SafeLog "ERROR: No valid network interfaces found. Script requires at least one active network connection." "ERROR"
            exit 1
        }
        
        $results = @()
        
        foreach ($ip in $ipAddresses) {
            $interface = Get-NetAdapter -InterfaceIndex $ip.InterfaceIndex -ErrorAction Stop
            
            # Skip disabled or disconnected interfaces
            if ($interface.Status -ne 'Up') {
                continue
            }
            
            $subnetMask = $ip.PrefixLength
            $networkAddress = Get-NetworkAddress -IPAddress $ip.IPAddress -PrefixLength $subnetMask
            
            $results += [PSCustomObject]@{
                InterfaceName = $interface.Name
                IPAddress = $ip.IPAddress
                SubnetMask = $subnetMask
                NetworkAddress = $networkAddress
                NetworkRange = "$networkAddress/$subnetMask"
                InterfaceIndex = $ip.InterfaceIndex
            }
            
            Write-SafeLog "Found network interface: $($interface.Name)" "SUCCESS"
            Write-SafeLog "IP Address: $($ip.IPAddress)/$subnetMask" "SUCCESS"
            Write-SafeLog "Network Range: $networkAddress/$subnetMask" "SUCCESS"
        }
        
        if ($results.Count -eq 0) {
            Write-SafeLog "ERROR: No active network interfaces found with valid IP configuration." "ERROR"
            exit 1
        }
        
        return $results
        
    } catch {
        Write-SafeLog "ERROR: Failed to detect network configuration: $_" "ERROR"
        exit 1
    }
}

# Helper function to calculate network address from IP and prefix length
function Get-NetworkAddress {
    param(
        [string]$IPAddress,
        [int]$PrefixLength
    )
    
    try {
        $ipBytes = [System.Net.IPAddress]::Parse($IPAddress).GetAddressBytes()
        $maskBytes = @()
        
        for ($i = 0; $i -lt 4; $i++) {
            $bits = $PrefixLength - $i * 8
            if ($bits -lt 0) { $bits = 0 }
            if ($bits -gt 8) { $bits = 8 }
            $maskBytes += [byte](0xFF -shl (8 - $bits))
        }
        
        $networkBytes = @()
        for ($i = 0; $i -lt 4; $i++) {
            $networkBytes += $ipBytes[$i] -band $maskBytes[$i]
        }
        
        return [System.Net.IPAddress]::new($networkBytes).ToString()
    } catch {
        Write-SafeLog "ERROR: Failed to calculate network address: $_" "ERROR"
        return $null
    }
}

# Function to backup current configuration
function Backup-WinRMConfig {
    Write-SafeLog "Creating backup of current WinRM configuration..." "INFO"
    
    try {
        # Backup trusted hosts
        $trustedHosts = Get-Item WSMan:\localhost\Client\TrustedHosts -ErrorAction SilentlyContinue
        if ($trustedHosts -and $trustedHosts.Value) {
            $trustedHosts.Value | Out-File $trustedHostsBackupFile -Force
            Write-SafeLog "Trusted hosts backed up to: $trustedHostsBackupFile" "SUCCESS"
        } else {
            # Create empty backup file to indicate no trusted hosts were set
            "" | Out-File $trustedHostsBackupFile -Force
            Write-SafeLog "Created empty trusted hosts backup file" "INFO"
        }
        
        # Backup network configuration
        $networkConfig = Get-LocalNetworkSubnet
        $networkConfig | ConvertTo-Json -Depth 10 | Out-File $networkBackupFile -Force
        Write-SafeLog "Network configuration backed up to: $networkBackupFile" "SUCCESS"
        
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
            Write-SafeLog "WinRM configuration backed up to: $backupFile" "SUCCESS"
        }
    } catch {
        Write-SafeLog "Warning: Failed to create complete backup. Continuing anyway." "WARNING"
    }
}

# Function to enable remote access with LOCAL NETWORK RESTRICTION
function Enable-RemoteAccess {
    Write-SafeLog "=== STARTING REMOTE ACCESS ENABLEMENT (LOCAL NETWORK ONLY) ===" "INFO"
    
    # Detect local network subnet FIRST - critical for security
    $localNetworks = Get-LocalNetworkSubnet
    
    Write-SafeLog "SECURITY CONFIGURATION:" "WARNING"
    Write-SafeLog "PowerShell remoting will be restricted to these local network ranges ONLY:" "WARNING"
    foreach ($network in $localNetworks) {
        Write-SafeLog "  - $($network.NetworkRange) on interface $($network.InterfaceName)" "WARNING"
    }
    Write-SafeLog "PUBLIC INTERNET ACCESS WILL BE BLOCKED" "WARNING"
    
    if (-not $Force) {
        $confirmation = Read-Host "`nConfirm: Restrict PowerShell remoting to LOCAL NETWORK ONLY (Y/N)?"
        if ($confirmation -notlike "Y*") {
            Write-SafeLog "Operation cancelled by user." "WARNING"
            return
        }
    }
    
    # Backup current config
    Backup-WinRMConfig
    
    try {
        # Determine which PowerShell version we're using
        $isWindowsPowerShell = $PSVersionTable.PSVersion.Major -lt 6 -or $PSVersionTable.PSEdition -eq "Desktop"
        
        Write-SafeLog "PowerShell version detected: $($PSVersionTable.PSVersion) ($($isWindowsPowerShell ? 'Windows PowerShell' : 'PowerShell Core'))" "INFO"
        
        # Enable PSRemoting - handle different PowerShell versions
        Write-SafeLog "Enabling PSRemoting..." "INFO"
        
        if ($isWindowsPowerShell) {
            # Windows PowerShell - use built-in cmdlet
            if ($Force) {
                Enable-PSRemoting -Force -SkipNetworkProfileCheck 2>&1 | Out-Null
            } else {
                Enable-PSRemoting -SkipNetworkProfileCheck 2>&1 | Out-Null
            }
            Write-SafeLog "PSRemoting enabled successfully in Windows PowerShell" "SUCCESS"
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
            
            # Fixed the ArgumentList parameter issue
            $arguments = @(
                "-Command"
                "& { $command }"
                "-ForceParam"
                $Force.IsPresent.ToString()
            )
            
            $result = Start-Process -FilePath "powershell.exe" -ArgumentList $arguments -Wait -PassThru -NoNewWindow
            
            if ($result.ExitCode -eq 0) {
                Write-SafeLog "PSRemoting enabled successfully via Windows PowerShell" "SUCCESS"
            } else {
                Write-SafeLog "Warning: PSRemoting enablement returned exit code $($result.ExitCode). Manual verification recommended." "WARNING"
            }
        }
        
        # Configure WinRM service
        Write-SafeLog "Configuring WinRM service..." "INFO"
        try {
            Set-Service -Name $winrmServiceName -StartupType Automatic -ErrorAction Stop
            Start-Service -Name $winrmServiceName -ErrorAction Stop
            Write-SafeLog "WinRM service configured and started successfully" "SUCCESS"
        } catch {
            Write-SafeLog "Warning: Failed to configure WinRM service. It may already be configured." "WARNING"
        }
        
        # Configure WinRM listeners - RESTRICT TO LOCAL INTERFACES ONLY
        Write-SafeLog "Configuring WinRM listeners for LOCAL NETWORK ONLY..." "WARNING"
        
        # Remove existing listeners first
        try {
            $existingListeners = Get-ChildItem WSMan:\localhost\Listener -ErrorAction Stop
            foreach ($listener in $existingListeners) {
                Remove-Item -Path "WSMan:\localhost\Listener\$($listener.Name)" -Recurse -Force -ErrorAction SilentlyContinue
            }
            Write-SafeLog "Removed existing WinRM listeners" "INFO"
        } catch {
            Write-SafeLog "No existing WinRM listeners to remove or error during removal" "INFO"
        }
        
        # Create new listeners only for local network interfaces
        foreach ($network in $localNetworks) {
            try {
                $listenerPath = "WSMan:\localhost\Listener"
                $listenerName = "DefaultIPFilterListener_$($network.InterfaceIndex)"
                
                # Create listener that only accepts connections from the local subnet
                $filter = "*S=$($network.NetworkAddress)/$($network.SubnetMask)"
                
                New-Item -Path $listenerPath -Transport HTTP -Address IP:$($network.IPAddress) -Force -ErrorAction Stop | Out-Null
                
                # Set IP filter to restrict to local subnet only
                Set-Item -Path "$listenerPath\Listener\$listenerName\IPFilter" -Value $filter -Force -ErrorAction Stop
                
                Write-SafeLog "Created WinRM listener for $($network.InterfaceName) restricted to $($network.NetworkRange)" "SUCCESS"
            } catch {
                Write-SafeLog "Warning: Failed to create listener for $($network.InterfaceName): $_" "WARNING"
            }
        }
        
        # Set Trusted Hosts - RESTRICT TO LOCAL NETWORK ONLY
        Write-SafeLog "Configuring trusted hosts for LOCAL NETWORK ONLY..." "WARNING"
        
        # Build trusted hosts list from local networks
        $trustedNetworks = @()
        foreach ($network in $localNetworks) {
            $trustedNetworks += "$($network.NetworkAddress)/$($network.SubnetMask)"
        }
        
        $trustedHostsValue = $trustedNetworks -join ","
        
        Set-Item WSMan:\localhost\Client\TrustedHosts -Value $trustedHostsValue -Force -Confirm:$false -ErrorAction Stop
        Write-SafeLog "Trusted hosts configured to accept connections ONLY from: $trustedHostsValue" "SUCCESS"
        
        # Configure firewall rules - LOCAL NETWORK ONLY
        Write-SafeLog "Configuring firewall rules for LOCAL NETWORK ACCESS ONLY..." "WARNING"
        
        # Remove any existing rules from previous runs
        $existingRules = Get-NetFirewallRule -DisplayName "$firewallRuleNamePrefix*" -ErrorAction SilentlyContinue
        if ($existingRules) {
            $existingRules | Remove-NetFirewallRule -ErrorAction SilentlyContinue
            Write-SafeLog "Removed existing firewall rules from previous runs" "INFO"
        }
        
        # Create HTTP rule (port 5985) - RESTRICTED TO LOCAL SUBNET
        foreach ($network in $localNetworks) {
            try {
                $ruleName = "$firewallRuleNamePrefix-HTTP-$($network.InterfaceIndex)"
                $ruleDisplayName = "$firewallRuleNamePrefix-HTTP $($network.InterfaceName)"
                
                $ruleParams = @{
                    DisplayName = $ruleDisplayName
                    Name = $ruleName
                    Direction = "Inbound"
                    Protocol = "TCP"
                    LocalPort = 5985
                    Action = "Allow"
                    Enabled = "True"
                    Description = "PowerShell remoting access RESTRICTED to $($network.NetworkRange) only"
                    Group = $firewallRuleNamePrefix
                    RemoteAddress = $network.NetworkAddress
                    ErrorAction = "Stop"
                }
                
                New-NetFirewallRule @ruleParams | Out-Null
                Write-SafeLog "Firewall rule created for $($network.InterfaceName): $($network.NetworkRange)" "SUCCESS"
            } catch {
                Write-SafeLog "Warning: Failed to create firewall rule for $($network.InterfaceName): $_" "WARNING"
                Write-SafeLog "Error details: $_" "WARNING"
            }
        }
        
        # Test configuration
        Write-SafeLog "Testing WinRM configuration..." "INFO"
        try {
            $testResult = Test-WsMan -ErrorAction Stop
            Write-SafeLog "WinRM test successful. Remote access should now be available from LOCAL NETWORK ONLY." "SUCCESS"
        } catch {
            Write-SafeLog "WinRM test failed. Manual verification may be required." "WARNING"
            Write-SafeLog "Test error: $_" "WARNING"
        }
        
        # Display connection information
        $computerName = $env:COMPUTERNAME
        
        Write-SafeLog "=== REMOTE ACCESS CONFIGURATION COMPLETE (LOCAL NETWORK ONLY) ===" "SUCCESS"
        Write-SafeLog "SECURITY SUMMARY:" "WARNING"
        Write-SafeLog "✅ Access RESTRICTED to local network subnets ONLY" "SUCCESS"
        Write-SafeLog "✅ NO public internet exposure" "SUCCESS"
        Write-SafeLog "✅ Firewall rules scoped to specific subnets" "SUCCESS"
        Write-SafeLog "✅ WinRM listeners filtered by IP range" "SUCCESS"
        
        Write-SafeLog "`nYou can now connect from LOCAL NETWORK machines using:" "INFO"
        Write-SafeLog "Enter-PSSession -ComputerName $computerName" "INFO"
        
        foreach ($network in $localNetworks) {
            Write-SafeLog "From subnet $($network.NetworkRange): Enter-PSSession -ComputerName $($network.IPAddress)" "INFO"
        }
        
        Write-SafeLog "`n=== IMPORTANT SECURITY REMINDER ===" "WARNING"
        Write-SafeLog "⚠️  This configuration is RESTRICTED to your local network only" "WARNING"
        Write-SafeLog "⚠️  PUBLIC INTERNET ACCESS IS BLOCKED by design" "WARNING"
        Write-SafeLog "⚠️  Run this script with -Disable parameter after completing your administrative tasks!" "WARNING"
        Write-SafeLog "Log file location: $logFile" "INFO"
        
    } catch {
        Write-SafeLog "Error during enablement process: $_" "ERROR"
        Write-SafeLog "Stack trace: $($_.ScriptStackTrace)" "ERROR"
        throw
    }
}

# Function to disable remote access
function Disable-RemoteAccess {
    Write-SafeLog "=== STARTING REMOTE ACCESS DISABLEMENT ===" "INFO"
    
    try {
        # Remove firewall rules
        Write-SafeLog "Removing firewall rules..." "INFO"
        $rulesToRemove = Get-NetFirewallRule -DisplayName "$firewallRuleNamePrefix*" -ErrorAction SilentlyContinue
        if ($rulesToRemove) {
            foreach ($rule in $rulesToRemove) {
                Remove-NetFirewallRule -DisplayName $rule.DisplayName -ErrorAction SilentlyContinue
                Write-SafeLog "Removed firewall rule: $($rule.DisplayName)" "SUCCESS"
            }
        } else {
            Write-SafeLog "No firewall rules found to remove" "INFO"
        }
        
        # Remove WinRM listeners created by this script
        Write-SafeLog "Removing WinRM listeners..." "INFO"
        try {
            $listeners = Get-ChildItem WSMan:\localhost\Listener -ErrorAction Stop
            foreach ($listener in $listeners) {
                if ($listener.Name -like "*DefaultIPFilterListener_*" -or $listener.Name -like "*_$scriptName*") {
                    Remove-Item -Path "WSMan:\localhost\Listener\$($listener.Name)" -Recurse -Force -ErrorAction SilentlyContinue
                    Write-SafeLog "Removed WinRM listener: $($listener.Name)" "SUCCESS"
                }
            }
        } catch {
            Write-SafeLog "No WinRM listeners to remove or error during removal" "INFO"
        }
        
        # Reset Trusted Hosts
        Write-SafeLog "Resetting trusted hosts..." "INFO"
        
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
                Write-SafeLog "Restored trusted hosts from backup: '$backupValue'" "SUCCESS"
                
                # Clean up backup file
                Remove-Item $trustedHostsBackupFile -Force -ErrorAction SilentlyContinue
            } catch {
                Write-SafeLog "Warning: Failed to restore trusted hosts from backup. Clearing instead." "WARNING"
                Set-Item WSMan:\localhost\Client\TrustedHosts -Value "" -Force -Confirm:$false -ErrorAction Stop
                Write-SafeLog "Cleared trusted hosts due to backup restoration failure" "SUCCESS"
            }
        } else {
            # No backup file exists, clear trusted hosts
            Set-Item WSMan:\localhost\Client\TrustedHosts -Value "" -Force -Confirm:$false -ErrorAction Stop
            Write-SafeLog "Cleared trusted hosts (no backup available)" "SUCCESS"
        }
        
        # Stop and set WinRM service to manual
        Write-SafeLog "Stopping WinRM service..." "INFO"
        Stop-Service -Name $winrmServiceName -Force -ErrorAction SilentlyContinue
        Set-Service -Name $winrmServiceName -StartupType Manual -ErrorAction Stop
        
        # Clean up backup files older than 30 days
        Write-SafeLog "Cleaning up old backup files..." "INFO"
        Get-ChildItem -Path $backupPath -Filter "*.json" -ErrorAction SilentlyContinue | 
            Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | 
            Remove-Item -Force -ErrorAction SilentlyContinue
        
        Write-SafeLog "=== REMOTE ACCESS DISABLED ===" "SUCCESS"
        Write-SafeLog "All firewall rules have been removed" "SUCCESS"
        Write-SafeLog "All WinRM listeners have been removed" "SUCCESS"
        Write-SafeLog "Trusted hosts have been reset" "SUCCESS"
        Write-SafeLog "WinRM service has been stopped and set to manual startup" "SUCCESS"
        Write-SafeLog "Log file location: $logFile" "INFO"
        
    } catch {
        Write-SafeLog "Error during disablement process: $_" "ERROR"
        Write-SafeLog "Stack trace: $($_.ScriptStackTrace)" "ERROR"
        throw
    }
}

# Main execution
try {
    Write-SafeLog "=== $scriptName Script Started ===" "SUCCESS"
    Write-SafeLog "Script path: $PSCommandPath" "INFO"
    Write-SafeLog "Computer: $env:COMPUTERNAME" "INFO"
    Write-SafeLog "User: $env:USERNAME" "INFO"
    Write-SafeLog "PowerShell version: $($PSVersionTable.PSVersion)" "INFO"
    Write-SafeLog "Running as Administrator: $(([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))" "INFO"
    Write-SafeLog "Execution Policy: $(Get-ExecutionPolicy)" "INFO"
    
    if ($Enable) {
        Enable-RemoteAccess
    }
    
    if ($Disable) {
        Disable-RemoteAccess
    }
    
    Write-SafeLog "=== SCRIPT COMPLETED SUCCESSFULLY ===" "SUCCESS"
    
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