$ErrorActionPreference = 'Stop'
$backlog = Get-Content 'j:\CLASSIC-Fallout4\docs\implementation\python_api_parity\governance\deferred_runtime_backlog.json' -Raw | ConvertFrom-Json

Write-Host '=== deferred_runtime_backlog: counts by ownerModule x wave ==='
$grouped = $backlog.entries | Group-Object ownerModule, wave | Sort-Object Name
$grouped | Format-Table Name, Count -AutoSize

Write-Host ''
Write-Host '=== runtime_coverage_registry deferred_total source ==='
$cs = Get-Content 'j:\CLASSIC-Fallout4\docs\implementation\python_api_parity\baseline\runtime_coverage_summary.json' -Raw | ConvertFrom-Json
Write-Host ('runtime_verified=' + $cs.summary.runtime_verified_total + ' deferred=' + $cs.summary.deferred_total + ' contract_mapped=' + $cs.summary.contract_mapped_total)
Write-Host '(deferred_total of 289 vs raw backlog of 285 differs by 4 — those 4 are runtime_verified Tier-2 binding identifiers in registry that override deferred classification on a per-id basis)'

# Cross-check: runtime_coverage_registry tier-2 binding identifiers
$reg = Get-Content 'j:\CLASSIC-Fallout4\ClassicLib-rs\python-bindings\tests\fixtures\runtime_coverage_registry.json' -Raw | ConvertFrom-Json
$t2id = @()
foreach ($e in $reg.entries) {
    if ($e.tier -eq 'tier2' -and $e.bindingIdentifiers) {
        foreach ($bid in $e.bindingIdentifiers) { $t2id += $bid }
    }
}
Write-Host ''
Write-Host ("=== Tier-2 binding identifiers in runtime_coverage_registry: {0} ===" -f $t2id.Count)
$t2id | ForEach-Object { "  $_" }
