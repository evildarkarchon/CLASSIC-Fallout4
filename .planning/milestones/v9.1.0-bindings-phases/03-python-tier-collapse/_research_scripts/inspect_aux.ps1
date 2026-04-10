$ErrorActionPreference = 'Stop'
$backlog = Get-Content 'j:\CLASSIC-Fallout4\docs\implementation\python_api_parity\governance\deferred_runtime_backlog.json' -Raw | ConvertFrom-Json
$aux = $backlog.entries | Where-Object { $_.ownerModule -eq 'aux' }
Write-Host '=== Full aux entry ==='
$aux | ConvertTo-Json -Depth 10

# Look for related Tier-2 entries by source crate by scanning rustSymbols across all
Write-Host ''
Write-Host '=== Distinct rustSymbol values across deferred entries by ownerModule ==='
foreach ($module in @('scanlog','config','version_registry','aux')) {
    $entries = $backlog.entries | Where-Object { $_.ownerModule -eq $module }
    Write-Host ("---- {0} ({1} entries) ----" -f $module, $entries.Count)
    $allSymbols = $entries | ForEach-Object { $_.rustSymbols } | Where-Object { $_ }
    Write-Host ("  total symbols across rustSymbols arrays: {0}" -f $allSymbols.Count)
    Write-Host ("  distinct symbols: {0}" -f ($allSymbols | Sort-Object -Unique).Count)
}
