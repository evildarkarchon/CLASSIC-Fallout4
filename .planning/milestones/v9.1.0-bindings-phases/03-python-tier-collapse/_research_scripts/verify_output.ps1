$ErrorActionPreference = 'Stop'
$f = Get-Item 'j:\CLASSIC-Fallout4\.planning\phases\03-python-tier-collapse\03-RESEARCH.md'
Write-Host ('File: ' + $f.FullName)
Write-Host ('Size: ' + $f.Length + ' bytes')
$lc = (Get-Content $f.FullName | Measure-Object -Line)
Write-Host ('Lines: ' + $lc.Lines)

# Check first line
$first = Get-Content $f.FullName -TotalCount 1
Write-Host ('First line: ' + $first)

# Check section headers
Write-Host ''
Write-Host '=== Section headers ==='
Select-String -Path $f.FullName -Pattern '^## ' | ForEach-Object { Write-Host ('  ' + $_.Line) }
