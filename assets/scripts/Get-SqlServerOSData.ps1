<#
.SYNOPSIS
    Collects SQL Server OS-level data for AutoDBAudit.

.DESCRIPTION
    Gathers data that cannot be obtained via T-SQL:
    - Client Protocols (TCP, Named Pipes, Shared Memory)
    - Service Accounts (actual account from WMI)
    - Service Status and Startup Type
    
    Self-elevates if not running as Administrator (skipped when remote).

.PARAMETER InstanceName
    The SQL Server instance name. Use "MSSQLSERVER" for default instance.

.OUTPUTS
    JSON object with collected data.

.EXAMPLE
    .\Get-SqlServerOSData.ps1 -InstanceName "MSSQLSERVER"
#>

#Requires -Version 2.0
param(
    [Parameter(Mandatory = $true)]
    [string]$InstanceName
)

# ============================================================================
# Self-Elevation Check (Skip if running via WinRM/PSRemoting)
# ============================================================================
$isRemote = $env:WINRM_SHELL_ID -or $PSVersionTable.PSEdition -eq 'Core' -or [bool]$Host.Runspace.ConnectionInfo
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin -and -not $isRemote) {
    Write-Warning "Script requires elevation - attempting elevation"
    $elevationArgs = "-ExecutionPolicy Bypass -File `"$PSCommandPath`" -InstanceName $InstanceName"
    Start-Process powershell -Verb RunAs -ArgumentList $elevationArgs -Wait
    exit
}

# ============================================================================
# Initialize Result Object
# ============================================================================
$ErrorActionPreference = "Stop"
$result = @{
    success       = $false
    error         = $null
    data          = @{
        client_protocols    = @{}
        services            = @()
        audit_policy_sample = ""
    }
    collected_at  = (Get-Date).ToString("o")
    instance_name = $InstanceName
}

try {
    # ========================================================================
    # 1. Client Protocols from Registry
    # ========================================================================
    $regBase = "HKLM:\SOFTWARE\Microsoft\Microsoft SQL Server"
    $instanceKey = Get-ChildItem $regBase -ErrorAction SilentlyContinue | Where-Object { 
        (Get-ItemProperty $_.PSPath -Name "" -ErrorAction SilentlyContinue)."(default)" -eq $InstanceName 
    }
    
    if ($instanceKey) {
        $netLibPath = "$($instanceKey.PSPath)\MSSQLServer\SuperSocketNetLib"
        
        if (Test-Path $netLibPath) {
            # TCP/IP
            $tcpPath = "$netLibPath\Tcp"
            if (Test-Path $tcpPath) {
                $result.data.client_protocols.tcp_enabled = (Get-ItemProperty $tcpPath -ErrorAction SilentlyContinue).Enabled
            }
            
            # Named Pipes
            $npPath = "$netLibPath\Np"
            if (Test-Path $npPath) {
                $result.data.client_protocols.np_enabled = (Get-ItemProperty $npPath -ErrorAction SilentlyContinue).Enabled
            }
            
            # Shared Memory
            $smPath = "$netLibPath\Sm"
            if (Test-Path $smPath) {
                $result.data.client_protocols.sm_enabled = (Get-ItemProperty $smPath -ErrorAction SilentlyContinue).Enabled
            }
            
            # VIA (legacy)
            $viaPath = "$netLibPath\Via"
            if (Test-Path $viaPath) {
                $result.data.client_protocols.via_enabled = (Get-ItemProperty $viaPath -ErrorAction SilentlyContinue).Enabled
            }
        }
    }
    else {
        $result.data.client_protocols.warning = "Instance registry key not found"
    }
    
    # ========================================================================
    # 2. Service Accounts via WMI
    # ========================================================================
    # Get ALL services first, then filter (script blocks don't survive minification)
    $allServices = Get-WmiObject Win32_Service -ErrorAction SilentlyContinue
    
    # Filter to SQL-related services using string matching
    $sqlServices = @()
    foreach ($svc in $allServices) {
        $name = $svc.Name
        $dispName = $svc.DisplayName
        if ($name -like "*SQL*" -or $name -like "*MSSQL*" -or $name -like "*ReportServer*" -or 
            $name -like "*MsDts*" -or $name -like "*Launchpad*" -or $dispName -like "*SQL Server*") {
            $sqlServices += @{
                name         = $svc.Name
                display_name = $svc.DisplayName
                start_mode   = $svc.StartMode
                state        = $svc.State
                start_name   = $svc.StartName
                path         = $svc.PathName
            }
        }
    }
    
    $result.data.services = $sqlServices
    
    # ========================================================================
    # 3. OS Audit Policy Sample
    # ========================================================================
    try {
        $auditOutput = & auditpol /get /category:"Logon/Logoff" 2>&1
        $result.data.audit_policy_sample = ($auditOutput -join "`n")
    }
    catch {
        $result.data.audit_policy_sample = "Failed to retrieve: $_"
    }
    
    $result.success = $true
    
}
catch {
    $result.error = $_.Exception.Message
}

# ============================================================================
# Output JSON
# ============================================================================
$result | ConvertTo-Json -Depth 10
