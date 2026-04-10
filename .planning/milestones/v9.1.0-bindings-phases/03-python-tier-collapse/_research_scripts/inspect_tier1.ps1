$ErrorActionPreference = 'Stop'
$contract = Get-Content 'j:\CLASSIC-Fallout4\docs\implementation\python_api_parity\baseline\parity_contract.json' -Raw | ConvertFrom-Json

function Get-PyExport($mapping) {
    if ($mapping.pythonExportPath) { return $mapping.pythonExportPath }
    if ($mapping.pythonExport)     { return $mapping.pythonExport }
    return ''
}

Write-Host '=== First 10 tier1Mappings (config) ==='
$contract.tier1Mappings | Where-Object { $_.ownerModule -eq 'config' } | Select-Object -First 10 | ForEach-Object {
    $py = Get-PyExport $_
    "{0,-32} | crate={1,-30} | rust={2,-30} | py={3}.{4}" -f $_.id, $_.rustCrate, $_.rustSymbol, $_.pythonModule, $py
}

Write-Host ''
Write-Host '=== ALL scanlog tier1 mappings ==='
$contract.tier1Mappings | Where-Object { $_.ownerModule -eq 'scanlog' } | ForEach-Object {
    $py = Get-PyExport $_
    "{0,-30} | crate={1,-30} | rust={2,-30} | py={3}.{4}" -f $_.id, $_.rustCrate, $_.rustSymbol, $_.pythonModule, $py
}

Write-Host ''
Write-Host '=== Distinct rustCrate values across tier1 mappings ==='
$contract.tier1Mappings | Group-Object rustCrate | Sort-Object Name | Format-Table Name, Count -AutoSize

Write-Host '=== Distinct pythonKind values ==='
$contract.tier1Mappings | Group-Object pythonKind | Sort-Object Name | Format-Table Name, Count -AutoSize
