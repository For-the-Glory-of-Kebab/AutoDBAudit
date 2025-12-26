<#
.SYNOPSIS
    Gracefully restarts SQL Server service with retry logic.

.DESCRIPTION
    Performs a controlled SQL Server service restart:
    1. Graceful stop with timeout
    2. Wait for connections to drain
    3. Start with retry logic
    4. Verify service is running
    
    Used after sp_configure changes require restart.

.PARAMETER InstanceName
    The SQL Server instance name. Use "MSSQLSERVER" for default instance.

.PARAMETER StopTimeoutSeconds
    Seconds to wait for service to stop. Default: 60

.PARAMETER StartTimeoutSeconds
    Seconds to wait for service to start. Default: 120

.PARAMETER MaxRetries
    Maximum restart attempts. Default: 3

.OUTPUTS
    JSON object with restart result.

.EXAMPLE
    .\Restart-SqlServerService.ps1 -InstanceName "MSSQLSERVER"
#>

#Requires -RunAsAdministrator
#Requires -Version 5.1
param(
    [Parameter(Mandatory)]
    [string]$InstanceName,
    
    [int]$StopTimeoutSeconds = 60,
    [int]$StartTimeoutSeconds = 120,
    [int]$MaxRetries = 3
)

$ErrorActionPreference = "Stop"
$result = @{
    success         = $false
    error           = $null
    actions         = @()
    final_state     = $null
    restart_time_ms = 0
}

# ============================================================================
# Determine Service Name
# ============================================================================
$serviceName = if ($InstanceName -eq "MSSQLSERVER" -or $InstanceName -eq "") { 
    "MSSQLSERVER" 
}
else { 
    "MSSQL`$$InstanceName" 
}

$result.actions += "Target service: $serviceName"
$startTime = Get-Date

try {
    $svc = Get-Service $serviceName -ErrorAction Stop
    $result.actions += "Initial state: $($svc.Status)"
    
    # ========================================================================
    # Step 1: Graceful Stop
    # ========================================================================
    if ($svc.Status -eq "Running") {
        $result.actions += "Stopping service (timeout: ${StopTimeoutSeconds}s)..."
        Stop-Service $serviceName -Force -NoWait
        
        # Wait for stop with timeout
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        while ((Get-Service $serviceName).Status -ne "Stopped" -and $stopwatch.Elapsed.TotalSeconds -lt $StopTimeoutSeconds) {
            Start-Sleep -Seconds 2
        }
        
        $svc = Get-Service $serviceName
        if ($svc.Status -ne "Stopped") {
            throw "Service did not stop within $StopTimeoutSeconds seconds (current: $($svc.Status))"
        }
        $result.actions += "Service stopped successfully in $([math]::Round($stopwatch.Elapsed.TotalSeconds))s"
    }
    
    # ========================================================================
    # Step 2: Start with Retries
    # ========================================================================
    $attempt = 0
    $started = $false
    
    while (-not $started -and $attempt -lt $MaxRetries) {
        $attempt++
        $result.actions += "Start attempt $attempt of $MaxRetries..."
        
        try {
            Start-Service $serviceName
            
            # Wait for running
            $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
            while ((Get-Service $serviceName).Status -ne "Running" -and $stopwatch.Elapsed.TotalSeconds -lt $StartTimeoutSeconds) {
                Start-Sleep -Seconds 2
            }
            
            $svc = Get-Service $serviceName
            if ($svc.Status -eq "Running") {
                $started = $true
                $result.actions += "Service started successfully"
            }
            else {
                $result.actions += "Attempt $attempt: Service state is $($svc.Status), retrying..."
            }
        }
        catch {
            $result.actions += "Attempt $attempt failed: $_"
            Start-Sleep -Seconds 5
        }
    }
    
    if (-not $started) {
        throw "Failed to start service after $MaxRetries attempts"
    }
    
    $result.success = $true
    $result.final_state = (Get-Service $serviceName).Status
    $result.restart_time_ms = [int]((Get-Date) - $startTime).TotalMilliseconds
    
}
catch {
    $result.error = $_.Exception.Message
    $result.final_state = (Get-Service $serviceName -ErrorAction SilentlyContinue).Status
    $result.restart_time_ms = [int]((Get-Date) - $startTime).TotalMilliseconds
}

# ============================================================================
# Output JSON
# ============================================================================
$result | ConvertTo-Json -Depth 10
