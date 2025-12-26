<#
.SYNOPSIS
    Enables or disables a SQL Server client protocol.

.DESCRIPTION
    Modifies SQL Server client protocol settings in the registry:
    - TCP/IP
    - Named Pipes
    - Shared Memory
    - VIA (legacy)
    
    NOTE: SQL Server service restart is required for changes to take effect.

.PARAMETER InstanceName
    The SQL Server instance name. Use "MSSQLSERVER" for default instance.

.PARAMETER Protocol
    Protocol to modify: Tcp, Np, Sm, or Via

.PARAMETER Enabled
    $true to enable, $false to disable

.OUTPUTS
    JSON object with result.

.EXAMPLE
    .\Set-ClientProtocol.ps1 -InstanceName "MSSQLSERVER" -Protocol "Np" -Enabled $false
#>

#Requires -RunAsAdministrator
#Requires -Version 5.1
param(
    [Parameter(Mandatory)]
    [string]$InstanceName,
    
    [Parameter(Mandatory)]
    [ValidateSet("Tcp", "Np", "Sm", "Via")]
    [string]$Protocol,
    
    [Parameter(Mandatory)]
    [bool]$Enabled
)

$ErrorActionPreference = "Stop"
$result = @{
    success        = $false
    error          = $null
    previous_value = $null
    new_value      = $null
    protocol       = $Protocol
    instance       = $InstanceName
    note           = $null
}

try {
    # ========================================================================
    # Find Instance Registry Path
    # ========================================================================
    $regBase = "HKLM:\SOFTWARE\Microsoft\Microsoft SQL Server"
    $instanceKey = Get-ChildItem $regBase -ErrorAction Stop | Where-Object { 
        (Get-ItemProperty $_.PSPath -Name "" -ErrorAction SilentlyContinue)."(default)" -eq $InstanceName 
    }
    
    if (-not $instanceKey) {
        throw "Instance '$InstanceName' not found in registry"
    }
    
    $protocolPath = "$($instanceKey.PSPath)\MSSQLServer\SuperSocketNetLib\$Protocol"
    
    if (-not (Test-Path $protocolPath)) {
        throw "Protocol '$Protocol' path not found: $protocolPath"
    }
    
    # ========================================================================
    # Get Current Value
    # ========================================================================
    $result.previous_value = (Get-ItemProperty $protocolPath -Name "Enabled" -ErrorAction Stop).Enabled
    
    # ========================================================================
    # Set New Value
    # ========================================================================
    $enabledInt = if ($Enabled) { 1 } else { 0 }
    Set-ItemProperty $protocolPath -Name "Enabled" -Value $enabledInt -ErrorAction Stop
    
    # ========================================================================
    # Verify
    # ========================================================================
    $result.new_value = (Get-ItemProperty $protocolPath -Name "Enabled").Enabled
    $result.success = $true
    $result.note = "SQL Server service restart required for changes to take effect"
    
}
catch {
    $result.error = $_.Exception.Message
}

# ============================================================================
# Output JSON
# ============================================================================
$result | ConvertTo-Json -Depth 10
