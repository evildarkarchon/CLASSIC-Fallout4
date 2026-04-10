$ErrorActionPreference = 'Stop'
$backlog = Get-Content 'j:\CLASSIC-Fallout4\docs\implementation\python_api_parity\governance\deferred_runtime_backlog.json' -Raw | ConvertFrom-Json

$scanlogEntries = $backlog.entries | Where-Object { $_.ownerModule -eq 'scanlog' }

# Build a class -> sub-module map by reading classic-scanlog-py source files
$pyRoot = 'j:\CLASSIC-Fallout4\ClassicLib-rs\python-bindings\classic-scanlog-py\src'
$pySubFiles = Get-ChildItem -Path $pyRoot -File -Filter '*.rs' | Where-Object { $_.Name -ne 'lib.rs' }

# Pull all `#[pyclass(name = "X")]` and `#[pyfunction]` declarations and structs/fns
$classToSub = @{}
$fnToSub    = @{}
foreach ($file in $pySubFiles) {
    $sub = $file.BaseName
    $content = Get-Content $file.FullName -Raw

    # 1) #[pyclass(name = "X")] then later struct PyX or pub struct PyX
    foreach ($m in [regex]::Matches($content, '(?ms)#\[pyclass\([^)]*name\s*=\s*"(?<name>[^"]+)"[^)]*\)\][^{]*?(?:pub\s+)?struct\s+(?<rust>\w+)')) {
        $classToSub[$m.Groups['name'].Value] = $sub
        $classToSub[$m.Groups['rust'].Value] = $sub
    }
    # 2) #[pyclass] then struct PyX (no rename — Python name is X-without-Py?)
    foreach ($m in [regex]::Matches($content, '(?ms)#\[pyclass\][^{]*?(?:pub\s+)?struct\s+(?<rust>\w+)')) {
        $rust = $m.Groups['rust'].Value
        $py = $rust -replace '^Py',''
        $classToSub[$rust] = $sub
        $classToSub[$py] = $sub
    }
    # 3) #[pyfunction] then fn name
    foreach ($m in [regex]::Matches($content, '(?ms)#\[pyfunction[^]]*\][^{]*?fn\s+(?<name>\w+)')) {
        $fnToSub[$m.Groups['name'].Value] = $sub
    }
}

Write-Host ("Class->sub map size: {0}" -f $classToSub.Count)
Write-Host ("Function->sub map size: {0}" -f $fnToSub.Count)

# Also map -core sub-module names directly when bindingIdentifiers is empty
$coreSubsByName = @{
    'patterns' = 'patterns'
    'parser' = 'parser'
    'formid' = 'formid'
    'formid_analyzer' = 'formid_analyzer'
    'plugin_analyzer' = 'plugin_analyzer'
    'record_scanner' = 'record_scanner'
    'mod_detector' = 'mod_detector'
    'fcx_handler' = 'fcx_handler'
    'gpu_detector' = 'gpu_detector'
    'settings_validator' = 'settings_validator'
    'suspect_scanner' = 'suspect_scanner'
    'orchestrator' = 'orchestrator'
    'report' = 'report'
    'papyrus' = 'papyrus'
    'version' = 'version'
    'crashgen_registry' = 'crashgen_registry'
    'segment_key' = 'segment_key'
    'error' = 'error'
}

# Map every deferred row to a sub-module
$rowsBySub = @{}
$unattributed = @()
foreach ($entry in $scanlogEntries) {
    $sub = $null
    # Try bindingIdentifiers first (e.g., classic_scanlog.LogParser.find_errors -> LogParser)
    $bids = $entry.bindingIdentifiers
    if ($bids -and $bids.Count -gt 0) {
        $bid = $bids[0]
        $parts = $bid -split '\.'
        if ($parts.Count -ge 2) {
            $cls = $parts[1]
            if ($classToSub.ContainsKey($cls))      { $sub = $classToSub[$cls] }
            elseif ($fnToSub.ContainsKey($cls))     { $sub = $fnToSub[$cls] }
            elseif ($coreSubsByName.ContainsKey($cls)) { $sub = $coreSubsByName[$cls] }
        }
    }
    # Fall back to rustSymbols
    if (-not $sub) {
        $rs = $entry.rustSymbols
        if ($rs -and $rs.Count -gt 0) {
            $sym = $rs[0]
            if ($classToSub.ContainsKey($sym))      { $sub = $classToSub[$sym] }
            elseif ($fnToSub.ContainsKey($sym))     { $sub = $fnToSub[$sym] }
            elseif ($coreSubsByName.ContainsKey($sym)) { $sub = $coreSubsByName[$sym] }
        }
    }
    if (-not $sub) {
        $sub = '_UNATTRIBUTED_'
        $unattributed += [pscustomobject]@{ id = $entry.coverageId; bid = ($bids -join ','); rs = ($entry.rustSymbols -join ',') }
    }
    if (-not $rowsBySub.ContainsKey($sub)) { $rowsBySub[$sub] = 0 }
    $rowsBySub[$sub] += 1
}

Write-Host ''
Write-Host '=== Deferred scanlog rows attributed to sub-modules ==='
$total = 0
$rowsBySub.GetEnumerator() | Sort-Object Name | ForEach-Object {
    Write-Host ("  {0,-25} {1,4} rows" -f $_.Key, $_.Value)
    $total += $_.Value
}
Write-Host ("  TOTAL: {0}" -f $total)

if ($unattributed.Count -gt 0) {
    Write-Host ''
    Write-Host ('=== Unattributed entries ({0}) ===' -f $unattributed.Count)
    $unattributed | Select-Object -First 30 | Format-Table -AutoSize
}

# Compute D-01 layer totals
$wave1 = @('parser','formid','formid_analyzer','record_scanner','plugin_analyzer','patterns')
$wave2 = @('mod_detector','suspect_scanner','settings_validator','fcx_handler','gpu_detector')
$wave3 = @('orchestrator','report','papyrus','version','crashgen_rules','core_mod_convert','crashgen_registry','segment_key','error')

function Sum-Wave($wave, $rowsBySub) {
    $sum = 0
    foreach ($s in $wave) { if ($rowsBySub.ContainsKey($s)) { $sum += $rowsBySub[$s] } }
    return $sum
}

Write-Host ''
Write-Host '=== D-01 wave totals ==='
$w1 = Sum-Wave $wave1 $rowsBySub
$w2 = Sum-Wave $wave2 $rowsBySub
$w3 = Sum-Wave $wave3 $rowsBySub
Write-Host ("  Wave 1 (parsing primitives, 6 sub-mods): {0}" -f $w1)
Write-Host ("  Wave 2 (detection & analysis, 5 sub-mods): {0}" -f $w2)
Write-Host ("  Wave 3 (orchestration & output, 6+3 sub-mods): {0}" -f $w3)
Write-Host ("  Total in waves: {0}" -f ($w1 + $w2 + $w3))
