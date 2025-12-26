param([Parameter(ValueFromRemainingArguments = $true)]$RemainingArgs)
Push-Location $PSScriptRoot\..
& .\venv\Scripts\Activate.ps1
python -m autodbaudit.interface.cli $RemainingArgs
Pop-Location
