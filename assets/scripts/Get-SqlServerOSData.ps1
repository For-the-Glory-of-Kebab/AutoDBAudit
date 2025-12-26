<#
.SYNOPSIS
    Collects SQL Server OS-level data for AutoDBAudit.

.DESCRIPTION
    Gathers data that cannot be obtained via T-SQL:
    - Client Protocols (TCP, Named Pipes, Shared Memory)
    - Service Accounts (actual account from WMI)
    - Service Status and Startup Type
    
    Self-elevates if not running as Administrator.

.PARAMETER InstanceName
    The SQL Server instance name. Use "MSSQLSERVER" for default instance.

.OUTPUTS
    JSON object with collected data.

.EXAMPLE
    .\Get-SqlServerOSData.ps1 -InstanceName "MSSQLSERVER"
#>

#Requires -Version 5.1
param(
    [Parameter(Mandatory)]
    [string]$InstanceName
)

# ============================================================================
# Self-Elevation Check
# ============================================================================
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
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
    $serviceFilter = if ($InstanceName -eq "MSSQLSERVER") {
        { $_.Name -eq "MSSQLSERVER" -or $_.Name -eq "SQLSERVERAGENT" -or $_.Name -like "*SQL*" }
    }
    else {
        { $_.Name -like "*$InstanceName*" -or $_.Name -like "*SQL*$InstanceName*" }
    }
    
    $services = Get-WmiObject Win32_Service | Where-Object $serviceFilter
    
    $result.data.services = $services | ForEach-Object {
        @{
            name         = $_.Name
            display_name = $_.DisplayName
            start_mode   = $_.StartMode
            state        = $_.State
            start_name   = $_.StartName  # Actual service account
            path         = $_.PathName
        }
    }
    
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
