$ErrorActionPreference = 'Stop'
$backlog = Get-Content 'j:\CLASSIC-Fallout4\docs\implementation\python_api_parity\governance\deferred_runtime_backlog.json' -Raw | ConvertFrom-Json

Write-Host '=== version_registry deferred entries grouped by binding-id class ==='
$vrEntries = $backlog.entries | Where-Object { $_.ownerModule -eq 'version_registry' }
$vrCounts = @{}
foreach ($e in $vrEntries) {
    $bids = $e.bindingIdentifiers
    if ($bids -and $bids.Count -gt 0) {
        $key = ($bids[0] -split '\.')[1]
    } else {
        $key = '_RUST_ONLY_:' + ($e.rustSymbols -join ',')
    }
    if (-not $vrCounts.ContainsKey($key)) { $vrCounts[$key] = 0 }
    $vrCounts[$key] += 1
}
$vrCounts.GetEnumerator() | Sort-Object Name | ForEach-Object {
    "{0,-50} {1,4}" -f $_.Key, $_.Value
}
Write-Host ('Total VR deferred: ' + $vrEntries.Count)

Write-Host ''
Write-Host '=== config deferred entries grouped by binding-id class ==='
$cEntries = $backlog.entries | Where-Object { $_.ownerModule -eq 'config' }
$cCounts = @{}
foreach ($e in $cEntries) {
    $bids = $e.bindingIdentifiers
    if ($bids -and $bids.Count -gt 0) {
        $key = ($bids[0] -split '\.')[1]
    } else {
        $key = '_RUST_ONLY_:' + ($e.rustSymbols -join ',')
    }
    if (-not $cCounts.ContainsKey($key)) { $cCounts[$key] = 0 }
    $cCounts[$key] += 1
}
$cCounts.GetEnumerator() | Sort-Object Name | ForEach-Object {
    "{0,-50} {1,4}" -f $_.Key, $_.Value
}
Write-Host ('Total config deferred: ' + $cEntries.Count)

Write-Host ''
Write-Host '=== aux deferred (full dump) ==='
$auxEntries = $backlog.entries | Where-Object { $_.ownerModule -eq 'aux' }
$auxEntries | ConvertTo-Json -Depth 5
