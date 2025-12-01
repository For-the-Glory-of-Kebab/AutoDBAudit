#requires -Version 7.0
Set-StrictMode -Version Latest
$stage = 'D:\Raz-Initiative\stage\PSModules'
$env:PSModulePath = "$stage;$env:PSModulePath"

Import-Module "$PSScriptRoot\SqlInventory.Targets.psm1" -Force

#region Connection
function Get-SqlConnectionString {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$ServerInstance,
        [ValidateSet('Integrated','Sql')][string]$Auth = 'Integrated',
        [System.Management.Automation.PSCredential]$Credential,
        [int]$ConnectTimeout = 15,
        [string]$ApplicationName = 'SqlInventory'
    )

    $mk = {
        param($ds)
        $b = [System.Data.SqlClient.SqlConnectionStringBuilder]::new()
        $b['Data Source']            = $ds
        $b['Initial Catalog']        = 'master'
        $b['Connect Timeout']        = $ConnectTimeout
        $b['Encrypt']                = $false
        $b['TrustServerCertificate'] = $true
        $b['Application Name']       = $ApplicationName
        $b['Persist Security Info']  = $false
        if ($Auth -eq 'Integrated') {
            $b['Integrated Security'] = $true
        } else {
            if (-not $Credential) { throw "Credential required for Auth=Sql" }
            $b['Integrated Security'] = $false
            $b['User ID']             = $Credential.UserName
            $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
                [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Credential.Password)
            )
            try { $b['Password'] = $plain } finally { $plain = $null }
        }
        $b.ConnectionString
    }

    $isLocal = @('.', 'localhost', $env:COMPUTERNAME) -contains ($ServerInstance -split '[\\,]')[0]
    $candidates = [System.Collections.Generic.List[string]]::new()
    $candidates.Add($ServerInstance)

    if ($isLocal -and $Auth -eq 'Integrated') {
        if ($ServerInstance -match '^[\.\w-]+\\(?<inst>[\w$-]+)$') {
            $inst = $Matches.inst
            $candidates.Insert(0, "lpc:.\$inst")
            $candidates.Insert(1, "np:\\.\pipe\MSSQL$$inst\sql\query")
        } else {
            $candidates.Insert(0, 'lpc:.')
            $candidates.Insert(1, 'np:\\.\pipe\sql\query')
        }
    }

    foreach ($ds in $candidates) {
        $cs = & $mk $ds
        $conn = [System.Data.SqlClient.SqlConnection]::new($cs)
        try { $conn.Open(); $conn.Close(); return $cs } catch { continue } finally {
            if ($conn.State -ne 'Closed') { $conn.Close() }
            $conn.Dispose()
        }
    }
    & $mk $candidates[-1]
}
#endregion

#region Flatteners
function Convert-DataTableToRows {
    [CmdletBinding()]
    param([Parameter(Mandatory)][System.Data.DataTable]$DataTable)
    foreach ($row in $DataTable.Rows) {
        $h = [ordered]@{}
        foreach ($col in $DataTable.Columns) {
            $v = $row[$col.ColumnName]
            $h[$col.ColumnName] = if ($null -eq $v) { $null } elseif ($v -is [ValueType] -or $v -is [string] -or $v -is [datetime]) { $v } else { "$v" }
        }
        [pscustomobject]$h
    }
}
function Convert-AnyToRow {
    [CmdletBinding()]
    param([Parameter(Mandatory)]$InputObject)
    if ($InputObject -is [System.Collections.IDictionary]) {
        $h = [ordered]@{}
        foreach ($k in $InputObject.Keys) {
            $v = $InputObject[$k]
            $h[$k] = if ($v -is [System.Collections.IEnumerable] -and -not ($v -is [string])) { ($v | ForEach-Object { "$_" }) -join ', ' }
                     elseif ($v -is [ValueType] -or $v -is [string] -or $v -is [datetime]) { $v }
                     else { "$v" }
        }
        return [pscustomobject]$h
    }
    if ($InputObject -is [System.Data.DataRow]) {
        $h = [ordered]@{}
        foreach ($col in $InputObject.Table.Columns) {
            $v = $InputObject[$col.ColumnName]
            $h[$col.ColumnName] = if ($null -eq $v) { $null } elseif ($v -is [ValueType] -or $v -is [string] -or $v -is [datetime]) { $v } else { "$v" }
        }
        return [pscustomobject]$h
    }
    if ($InputObject -is [psobject]) {
        $h = [ordered]@{}
        foreach ($p in $InputObject.PSObject.Properties) {
            $v = $p.Value
            $h[$p.Name] = if ($null -eq $v) { $null }
                          elseif ($v -is [System.Collections.IDictionary]) { (Convert-AnyToRow -InputObject $v) | ConvertTo-Json -Compress }
                          elseif ($v -is [System.Collections.IEnumerable] -and -not ($v -is [string])) { ($v | ForEach-Object { "$_" }) -join ', ' }
                          elseif ($v -is [ValueType] -or $v -is [string] -or $v -is [datetime]) { $v }
                          else { "$v" }
        }
        return [pscustomobject]$h
    }
    [pscustomobject]@{ Value = "$InputObject" }
}
#endregion

#region Excel helpers
function Add-ServerSeparators {
    [CmdletBinding()]
    param(
        [Parameter(ValueFromPipeline,Mandatory)][psobject]$InputObject,
        [Parameter(Mandatory)][string]$ServerKeyProperty
    )
    begin { $script:_lastSepVal = $null }
    process {
        $cur = $InputObject.$ServerKeyProperty
        if ($script:_lastSepVal -ne $cur) {
            $sepHash = [ordered]@{}
            foreach ($p in $InputObject.PSObject.Properties.Name) { $sepHash[$p] = $null }
            $sepHash[$ServerKeyProperty] = "— $cur —"
            [pscustomobject]$sepHash
            $script:_lastSepVal = $cur
        }
        $InputObject
    }
}

function Merge-RepeatingByColumn {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][OfficeOpenXml.ExcelWorksheet]$Worksheet,
        [int]$HeaderRow = 1,
        [Parameter(Mandatory)][string[]]$ColumnsToMerge
    )
    if (-not $Worksheet.Dimension) { return }
    $colCount = $Worksheet.Dimension.Columns
    # Build header -> letter map
    $nameToLetter = @{}
    for ($c=1; $c -le $colCount; $c++) {
        $header = $Worksheet.Cells[$HeaderRow,$c].Text
        $n=$c; $letters=''
        while ($n -gt 0) {
            $rem = ($n-1)%26
            $letters = ([char](65+$rem)) + $letters
            $n = [int](($n-$rem-1)/26)
        }
        if ($header) { $nameToLetter[$header] = $letters }
    }

    $letters = foreach ($req in $ColumnsToMerge) {
        if ($nameToLetter.ContainsKey($req)) { $nameToLetter[$req] }
    }
    if (-not $letters) { return }

    $lastText = @{}
    $startRow = @{}
    $rowCount = $Worksheet.Dimension.Rows
    foreach ($L in $letters) { $lastText[$L] = $null; $startRow[$L] = $HeaderRow + 1 }

    for ($r = $HeaderRow + 1; $r -le $rowCount + 1; $r++) {
        foreach ($L in $letters) {
            $cell = $Worksheet.Cells["$L$r"]
            $text = if ($r -le $rowCount) { $cell.Text } else { $null }
            if ($text -ne $lastText[$L]) {
                $s = $startRow[$L]; $e = $r - 1
                if ($e -ge $s) {
                    $range = $Worksheet.Cells["${L}${s}:${L}${e}"]
                    $span = $e - $s + 1
                    if ($span -gt 1) {
                        $range.Merge = $true
                        $range.Style.VerticalAlignment = 'Top'
                        $range.Style.HorizontalAlignment = 'Center'
                    }
                }
                $startRow[$L] = $r
                $lastText[$L] = $text
            }
        }
    }
}

function Apply-WorksheetStyling {
    param(
        [Parameter(Mandatory)][OfficeOpenXml.ExcelWorksheet]$Worksheet,
        [int]$HeaderRow = 1
    )
    if (-not $Worksheet.Dimension){ return }
    $dim = $Worksheet.Dimension
    $header = $Worksheet.Cells[$HeaderRow,1,$HeaderRow,$dim.Columns]
    $header.Style.Font.Bold = $true
    $header.Style.Fill.PatternType = 'Solid'
    $header.Style.Fill.BackgroundColor.SetColor([System.Drawing.Color]::FromArgb(31,78,121))
    $header.Style.Font.Color.SetColor([System.Drawing.Color]::White)
    $header.Style.HorizontalAlignment = 'Center'
    $Worksheet.View.FreezePanes($HeaderRow+1,1)
    for ($c=1; $c -le $dim.Columns; $c++){
        $h = $Worksheet.Cells[$HeaderRow,$c].Text
        if ($h -match 'Description|Definition|Query|Trigger|Schedule|Permissions'){ $Worksheet.Column($c).Style.WrapText = $true }
        if ($h -match 'Date$|At$|Time$|CollectedAt|Created|Backup') { $Worksheet.Column($c).Style.Numberformat.Format = 'yyyy-mm-dd HH:mm' }
    }
    $Worksheet.Cells[$HeaderRow,1,$dim.Rows,$dim.Columns].AutoFilter = $true
    # Attempt AutoFit; guard against OleAut date conversion issues
    try { $Worksheet.Cells.AutoFitColumns() | Out-Null } catch { Write-Verbose "AutoFitColumns skipped: $($_.Exception.Message)" }
}

function Add-ConditionalFormatting {
    param(
        [OfficeOpenXml.ExcelWorksheet]$Worksheet
    )
    if (-not $Worksheet.Dimension){ return }
    $headers = @{}
    for ($c=1;$c -le $Worksheet.Dimension.Columns;$c++){
        $t = $Worksheet.Cells[1,$c].Text
        if ($t) { $headers[$t] = $c }
    }
    if ($headers.ContainsKey('LastRunStatus')) {
        $col = $headers['LastRunStatus']
        $addr = $Worksheet.Cells[2,$col,$Worksheet.Dimension.Rows,$col].Address
        $ok = $Worksheet.ConditionalFormatting.AddContainsText($Worksheet.Cells[$addr]);  $ok.Text='Succeeded'; $ok.Style.Font.Color.Color=[System.Drawing.Color]::Green
        $fail = $Worksheet.ConditionalFormatting.AddContainsText($Worksheet.Cells[$addr]);$fail.Text='Failed';   $fail.Style.Font.Color.Color=[System.Drawing.Color]::Red
    }
}
#endregion

#region Data collection
function Collect-InventoryData {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][psobject[]]$ValidatedTargets,
        [string]$QueriesPath = ".\queries"
    )

    if (-not (Get-Module -ListAvailable -Name SqlServer)) {
        throw "SqlServer module (Invoke-Sqlcmd) missing. Install-Module SqlServer."
    }
    if (-not (Test-Path -LiteralPath $QueriesPath)) {
        Write-Warning "Queries path not found: $QueriesPath"
        return @()
    }

    $runAt = Get-Date
    $allSheets = @()

    foreach ($target in $ValidatedTargets) {
        if ($target.ValidationStatus -and $target.ValidationStatus -ne 'Success') {
            Write-Warning "Skipping $($target.Display) (validation=$($target.ValidationStatus))"
            continue
        }

        $connStr = Get-SqlConnectionString -ServerInstance $target.ServerInstance `
                                           -Auth $target.Auth `
                                           -Credential $target.Credential `
                                           -ConnectTimeout $target.ConnectTimeout `
                                           -ApplicationName $target.ApplicationName

        Get-ChildItem -Path $QueriesPath -Filter '*.sql' | Sort-Object Name | ForEach-Object {
            $sheetName = $_.BaseName
            $query = Get-Content -LiteralPath $_.FullName -Raw
            try {
                $rawResult = Invoke-Sqlcmd -ConnectionString $connStr -Query $query -ErrorAction Stop

                # Normalize results to enumerable rows
                $rows =
                    if ($rawResult -is [System.Data.DataSet]) {
                        if ($rawResult.Tables.Count -gt 0) {
                            Convert-DataTableToRows -DataTable $rawResult.Tables[0]
                        }
                    }
                    elseif ($rawResult -is [System.Data.DataTable]) {
                        Convert-DataTableToRows -DataTable $rawResult
                    }
                    elseif ($rawResult -is [System.Array]) {
                        $rawResult | ForEach-Object { Convert-AnyToRow $_ }
                    }
                    elseif ($rawResult -is [System.ValueType] -or $rawResult -is [string]) {
                        ,([pscustomobject]@{ Value = $rawResult })
                    }
                    else {
                        $rawResult | ForEach-Object { Convert-AnyToRow $_ }
                    }

                if (-not $rows) { return }

                $rowsTagged = $rows | ForEach-Object {
                    $_ | Add-Member -NotePropertyName 'Target' -NotePropertyValue $target.Display -Force
                    $_ | Add-Member -NotePropertyName 'CollectedAt' -NotePropertyValue $runAt -Force
                    $_
                }

                $sheet = $allSheets | Where-Object { $_.Name -eq $sheetName }
                if (-not $sheet) {
                    $mergeCols = switch ($sheetName) {
                        'InstanceInfo'        { @('Target') }
                        'Databases'           { @('Target') }
                        'ServerLogins'        { @('Target','LoginName') }
                        'DbUserLoginRoleMatrix'{ @('Target','Database','UserName') }
                        'DbUserLoginMatrix'   { @('Target','Database','UserName') }
                        'DbUsers'             { @('Target','Database') }
                        'DbRoles'             { @('Target','Database','RoleName') }
                        'RoleMatrix'          { @('Target') }
                        'DbTriggers'          { @('Target','Database','TriggerName') }
                        'ServerTriggers'      { @('Target','TriggerName') }
                        'JobsAndSchedules'    { @('Target','JobName') }
                        'JobHistory'          { @('Target','JobName') }
                        'LinkedServers'       { @('Target','LinkedServer') }
                        'ProtocolStatus'      { @('Target','protocol_desc') }
                        'TcpListeners'        { @('Target','ip_address') }
                        'Services'            { @('Target','ServiceName') }
                        'ServerPermissions'   { @('Target','PrincipalName') }
                        default               { @('Target') }
                    }
                    $sheet = @{
                        Name         = $sheetName
                        Rows         = @()
                        MergeColumns = $mergeCols
                    }
                    $allSheets += $sheet
                }
                $sheet.Rows += $rowsTagged
            }
            catch {
                Write-Warning "Query [$sheetName] failed for $($target.Display): $($_.Exception.Message)"
            }
        }
    }

    $allSheets
}
#endregion

#region Excel export
function Export-InventoryToExcel {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][array]$AllSheets,
        [Parameter(Mandatory)][string]$OutputPath,
        [psobject[]]$ValidatedTargets,
        [string]$TableStyle = 'Medium2',
        [switch]$OpenAfter
    )

    if (-not (Get-Module -ListAvailable -Name ImportExcel)) {
        throw "ImportExcel module required."
    }

    $order = @(
        'Summary',
        'InstanceInfo','Databases',
        'ServerLogins','RoleMatrix','ServerPermissions',
        'DbUserLoginMatrix','DbUserLoginRoleMatrix','DbUsers','DbRoles','DbTriggers',
        'ServerTriggers','JobsAndSchedules','JobHistory',
        'LinkedServers','ProtocolStatus','TcpListeners','Services'
    )

    # Ensure critical sheets exist even if queries returned zero rows so they appear in workbook
    $criticalSheets = 'DbUserLoginMatrix','DbUserLoginRoleMatrix'
    foreach ($cs in $criticalSheets) {
        if (-not ($AllSheets | Where-Object Name -eq $cs)) {
            $mergeCols = switch ($cs) {
                'DbUserLoginRoleMatrix' { @('Target','Database','UserName') }
                'DbUserLoginMatrix'     { @('Target','Database','UserName') }
            }
            $AllSheets += @{ Name=$cs; Rows=@(); MergeColumns=$mergeCols }
        }
    }

    $orderedData = $AllSheets | Sort-Object {
        $idx = $order.IndexOf($_.Name)
        if ($idx -lt 0) { 999 + [array]::IndexOf($AllSheets,$_) } else { $idx }
    }

    if (-not (Get-Module ImportExcel)) { Import-Module ImportExcel -ErrorAction Stop }
    # Use Open-ExcelPackage (returns wrapper with .Package) and normalize
    # Export each sheet directly to file (append mode) without manual workbook handling yet
    if (Test-Path -LiteralPath $OutputPath) { Remove-Item -LiteralPath $OutputPath -Force }
    $first = $true
    foreach ($sheet in $orderedData) {
        if (-not $sheet.Rows -or $sheet.Rows.Count -eq 0) {
            if ($criticalSheets -contains $sheet.Name) {
                # Add placeholder row so sheet is created
                $sheet.Rows = @([pscustomobject]@{ Target=$null; Note='No data collected' })
            } else {
                Write-Verbose "Skipping empty sheet $($sheet.Name)"; continue
            }
        }
        $data = $sheet.Rows | Sort-Object Target
        $dataWithSeps = $data | Add-ServerSeparators -ServerKeyProperty Target
        $exportParams = @{ Path = $OutputPath; WorksheetName = $sheet.Name; AutoSize=$true; BoldTopRow=$true; FreezeTopRow=$true; AutoFilter=$true }
        if (-not $first) { $exportParams.Append = $true }
        $null = $dataWithSeps | Export-Excel @exportParams
        $first = $false
    }

    # Create summary sheet now (append)
    $distinctTargets = [System.Collections.Generic.HashSet[string]]::new()
    foreach ($s in $orderedData) { foreach ($r in $s.Rows) { if ($r.Target) { $null = $distinctTargets.Add([string]$r.Target) } } }
    if (-not $distinctTargets.Count -and $ValidatedTargets) { foreach ($vt in $ValidatedTargets) { if ($vt.Display) { $null = $distinctTargets.Add([string]$vt.Display) } } }
    $rowTotal = ($orderedData | ForEach-Object { $_.Rows.Count } | Measure-Object -Sum).Sum
    $summaryData = @(
        [pscustomobject]@{ Item='GeneratedAt'; Value=(Get-Date) }
        [pscustomobject]@{ Item='Host';        Value=$env:COMPUTERNAME }
        [pscustomobject]@{ Item='Instances';   Value=$distinctTargets.Count }
        [pscustomobject]@{ Item='Sheets';      Value=($orderedData.Name -join ', ') }
        [pscustomobject]@{ Item='TotalRows';   Value=$rowTotal }
    )
    $null = $summaryData | Export-Excel -Path $OutputPath -WorksheetName 'Summary' -AutoSize -BoldTopRow -FreezeTopRow -Append:(!$first)

    # Reopen workbook once for styling & merging
    $pkg2 = Open-ExcelPackage -Path $OutputPath
    if ($pkg2 -and ($pkg2 | Get-Member -Name Workbook -ErrorAction SilentlyContinue)) {
        foreach ($sheet in $orderedData) {
            $ws = $pkg2.Workbook.Worksheets[$sheet.Name]
            if (-not $ws) { continue }
            # Remove any tables to avoid merge/styling corruption and Excel repair warnings
            if ($ws.Tables.Count -gt 0) { foreach ($t in @($ws.Tables)) { try { $null = $t.ConvertTableToRange() } catch {} } }
            $mergeCols = @()
            if ($sheet.PSObject.Properties['MergeColumns']) {
                $mc = $sheet.MergeColumns
                if ($mc -is [System.Collections.IEnumerable]) {
                    $mCount = ($mc | Measure-Object).Count
                    if ($mCount -gt 0) { $mergeCols = @($mc) }
                }
            }
            if ($mergeCols.Count -gt 0) { Merge-RepeatingByColumn -Worksheet $ws -HeaderRow 1 -ColumnsToMerge $mergeCols }
            if ($ws.Dimension) {
                for ($r=2; $r -le $ws.Dimension.Rows; $r++) {
                    if ($ws.Cells["A$r"].Text -like "—*—") {
                        $rowRange = $ws.Cells["${r}:$r"]
                        $rowRange.Style.Font.Italic = $true
                        $rowRange.Style.Fill.PatternType = 'Solid'
                        $rowRange.Style.Fill.BackgroundColor.SetColor([System.Drawing.Color]::FromArgb(235,235,235))
                        $rowRange.Style.Font.Color.SetColor([System.Drawing.Color]::FromArgb(90,90,90))
                    }
                }
                for ($r=2; $r -le $ws.Dimension.Rows; $r++) {
                    if ($ws.Cells["A$r"].Text -like "—*—") { continue }
                    if (($r % 2) -eq 0) {
                        $rowRange = $ws.Cells["${r}:$r"]
                        if ($rowRange.Style.Fill.BackgroundColor.Rgb -eq $null) {
                            $rowRange.Style.Fill.PatternType = 'Solid'
                            $rowRange.Style.Fill.BackgroundColor.SetColor([System.Drawing.Color]::FromArgb(248,250,252))
                        }
                    }
                }
                if ($sheet.Name -eq 'RoleMatrix') {
                    $roleCols = @(); for ($c=1; $c -le $ws.Dimension.Columns; $c++) { $h=$ws.Cells[1,$c].Text; if ($h -match '^(sysadmin|serveradmin|securityadmin|processadmin|setupadmin|diskadmin|dbcreator|bulkadmin)$'){ $roleCols+=$c } }
                    foreach ($c in $roleCols){ for ($r=2; $r -le $ws.Dimension.Rows; $r++){ $cell=$ws.Cells[$r,$c]; $val=$cell.Text; if ($val -in @('1','True')){ $cell.Style.Fill.PatternType='Solid'; $cell.Style.Fill.BackgroundColor.SetColor([System.Drawing.Color]::FromArgb(198,239,206)); $cell.Style.Font.Color.SetColor([System.Drawing.Color]::FromArgb(0,97,0)) } elseif ($val -in @('0','False')){ $cell.Style.Fill.PatternType='Solid'; $cell.Style.Fill.BackgroundColor.SetColor([System.Drawing.Color]::FromArgb(255,235,238)); $cell.Style.Font.Color.SetColor([System.Drawing.Color]::FromArgb(156,0,6)) } } }
                }
            }
            Apply-WorksheetStyling -Worksheet $ws
            Add-ConditionalFormatting -Worksheet $ws
        }
    $summaryWs = $pkg2.Workbook.Worksheets['Summary']; if ($summaryWs) { if ($summaryWs.Tables.Count -gt 0) { foreach ($t in @($summaryWs.Tables)) { try { $null = $t.ConvertTableToRange() } catch {} } }; Apply-WorksheetStyling -Worksheet $summaryWs }
        $pkg2.Save(); $pkg2.Dispose()
    } else { Write-Warning 'Could not reopen workbook for styling; data exported without styling.' }
    Write-Host "Report written: $OutputPath" -ForegroundColor Green

    if ($OpenAfter -and (Test-Path -LiteralPath $OutputPath)) {
        Start-Process $OutputPath | Out-Null
    }
}
#endregion

#region Run
$targetsFile = '.\SqlTargets.json'
$validated  = Import-SqlTargets -Path $targetsFile -ValidateAuth -PromptMissingCredentials
$allSheets  = Collect-InventoryData -ValidatedTargets $validated -QueriesPath '.\queries'
$outFile    = Join-Path $PWD ("SqlInventory_{0:yyyyMMdd_HHmm}.xlsx" -f (Get-Date))
Export-InventoryToExcel -AllSheets $allSheets -OutputPath $outFile -ValidatedTargets $validated -OpenAfter
#endregion