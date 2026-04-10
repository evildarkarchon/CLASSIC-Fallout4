$ErrorActionPreference = 'Stop'
$d = Get-Content 'j:\CLASSIC-Fallout4\docs\implementation\python_api_parity\baseline\parity_diff_report.json' -Raw | ConvertFrom-Json
Write-Host '=== Summary ==='
$d.summary | Format-List

Write-Host ''
Write-Host '=== Gap counts by owner / tier ==='
$d.gap_counts_by_owner_tier | ConvertTo-Json -Depth 5

Write-Host ''
Write-Host '=== Gap kind/owner sample (first 5 of each gap type) ==='
$d.gaps | Group-Object gap_type | ForEach-Object {
    Write-Host ("---- gap_type={0} ({1} entries) ----" -f $_.Name, $_.Count)
    $_.Group | Select-Object -First 5 | ForEach-Object {
        "  {0,-22} | {1,-30} | {2}" -f $_.owner_module, $_.rust_symbol, $_.python_export
    }
}

# Read and check coverage summary too
$cs = Get-Content 'j:\CLASSIC-Fallout4\docs\implementation\python_api_parity\baseline\runtime_coverage_summary.json' -Raw | ConvertFrom-Json
Write-Host ''
Write-Host '=== runtime_coverage_summary.json summary ==='
$cs.summary | Format-List
Write-Host '=== perOwnerModule ==='
$cs.perOwnerModule | ConvertTo-Json -Depth 4
