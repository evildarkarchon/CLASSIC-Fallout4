$ErrorActionPreference = 'Stop'
$path = 'j:\CLASSIC-Fallout4\.planning\phases\03-python-tier-collapse\03-RESEARCH.md'
$content = Get-Content $path -Raw

# Insert <user_constraints> tag before "## User Constraints (from CONTEXT.md)"
$marker1 = "## User Constraints (from CONTEXT.md)"
if ($content -notmatch [regex]::Escape($marker1)) { throw "Marker 1 not found" }
$content = $content -replace [regex]::Escape($marker1), "<user_constraints>`r`n$marker1"

# Insert </user_constraints> + <phase_requirements> wrapper
# Replace the boundary "---`n`n## Phase Requirements" so the tag closes user_constraints and opens phase_requirements
$marker2 = "## Phase Requirements"
if ($content -notmatch [regex]::Escape($marker2)) { throw "Marker 2 not found" }
$replacement2 = "</user_constraints>`r`n`r`n<phase_requirements>`r`n$marker2"
# But we need to make this a single replacement targeting the FIRST occurrence which is the section header.
# Use a regex that requires the line to be a section header (not a table-cell reference).
$content = [regex]::Replace($content, "(?m)^## Phase Requirements\b", $replacement2, 1)

# Insert </phase_requirements> tag at the end of the Phase Requirements section, just before the next "---" + "## Validation Architecture"
$marker3 = "## Validation Architecture"
if ($content -notmatch [regex]::Escape($marker3)) { throw "Marker 3 not found" }
$replacement3 = "</phase_requirements>`r`n`r`n---`r`n`r`n$marker3"
# Match: "---`n`n## Validation Architecture" → "</phase_requirements>`n`n---`n`n## Validation Architecture"
$content = [regex]::Replace($content, "(?ms)^---\s*\r?\n\s*\r?\n## Validation Architecture\b", $replacement3, 1)

Set-Content -Path $path -Value $content -NoNewline -Encoding utf8
Write-Host 'Wrapped tags successfully.'

# Verify
$verify = Get-Content $path -Raw
$tags = @('<user_constraints>','</user_constraints>','<phase_requirements>','</phase_requirements>')
foreach ($t in $tags) {
    $count = ([regex]::Matches($verify, [regex]::Escape($t))).Count
    Write-Host ("  {0,-25} count={1}" -f $t, $count)
}
