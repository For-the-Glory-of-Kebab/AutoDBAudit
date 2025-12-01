#requires -Version 7.0
Set-StrictMode -Version Latest

#region helpers

function Test-HasProperty {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][object]$InputObject,
        [Parameter(Mandatory)][string]$Name
    )
    return ($InputObject.PSObject.Properties.Name -contains $Name)
}

function Get-IfPresent {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]$InputObject,
        [Parameter(Mandatory)][string]$Name
    )
    if (Test-HasProperty -InputObject $InputObject -Name $Name) { return $InputObject.$Name }
    return $null
}

function Normalize-Null {
    [CmdletBinding()]
    param([Parameter(ValueFromPipeline=$true)]$Value)
    process {
        if ($null -eq $Value) { return $null }
        $s = "$Value"
        if ([string]::IsNullOrWhiteSpace($s)) { return $null }
        if ($s.Trim().ToLowerInvariant() -eq 'null') { return $null }
        return $Value
    }
}

function Normalize-Auth {
    [CmdletBinding()]
    param([string]$Auth)
    if ([string]::IsNullOrWhiteSpace($Auth)) { return 'Integrated' }
    switch ($Auth.Trim().ToLowerInvariant()) {
        'integrated' { 'Integrated' }
        'windows'    { 'Integrated' }
        'win'        { 'Integrated' }
        'ntlm'       { 'Integrated' }
        'sql'        { 'Sql' }
        'sqlauth'    { 'Sql' }
        'sqlpassword'{ 'Sql' }
        default      { 'Integrated' }
    }
}

function To-IntOrDefault {
    [CmdletBinding()]
    param(
        $Value,
        [Parameter(Mandatory)][int]$Default
    )
    if ($null -eq $Value) { return $Default }
    try { return [int]$Value } catch { return $Default }
}

function Build-ServerInstance {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Server,
        [string]$Instance,
        [Nullable[int]]$Port
    )
    if ($Port)     { return "$Server,$Port" }
    if ($Instance) { return "$Server\$Instance" }
    return $Server
}

function New-CredentialFromSecret {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "SecretPath not found: $Path"
    }
    $obj = Import-Clixml -Path $Path
    if ($obj -is [System.Management.Automation.PSCredential]) { return $obj }
    throw "SecretPath does not contain a PSCredential: $Path"
}

#endregion helpers

#region JSON ingestion

function Read-JsonTargets {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Targets file not found: $Path"
    }

    $raw = (Get-Content -LiteralPath $Path -Raw) | ConvertFrom-Json
    $items = @($raw)

    foreach ($t in $items) {
        $serverRaw = Get-IfPresent -InputObject $t -Name 'Server' | Normalize-Null
        if ([string]::IsNullOrWhiteSpace($serverRaw)) {
            Write-Warning "Skipping row with missing 'Server'."
            continue
        }
        $server = [string]$serverRaw

        $instance = Get-IfPresent -InputObject $t -Name 'Instance' | Normalize-Null
        if ($instance) { $instance = [string]$instance }

        $portVal = Get-IfPresent -InputObject $t -Name 'Port' | Normalize-Null
        $port    = if ($portVal -ne $null -and "$portVal".Trim() -ne '') { To-IntOrDefault -Value $portVal -Default $null } else { $null }

        $auth = Normalize-Auth -Auth (Get-IfPresent -InputObject $t -Name 'Auth' | Normalize-Null)

        $sqlUser    = Get-IfPresent -InputObject $t -Name 'SqlUser'    | Normalize-Null
        $secretPath = Get-IfPresent -InputObject $t -Name 'SecretPath' | Normalize-Null

        # Encrypt is a string: 'Mandatory','Optional','Strict' (default: Optional)
        $encryptVal = Get-IfPresent -InputObject $t -Name 'Encrypt' | Normalize-Null
        $encrypt    = if ($encryptVal) { [string]$encryptVal } else { 'Optional' }

        # Trust server cert by default (no certs in your env)
        $trustVal = Get-IfPresent -InputObject $t -Name 'TrustServerCertificate'
        $trust    = if ($trustVal -ne $null) { [bool]$trustVal } else { $true }

        $connectTimeout = To-IntOrDefault -Value (Get-IfPresent -InputObject $t -Name 'ConnectTimeout') -Default 15
        $appName = Get-IfPresent -InputObject $t -Name 'ApplicationName' | Normalize-Null
        if (-not $appName) { $appName = 'SqlInventory' }

        $serverInstance = Build-ServerInstance -Server $server -Instance $instance -Port $port
        $display = if ($port) { "${server}:$port" } elseif ($instance) { "${server}\$instance" } else { $server }

        [pscustomobject]@{
            Server                 = $server
            Instance               = $instance
            Port                   = $port
            ServerInstance         = $serverInstance
            Display                = $display
            Auth                   = $auth
            SqlUser                = $sqlUser
            SecretPath             = $secretPath
            Encrypt                = $encrypt
            TrustServerCertificate = $trust
            ConnectTimeout         = $connectTimeout
            ApplicationName        = $appName
        }
    }
}

#endregion JSON ingestion

#region connectivity

function Test-SqlLogin {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$ServerInstance,
        [ValidateSet('Integrated','Sql')]
        [string]$Auth = 'Integrated',
        [System.Management.Automation.PSCredential]$Credential,
        [int]$ConnectTimeout = 15,
        [ValidateSet('Mandatory','Optional','Strict')]
        [string]$Encrypt = 'Optional',
        [bool]$TrustServerCertificate = $true,
        [string]$ApplicationName = 'SqlInventory'
    )

    $builder = New-Object System.Data.SqlClient.SqlConnectionStringBuilder
    $builder['Data Source']            = $ServerInstance
    $builder['Initial Catalog']        = 'master'
    $builder['Connect Timeout']        = $ConnectTimeout
    # For no-cert envs use driver-level: disable TLS and trust server by default
    $builder['Encrypt']                = $false
    $builder['TrustServerCertificate'] = $true
    $builder['Application Name']       = $ApplicationName
    $builder['Persist Security Info']  = $false

    if ($Auth -eq 'Integrated') {
        $builder['Integrated Security'] = $true
    } else {
        if (-not $Credential) { throw "Credential is required for Auth=Sql" }
        $builder['Integrated Security'] = $false
        $builder['User ID']             = $Credential.UserName
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Credential.Password)
        )
        try { $builder['Password'] = $plain } finally { $plain = $null }
    }

    $conn = New-Object System.Data.SqlClient.SqlConnection $builder.ConnectionString
    try {
        $conn.Open()
        $srv = $conn.DataSource
        $conn.Close()
        [pscustomobject]@{ Success = $true; Message = "Connected to $srv" }
    } catch {
        [pscustomobject]@{ Success = $false; Message = $_.Exception.Message }
    } finally {
        if ($conn.State -ne 'Closed') { $conn.Close() }
        $conn.Dispose()
    }
}

#endregion connectivity

#region public API

function Import-SqlTargets {
    [CmdletBinding(SupportsShouldProcess=$false)]
    param(
        [Parameter(Mandatory)][string]$Path,
        [switch]$ValidateAuth,
        [int]$MaxAuthRetries = 3,
        [switch]$PromptMissingCredentials,
        [switch]$AllowPromptOnFailure,
        [switch]$Deduplicate
    )

    $rawTargets = Read-JsonTargets -Path $Path

    $targets = if ($Deduplicate) {
        $seen = @{}
        foreach ($t in $rawTargets) {
            if (-not $seen.ContainsKey($t.Display)) {
                $seen[$t.Display] = $true
                $t
            } else {
                Write-Verbose "Deduplicated target: $($t.Display)"
            }
        }
    } else { $rawTargets }

    $output = New-Object System.Collections.Generic.List[object]

    foreach ($t in $targets) {
        $auth = $t.Auth
        $cred = $null

        if ($auth -eq 'Sql') {
            if ($t.SecretPath) {
                try { $cred = New-CredentialFromSecret -Path $t.SecretPath }
                catch { Write-Warning "SecretPath load failed for $($t.Display): $($_.Exception.Message)" }
            }
            if (-not $cred -and $t.SqlUser) {
                if ($PromptMissingCredentials) {
                    $password = Read-Host -AsSecureString -Prompt "Enter SQL password for $($t.Display) as $($t.SqlUser)"
                    $cred     = [pscredential]::new([string]$t.SqlUser, $password)
                } else {
                    Write-Warning "Missing password for $($t.Display) user $($t.SqlUser). Use -PromptMissingCredentials or provide SecretPath."
                }
            }
            if (-not $cred -and $PromptMissingCredentials) {
                $user     = Read-Host -Prompt "Enter SQL username for $($t.Display)"
                $password = Read-Host -AsSecureString -Prompt "Enter SQL password for $($t.Display) as $user"
                if (-not [string]::IsNullOrWhiteSpace($user)) {
                    $cred = [pscredential]::new($user, $password)
                }
            }
        }

        $validationStatus  = 'Skipped'
        $validationMessage = $null

        if ($ValidateAuth) {
            $attempt = 0
            do {
                $attempt++
                try {
                    $test = Test-SqlLogin -ServerInstance $t.ServerInstance -Auth $auth -Credential $cred `
                        -ConnectTimeout $t.ConnectTimeout -Encrypt $t.Encrypt `
                        -TrustServerCertificate:$t.TrustServerCertificate -ApplicationName $t.ApplicationName
                } catch {
                    $test = [pscustomobject]@{ Success = $false; Message = $_.Exception.Message }
                }

                if ($test.Success) {
                    $validationStatus  = 'Success'
                    $validationMessage = $test.Message
                    break
                } else {
                    $validationStatus  = 'Failed'
                    $validationMessage = $test.Message
                    Write-Warning "Auth failed [$attempt/$MaxAuthRetries] for $($t.Display): $($test.Message)"

                    if ($auth -eq 'Sql' -and ($AllowPromptOnFailure -or $PromptMissingCredentials)) {
                        $existingUser = if ($cred) { $cred.UserName } elseif ($t.SqlUser) { [string]$t.SqlUser } else { '' }
                        $userPrompt   = if ($existingUser) { $existingUser } else { Read-Host -Prompt "Enter SQL username for $($t.Display)" }
                        $password     = Read-Host -AsSecureString -Prompt "Enter SQL password for $($t.Display) as $userPrompt"
                        $cred         = [pscredential]::new($userPrompt, $password)
                    } else {
                        break
                    }
                }
            } while ($attempt -lt $MaxAuthRetries)
        }

        $output.Add([pscustomobject]@{
            Server                 = $t.Server
            Instance               = $t.Instance
            Port                   = $t.Port
            ServerInstance         = $t.ServerInstance
            Display                = $t.Display
            Auth                   = $auth
            Credential             = $cred
            Encrypt                = $t.Encrypt
            TrustServerCertificate = $t.TrustServerCertificate
            ConnectTimeout         = $t.ConnectTimeout
            ApplicationName        = $t.ApplicationName
            ValidationStatus       = $validationStatus
            ValidationMessage      = $validationMessage
        }) | Out-Null
    }

    return $output
}

#endregion public API

Export-ModuleMember -Function Import-SqlTargets