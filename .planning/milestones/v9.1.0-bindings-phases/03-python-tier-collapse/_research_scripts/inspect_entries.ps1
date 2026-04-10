$ErrorActionPreference = 'Stop'
$backlog = Get-Content 'j:\CLASSIC-Fallout4\docs\implementation\python_api_parity\governance\deferred_runtime_backlog.json' -Raw | ConvertFrom-Json

Write-Host '=== Sample of 5 scanlog entries (full) ==='
$backlog.entries | Where-Object { $_.ownerModule -eq 'scanlog' } | Select-Object -First 5 | ConvertTo-Json -Depth 5

Write-Host ''
Write-Host '=== bindingIdentifiers analysis ==='
$bidCounts = @{}
foreach ($e in $backlog.entries) {
    $count = if ($e.bindingIdentifiers) { $e.bindingIdentifiers.Count } else { 0 }
    if (-not $bidCounts.ContainsKey($count)) { $bidCounts[$count] = 0 }
    $bidCounts[$count] += 1
}
$bidCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "  bindingIdentifiers count={0} -> {1} entries" -f $_.Key, $_.Value }

Write-Host ''
Write-Host '=== Sample bindingIdentifiers from scanlog (showing module breakdown) ==='
$scanlogIds = $backlog.entries | Where-Object { $_.ownerModule -eq 'scanlog' } | ForEach-Object { $_.bindingIdentifiers } | Where-Object { $_ }
Write-Host ("Total scanlog bindingIdentifiers: {0}" -f $scanlogIds.Count)
Write-Host 'First 30 distinct prefixes (split on first dot after module):'
$prefixes = @{}
foreach ($id in $scanlogIds) {
    $parts = $id -split '\.'
    if ($parts.Count -ge 2) {
        $key = ($parts[0..1] -join '.')
    } else {
        $key = $id
    }
    if (-not $prefixes.ContainsKey($key)) { $prefixes[$key] = 0 }
    $prefixes[$key] += 1
}
$prefixes.GetEnumerator() | Sort-Object Name | ForEach-Object { "  {0,-60} -> {1}" -f $_.Key, $_.Value }
