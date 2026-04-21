$ErrorActionPreference = 'Stop'
$backlog = Get-Content 'j:\CLASSIC-Fallout4\docs\implementation\python_api_parity\governance\deferred_runtime_backlog.json' -Raw | ConvertFrom-Json

# Get all distinct rustSymbols and bindingIdentifiers from deferred scanlog entries
$scanlogEntries = $backlog.entries | Where-Object { $_.ownerModule -eq 'scanlog' }
Write-Host ("Scanlog deferred entries: {0}" -f $scanlogEntries.Count)

# Extract distinct rustSymbol values
$rustSyms = $scanlogEntries | ForEach-Object { $_.rustSymbols } | Where-Object { $_ } | Sort-Object -Unique
Write-Host ("Distinct rustSymbols across deferred: {0}" -f $rustSyms.Count)

# Now find which sub-module each symbol lives in by greppping classic-scanlog-core source
$coreRoot = 'j:\CLASSIC-Fallout4\ClassicLib-rs\business-logic\classic-scanlog-core\src'
$subFiles = Get-ChildItem -Path $coreRoot -Recurse -File -Filter '*.rs' | Where-Object { $_.Name -ne 'lib.rs' }
Write-Host ("Core source files: {0}" -f $subFiles.Count)

$symToFile = @{}
foreach ($sym in $rustSyms) {
    $found = @()
    foreach ($file in $subFiles) {
        $content = Get-Content $file.FullName -Raw
        $patternStruct = "(?m)^\s*(?:pub\s+)?(?:struct|enum|fn|type|trait|const)\s+$([regex]::Escape($sym))\b"
        if ($content -match $patternStruct) { $found += $file.FullName }
    }
    $symToFile[$sym] = $found
}

# Group by top-level sub-module name (the directory or file under src/)
function Get-ModuleName($absPath) {
    $rel = $absPath.Substring($coreRoot.Length).TrimStart('\','/')
    $parts = $rel -split '[\\/]'
    return $parts[0] -replace '\.rs$',''
}

$bySubModule = @{}
foreach ($sym in $symToFile.Keys) {
    $files = $symToFile[$sym]
    if ($files.Count -eq 0) {
        $sub = '_NOT_FOUND_'
    } else {
        # take first match
        $sub = Get-ModuleName $files[0]
    }
    if (-not $bySubModule.ContainsKey($sub)) { $bySubModule[$sub] = @() }
    $bySubModule[$sub] += $sym
}

Write-Host ''
Write-Host '=== Distinct rustSymbols grouped by core sub-module ==='
$bySubModule.GetEnumerator() | Sort-Object Name | ForEach-Object {
    Write-Host ("{0,-25} {1,4} symbols: {2}" -f $_.Key, $_.Value.Count, ($_.Value -join ', '))
}

# Now also count how many CONTRACT ROWS (deferred entries) each sub-module owns
# A contract row maps to a rustSymbol; multiple rows can share a symbol
$rowsBySub = @{}
foreach ($entry in $scanlogEntries) {
    $rs = $entry.rustSymbols
    if (-not $rs -or $rs.Count -eq 0) { continue }
    $sym = $rs[0]
    if ($symToFile.ContainsKey($sym) -and $symToFile[$sym].Count -gt 0) {
        $sub = Get-ModuleName $symToFile[$sym][0]
    } else {
        $sub = '_NOT_FOUND_'
    }
    if (-not $rowsBySub.ContainsKey($sub)) { $rowsBySub[$sub] = 0 }
    $rowsBySub[$sub] += 1
}

# Many entries have empty rustSymbols but bindingIdentifiers — count those by binding identifier prefix
$entriesByBindingClass = @{}
foreach ($entry in $scanlogEntries) {
    $rs = $entry.rustSymbols
    if ($rs -and $rs.Count -gt 0) { continue }
    $bids = $entry.bindingIdentifiers
    if (-not $bids -or $bids.Count -eq 0) { continue }
    $bid = $bids[0]
    # classic_scanlog.LogParser.find_errors -> LogParser
    $parts = $bid -split '\.'
    if ($parts.Count -ge 2) {
        $cls = $parts[1]
        if ($symToFile.ContainsKey($cls) -and $symToFile[$cls].Count -gt 0) {
            $sub = Get-ModuleName $symToFile[$cls][0]
        } else {
            $sub = '_NOT_FOUND_'
        }
        if (-not $rowsBySub.ContainsKey($sub)) { $rowsBySub[$sub] = 0 }
        $rowsBySub[$sub] += 1
    }
}

Write-Host ''
Write-Host '=== Deferred contract rows attributed to scanlog sub-modules ==='
$total = 0
$rowsBySub.GetEnumerator() | Sort-Object Name | ForEach-Object {
    Write-Host ("{0,-25} {1,4} rows" -f $_.Key, $_.Value)
    $total += $_.Value
}
Write-Host ("TOTAL ROWS ATTRIBUTED: {0} (expected ~228)" -f $total)
