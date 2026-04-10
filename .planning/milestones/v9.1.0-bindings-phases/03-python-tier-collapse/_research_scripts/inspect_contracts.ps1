# Inspect Python parity contract + deferred backlog
$ErrorActionPreference = 'Stop'

$contract = Get-Content 'j:\CLASSIC-Fallout4\docs\implementation\python_api_parity\baseline\parity_contract.json' -Raw | ConvertFrom-Json
$backlog  = Get-Content 'j:\CLASSIC-Fallout4\docs\implementation\python_api_parity\governance\deferred_runtime_backlog.json' -Raw | ConvertFrom-Json

Write-Host '=== parity_contract.json ===' -ForegroundColor Cyan
Write-Host ('Top-level keys: ' + (($contract.PSObject.Properties | ForEach-Object { $_.Name }) -join ', '))
foreach ($prop in $contract.PSObject.Properties) {
    if ($prop.Value -is [System.Array]) {
        Write-Host ("  array key '{0}' length={1}" -f $prop.Name, $prop.Value.Count)
    } elseif ($prop.Value -is [System.Management.Automation.PSCustomObject]) {
        Write-Host ("  object key '{0}' subkeys=({1})" -f $prop.Name, (($prop.Value.PSObject.Properties | ForEach-Object { $_.Name }) -join ','))
    } else {
        Write-Host ("  scalar key '{0}'={1}" -f $prop.Name, $prop.Value)
    }
}

# Find the entry-array name
$entries = $null
foreach ($candidate in @('entries','rows','contractRows','contract_rows','tier1','tier_one','items')) {
    if ($contract.PSObject.Properties.Name -contains $candidate) { $entries = $contract.$candidate; break }
}
if ($null -eq $entries) {
    Write-Host 'No entry array key found at top level — dumping raw JSON head.' -ForegroundColor Yellow
    (Get-Content 'j:\CLASSIC-Fallout4\docs\implementation\python_api_parity\baseline\parity_contract.json' -Raw).Substring(0,2000)
} else {
    Write-Host ("Entry array count: {0}" -f $entries.Count)
    Write-Host 'First entry sample:'
    $entries[0] | ConvertTo-Json -Depth 6
    Write-Host 'Sample entry keys: '
    ($entries[0].PSObject.Properties | ForEach-Object { $_.Name }) -join ', '
}

Write-Host ''
Write-Host '=== deferred_runtime_backlog.json ===' -ForegroundColor Cyan
Write-Host ('Top-level keys: ' + (($backlog.PSObject.Properties | ForEach-Object { $_.Name }) -join ', '))
foreach ($prop in $backlog.PSObject.Properties) {
    if ($prop.Value -is [System.Array]) {
        Write-Host ("  array key '{0}' length={1}" -f $prop.Name, $prop.Value.Count)
    } elseif ($prop.Value -is [System.Management.Automation.PSCustomObject]) {
        Write-Host ("  object key '{0}' subkeys=({1})" -f $prop.Name, (($prop.Value.PSObject.Properties | ForEach-Object { $_.Name }) -join ','))
    } else {
        Write-Host ("  scalar key '{0}'={1}" -f $prop.Name, $prop.Value)
    }
}
$entries2 = $null
foreach ($candidate in @('entries','rows','deferred','items','tier2','tier_two','backlog')) {
    if ($backlog.PSObject.Properties.Name -contains $candidate) { $entries2 = $backlog.$candidate; break }
}
if ($null -eq $entries2) {
    Write-Host 'No entry array key found in backlog at top level — dumping raw JSON head.' -ForegroundColor Yellow
    (Get-Content 'j:\CLASSIC-Fallout4\docs\implementation\python_api_parity\governance\deferred_runtime_backlog.json' -Raw).Substring(0,2000)
} else {
    Write-Host ("Backlog entry count: {0}" -f $entries2.Count)
    Write-Host 'First backlog entry sample:'
    $entries2[0] | ConvertTo-Json -Depth 6
}
