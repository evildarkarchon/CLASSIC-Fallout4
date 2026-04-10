# Count entries by ownerModule in both files
$ErrorActionPreference = 'Stop'

$contract = Get-Content 'j:\CLASSIC-Fallout4\docs\implementation\python_api_parity\baseline\parity_contract.json' -Raw | ConvertFrom-Json
$backlog  = Get-Content 'j:\CLASSIC-Fallout4\docs\implementation\python_api_parity\governance\deferred_runtime_backlog.json' -Raw | ConvertFrom-Json

Write-Host '=== parity_contract.json tier1Mappings by ownerModule ===' -ForegroundColor Cyan
$contract.tier1Mappings | Group-Object ownerModule | Sort-Object Name | Format-Table Name, Count -AutoSize

Write-Host 'Total tier1Mappings: ' $contract.tier1Mappings.Count

Write-Host '=== parity_contract.json tier1Mappings by rustCrate ===' -ForegroundColor Cyan
$contract.tier1Mappings | Group-Object rustCrate | Sort-Object Name | Format-Table Name, Count -AutoSize

Write-Host '=== deferred_runtime_backlog.json entries by ownerModule ===' -ForegroundColor Cyan
$backlog.entries | Group-Object ownerModule | Sort-Object Name | Format-Table Name, Count -AutoSize

Write-Host 'Total deferred entries: ' $backlog.entries.Count

Write-Host '=== deferred_runtime_backlog.json by classification ===' -ForegroundColor Cyan
$backlog.entries | Group-Object classification | Sort-Object Name | Format-Table Name, Count -AutoSize

Write-Host '=== deferred_runtime_backlog.json by wave ===' -ForegroundColor Cyan
$backlog.entries | Group-Object wave | Sort-Object Name | Format-Table Name, Count -AutoSize

Write-Host '=== deferred entries: aux subset ===' -ForegroundColor Cyan
$backlog.entries | Where-Object { $_.ownerModule -eq 'aux' } | ForEach-Object {
    $rs = ($_.rustSymbols -join ',')
    "{0,-40} | wave={1} | rustSymbols=[{2}]" -f $_.coverageId, $_.wave, $rs
}

Write-Host '=== deferred scanlog entries: rustSymbols crate hint sample ===' -ForegroundColor Cyan
$backlog.entries | Where-Object { $_.ownerModule -eq 'scanlog' } | Select-Object -First 5 | ForEach-Object {
    "{0} | {1}" -f $_.coverageId, ($_.rustSymbols -join ',')
}
