<#
.SYNOPSIS
    Smart Bootstrap & Diagnostic tool for Enabling/Disabling Remote Access on generic Windows targets.
    
.DESCRIPTION
    Automates the deployment of 'Enable-WinRM.ps1' to remote machines without existing PSRemote access.
    
    Logic Flow:
    1. CHECKS if PSRemote is already working.
    2. IF NOT, checks if SMB (445) & RPC (135) are open.
    3. IF OPEN, performs "Agentless" Bootstrap:
       - Copies 'Enable-WinRM.ps1' to Target (C:\Windows\Temp).
       - Executes it via WMI (Win32_Process) with -ExecutionPolicy Bypass.
    4. IF BLOCKED, Reports failure and provides Manual RDP instructions.
    
    Reversibility (Cleanup):
    - Run with -Action Disable to execute the Revert logic on the target and delete the payload.
    
.PARAMETER Target
    Hostname or IP of the remote machine.
    
.PARAMETER Credential
    Domain credentials with Local Admin rights on Target.
    
.PARAMETER Action
    'Enable' (Default) or 'Disable'.
    
.EXAMPLE
    .\Bootstrap-WinRM.ps1 -Target 10.10.0.20 -Credential (Get-Credential)
    Checks status and enables WinRM if needed.
    
.EXAMPLE
    .\Bootstrap-WinRM.ps1 -Target 10.10.0.20 -Action Disable
    Reverts all changes on the target and removes the script.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Target,
    
    [System.Management.Automation.PSCredential]$Credential,
    
    [ValidateSet("Enable", "Disable")]
    [string]$Action = "Enable"
)

# Paths
$SourceScript = "$PSScriptRoot\CreateAccess\Enable-WinRM.ps1"
if (-not (Test-Path $SourceScript)) { Write-Error "Payload 'Enable-WinRM.ps1' not found at $SourceScript"; exit 1 }

$RemotePath = "\\$Target\C$\Windows\Temp\AutoDBAudit_Enable-WinRM.ps1"
$LocalExecPath = "C:\Windows\Temp\AutoDBAudit_Enable-WinRM.ps1"

function Write-Log ($Msg, $Color = "White", $Level = "INFO") {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] [$Level] $Msg" -ForegroundColor $Color
}

function Test-Port ($Port) {
    $t = Test-NetConnection -ComputerName $Target -Port $Port -WarningAction SilentlyContinue
    return $t.TcpTestSucceeded
}

# 1. Connectivity Check
Write-Log "Checking Connectivity to $Target..." "Cyan"

$WinRM_Open = Test-Port 5985
$SMB_Open = Test-Port 445
$RPC_Open = Test-Port 135

Write-Log "  TCP 5985 (WinRM): $(if ($WinRM_Open){'OPEN'}else{'CLOSED'})" $(if ($WinRM_Open) { 'Green' }else { 'Yellow' })
Write-Log "  TCP 445  (SMB):   $(if ($SMB_Open){'OPEN'}else{'CLOSED'})" $(if ($SMB_Open) { 'Green' }else { 'Red' })

# 2. Logic Controller
if ($Action -eq "Enable") {
    
    # CASE A: Already Enabled?
    if ($WinRM_Open) {
        Write-Log "WinRM Port is OPEN. Attempting Test-WSMan..."
        try {
            $test = Test-WSMan -ComputerName $Target -Credential $Credential -ErrorAction Stop
            Write-Log "SUCCESS: PSRemote is already active (Protocol: $($test.ProductVersion))." "Green"
            Write-Log "You can use standard scripts." "Green"
            return
        }
        catch {
            Write-Log "WARNING: Port 5985 is open but Test-WSMan failed. Auth or Config issue." "Yellow"
            # Fallthrough to bootstrap to try and fix it?
        }
    }

    # CASE B: Agentless Bootstrap (Needs SMB/RPC)
    if ($SMB_Open -and $RPC_Open) {
        Write-Log "Attempting Agentless Bootstrap (WMI/SMB)..." "Cyan"
        
        try {
            # 1. Map Temp Drive (UNC + Credentials)
            $DriveName = "AutoDBAudit_Bootstrap_$(Get-Random)"
            $RootUNC = "\\$Target\C$"
            
            Write-Log "  Mapping temp drive $DriveName to $RootUNC..."
            New-PSDrive -Name $DriveName -PSProvider FileSystem -Root $RootUNC -Credential $Credential -ErrorAction Stop | Out-Null
            
            try {
                # 2. Copy Payload
                $DestOnDrive = "$($DriveName):\Windows\Temp\AutoDBAudit_Enable-WinRM.ps1"
                Write-Log "  Copying payload to $DestOnDrive..."
                Copy-Item -Path $SourceScript -Destination $DestOnDrive -Force -ErrorAction Stop
            }
            finally {
                # 3. Cleanup Drive
                Remove-PSDrive -Name $DriveName -ErrorAction SilentlyContinue
            }
            
            # 4. Execute via WMI (Force DCOM since WinRM is flaky)
            Write-Log "  Executing Payload via WMI (DCOM)..."
            $cmd = "powershell.exe -ExecutionPolicy Bypass -File `"$LocalExecPath`""
            
            $SessionOption = New-CimSessionOption -Protocol DCOM
            $CimSession = New-CimSession -ComputerName $Target -Credential $Credential -SessionOption $SessionOption -ErrorAction Stop
            
            try {
                Invoke-CimMethod -CimSession $CimSession -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $cmd } -ErrorAction Stop | Out-Null
            }
            finally {
                Remove-CimSession -CimSession $CimSession -ErrorAction SilentlyContinue
            }
            
            Write-Log "  Command Sent. Waiting for Service Start (15s)..."
            Start-Sleep -Seconds 15
            
            # 5. Verify
            $New_WinRM = Test-Port 5985
            if ($New_WinRM) {
                Write-Log "SUCCESS: WinRM Port is now OPEN." "Green"
                Write-Log "State has been tracked on remote machine for Zero-Footprint Revert." "Gray"
            }
            else {
                Write-Log "FAILURE: Port 5985 remains closed after bootstrap attempt." "Red"
                Write-Log "Possible causes: GPO Block, Advanced Firewall Block, or WMI exec failure." "Red"
            }
        }
        catch {
            Write-Log "BOOTSTRAP FAILED: $_" "Red"
            Write-Log "Note: File copy requires Admin Share (ADMIN$) access." "Yellow"
        }
    }
    else {
        # CASE C: Manual RDP Required
        Write-Log "❌ BOOTSTRAP UNAVAILABLE" "Red"
        Write-Log "Reasons:" "Red"
        if (-not $SMB_Open) { Write-Log "  - SMB (Port 445) is BLOCKED. Cannot copy payload." "Yellow" }
        if (-not $RPC_Open) { Write-Log "  - RPC (Port 135) is BLOCKED. Cannot execute remotely." "Yellow" }
        
        Write-Log "`n=== MANUAL INSTRUCTIONS ===" "White"
        Write-Log "1. RDP to $Target" "White"
        Write-Log "2. Copy 'Enable-WinRM.ps1' to the server." "White"
        Write-Log "3. Run PowerShell as Admin: .\Enable-WinRM.ps1" "White"
        Write-Log "4. To Revert later: .\Enable-WinRM.ps1 -Disable" "White"
    }

}
elseif ($Action -eq "Disable") {
    
    Write-Log "Attempting Remote Cleanup/Revert..." "Cyan"
    
    # Try via PSRemote first (cleanest)
    if ($WinRM_Open) {
        try {
            Write-Log "  Sending Revert command via PSRemote..."
            Invoke-Command -ComputerName $Target -Credential $Credential -ScriptBlock {
                param($Path)
                if (Test-Path $Path) {
                    Write-Host "Reverting..."
                    & $Path -Disable
                }
                else {
                    Write-Error "Payload not found at $Path"
                }
            } -ArgumentList $LocalExecPath -ErrorAction Stop
            
            Write-Log "  Command executed." "Green"
        }
        catch {
            Write-Log "  PSRemote Failed ($($_)). Falling back to WMI..." "Yellow"
            $WinRM_Open = $false # Force fallback
        }
    }
    
    if (-not $WinRM_Open -and $SMB_Open) {
        # WMI Fallback for Disable
        Write-Log "  Executing Revert via WMI (DCOM)..."
        $cmd = "powershell.exe -ExecutionPolicy Bypass -File `"$LocalExecPath`" -Disable"
        
        $SessionOption = New-CimSessionOption -Protocol DCOM
        $CimSession = New-CimSession -ComputerName $Target -Credential $Credential -SessionOption $SessionOption -ErrorAction SilentlyContinue
        
        if ($CimSession) {
            try {
                Invoke-CimMethod -CimSession $CimSession -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $cmd } -ErrorAction Stop | Out-Null
                Write-Log "  Revert command sent via WMI." "Green"
            }
            catch {
                Write-Log "  WMI Execution failed: $_" "Red"
            }
            finally {
                Remove-CimSession -CimSession $CimSession -ErrorAction SilentlyContinue
            }
        }
        else {
            Write-Log "  Could not create DCOM Session for WMI execution." "Red"
        }
    }
    
    # Cleanup Payload File
    if ($SMB_Open) {
        Write-Log "  Cleaning up payload file..."
        try {
            # Map Drive for Cleanup
            $DriveNameClean = "AutoDBAudit_Clean_$(Get-Random)"
            $RootUNC = "\\$Target\C$"
            New-PSDrive -Name $DriveNameClean -PSProvider FileSystem -Root $RootUNC -Credential $Credential -ErrorAction Stop | Out-Null
            
            try {
                $RemoteFile = "$($DriveNameClean):\Windows\Temp\AutoDBAudit_Enable-WinRM.ps1"
                if (Test-Path $RemoteFile) {
                    Remove-Item -Path $RemoteFile -Force -ErrorAction SilentlyContinue
                    Write-Log "  Payload deleted." "Green"
                }
            }
            finally {
                Remove-PSDrive -Name $DriveNameClean -ErrorAction SilentlyContinue
            }
        }
        catch {
            Write-Log "  Could not delete payload file (Permissions?)." "Yellow"
        }
    }
    else {
        Write-Log "  Skipping file cleanup (SMB Closed)." "Yellow"
    }
    
    Write-Log "Disable Sequence Complete." "Green"
}
