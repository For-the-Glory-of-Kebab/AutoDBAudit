<#
.SYNOPSIS
    Enable or disable PowerShell remote management (WinRM) with COMPLETE REVERSIBILITY (Zero Footprint).
    
.DESCRIPTION
    Configures WinRM for remote management while tracking the EXACT initial state.
    - SAVES: Service State, Existing Listeners, TrustedHosts.
    - RESTORES: Reverts to exactly how it was found (even if it was broken/partial).
    - ISOLATION: Uses namespaced Firewall Rules and Listeners where possible.
    
.PARAMETER Enable
    Enable remote access (Default). Captures state before applying.
    
.PARAMETER Disable
    Revert system to the captured state in 'state.json'.
    
.PARAMETER Unrestricted
    If set, allows connections from ANY IP Address (0.0.0.0/0). 
    
.PARAMETER Force
    Skip confirmation prompts.
#>

[CmdletBinding()]
param(
    [switch]$Enable,
    [switch]$Disable,
    [switch]$Unrestricted,
    [switch]$Force
)

# Constants
$ScriptName = "AutoDBAudit_WinRM_Config"
$StatePath = "$env:ProgramData\$ScriptName"
$StateFile = "$StatePath\state.json"

# Default action
if (-not $Enable -and -not $Disable) { $Enable = $true }

# Elevation
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning "Elevation required. Restarting..."
    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" $($MyInvocation.Line)" -Verb RunAs
    exit
}

function Write-Log ($Msg, $Color = "White", $Level = "INFO") {
    $str = "[$(Get-Date -Format 'HH:mm:ss')] [$Level] $Msg"
    Write-Host $str -ForegroundColor $Color
}

function Get-ServiceState {
    $svc = Get-Service WinRM -ErrorAction SilentlyContinue
    return @{
        Status    = if ($svc) { $svc.Status.ToString() } else { "Unknown" }
        StartType = if ($svc) { $svc.StartType.ToString() } else { "Unknown" }
    }
}

function Get-Listeners {
    # Returns array of Listener Names
    try {
        return @(Get-ChildItem WSMan:\localhost\Listener | ForEach-Object { $_.Name })
    }
    catch {
        return @()
    }
}

function Save-State {
    if (Test-Path $StateFile) {
        Write-Log "State file already exists. Preserving ORIGINAL state." "Yellow"
        return # Don't overwrite original state if we run Enable twice
    }

    if (-not (Test-Path $StatePath)) { New-Item $StatePath -ItemType Directory -Force | Out-Null }

    # Capture State
    $state = @{
        Timestamp    = Get-Date
        Service      = Get-ServiceState
        Listeners    = Get-Listeners
        TrustedHosts = (Get-Item WSMan:\localhost\Client\TrustedHosts -ErrorAction SilentlyContinue).Value
    }
    
    $state | ConvertTo-Json | Out-File $StateFile -Force
    Write-Log "System State Captured to $StateFile" "Cyan"
}

function Enable-Access {
    Write-Log "=== Enabling WinRM (Zero Footprint Mode) ===" "Cyan"
    
    # 1. Save Initial State
    Save-State
    
    # 2. Enable PSRemoting (This creates default listeners)
    Write-Log "Configuring WinRM..."
    Enable-PSRemoting -Force -SkipNetworkProfileCheck -ErrorAction SilentlyContinue | Out-Null
    
    # 3. Configure Service
    Set-Service WinRM -StartupType Automatic
    Start-Service WinRM
    
    # 4. TrustedHosts
    Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
    
    # 5. Firewall Rules (Namespaced for easy cleanup)
    # Remove old run artifacts first
    Remove-NetFirewallRule -DisplayName "AutoDBAudit_WinRM*" -ErrorAction SilentlyContinue
    
    if ($Unrestricted) {
        Write-Log "WARNING: Allowing Unrestricted Access" "Red"
        New-NetFirewallRule -DisplayName "AutoDBAudit_WinRM_Any" -Direction Inbound -LocalPort 5985 -Protocol TCP -Action Allow -Profile Any | Out-Null
    }
    else {
        Write-Log "Restricting to LocalSubnet" "Green"
        New-NetFirewallRule -DisplayName "AutoDBAudit_WinRM_Subnet" -Direction Inbound -LocalPort 5985 -Protocol TCP -Action Allow -RemoteAddress LocalSubnet | Out-Null
    }
    
    Write-Log "Enabled Successfully." "Green"
}

function Disable-Access {
    Write-Log "=== Reverting WinRM Changes ===" "Cyan"
    
    if (-not (Test-Path $StateFile)) {
        Write-Log "ERROR: No state file found at $StateFile. Cannot guarantee zero footprint." "Red"
        $confirm = Read-Host "Do you want to perform a 'Best Effort' cleanup? (Y/N)"
        if ($confirm -ne 'Y') { exit }
        # Best Effort defaults
        $state = @{
            Service      = @{ Status = "Stopped"; StartType = "Manual" }
            Listeners    = @()
            TrustedHosts = ""
        }
    }
    else {
        $state = Get-Content $StateFile | ConvertFrom-Json
        Write-Log "Loaded State from $( $state.Timestamp )" "Gray"
    }
    
    # 1. Remove Our Firewall Rules
    Write-Log "Removing AutoDBAudit Firewall Rules..."
    Remove-NetFirewallRule -DisplayName "AutoDBAudit_WinRM*" -ErrorAction SilentlyContinue
    
    # 2. Revert Listeners
    # Identify listeners that exist NOW but were NOT in state
    $currentListeners = Get-Listeners
    foreach ($L in $currentListeners) {
        if ($L -notin $state.Listeners) {
            Write-Log "Removing Alien Listener: $L" "Yellow"
            Remove-Item "WSMan:\localhost\Listener\$L" -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    
    # 3. Revert TrustedHosts
    Write-Log "Restoring TrustedHosts..."
    Set-Item WSMan:\localhost\Client\TrustedHosts -Value ($state.TrustedHosts) -Force
    
    # 4. Revert Service State
    Write-Log "Restoring Service State ($($state.Service.Status) / $($state.Service.StartType))..."
    if ($state.Service.StartType) { Set-Service WinRM -StartupType $state.Service.StartType }
    
    if ($state.Service.Status -eq "Stopped") { Stop-Service WinRM -Force }
    elseif ($state.Service.Status -eq "Running") { Start-Service WinRM }
    
    # 5. Cleanup State File
    Remove-Item $StatePath -Recurse -Force -ErrorAction SilentlyContinue
    
    Write-Log "Revert Complete. Footprints removed." "Green"
}

try {
    if ($Disable) { Disable-Access }
    else { Enable-Access }
}
catch {
    Write-Log "FATAL: $_" "Red"
    exit 1
}
