param(
    [string]$ScriptPath = (Join-Path $PSScriptRoot "../.." "rebuild_rust.ps1")
)

$ErrorActionPreference = "Stop"

$resolvedScriptPath = Resolve-Path -Path $ScriptPath

$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $resolvedScriptPath.Path,
    [ref]$tokens,
    [ref]$parseErrors
)

if ($parseErrors -and $parseErrors.Count -gt 0) {
    throw "Script has parse errors: $($parseErrors[0].Message)"
}

$paramBlock = $ast.ParamBlock
if (-not $paramBlock) {
    throw "Expected script-level param block in rebuild_rust.ps1."
}

$scriptText = Get-Content -Path $resolvedScriptPath.Path -Raw

if ($scriptText -match "auto-selecting -Target python") {
    throw "Expected no implicit Python-target fallback. Wheels must build only when -Target python is explicitly set."
}

if ($scriptText -match '(?s)-not \$PSBoundParameters\.ContainsKey\("Target"\).*?\$resolvedTarget\s*=\s*"python"') {
    throw "Expected no implicit reassignment to Python target when -Target is omitted."
}

if ($scriptText -notmatch '(?s)"workspace"\s*\{[\s\S]*?Invoke-RustWorkspaceRebuild[\s\S]*?-CrateFilters\s+\$Crates') {
    throw "Expected -Target workspace to pass positional crate filters into workspace rebuild selection."
}

if ($scriptText -match "ignored for -Target workspace") {
    throw "Expected positional crate filters to be supported for workspace target."
}

if ($scriptText -match '(?m)^\s*"all"\s*\{') {
    throw "Expected -Target all support to be removed from the target switch."
}

$targetParameter = $paramBlock.Parameters |
Where-Object { $_.Name.VariablePath.UserPath -eq "Target" } |
Select-Object -First 1

if (-not $targetParameter) {
    throw "Expected rebuild_rust.ps1 to expose a -Target parameter for selecting rebuild scope."
}

$targetDefaultAst = $targetParameter.DefaultValue
if (-not $targetDefaultAst) {
    throw "Expected -Target to define a default value."
}

$targetDefaultValue = if ($targetDefaultAst -is [System.Management.Automation.Language.ConstantExpressionAst]) {
    [string]$targetDefaultAst.Value
}
else {
    $rawTargetDefault = [string]$targetDefaultAst.Extent.Text
    $rawTargetDefault = $rawTargetDefault.Trim("'")
    $rawTargetDefault = $rawTargetDefault.Trim([char]34)
    $rawTargetDefault
}

if ($targetDefaultValue -ne "workspace") {
    throw "Expected -Target default to be 'workspace' so no-arg rebuild runs Rust-first workflows. Found '$targetDefaultValue'."
}

$targetParameterAttr = $targetParameter.Attributes |
Where-Object { $_.TypeName.Name -eq "Parameter" } |
Select-Object -First 1

$targetPositionNamedArg = $targetParameterAttr.NamedArguments |
Where-Object { $_.ArgumentName -eq "Position" } |
Select-Object -First 1

if ($targetPositionNamedArg) {
    throw "Expected -Target to remain named-only so positional args continue to map to crate/module filters."
}

$validateSet = $targetParameter.Attributes |
Where-Object { $_.TypeName.Name -eq "ValidateSet" } |
Select-Object -First 1

if (-not $validateSet) {
    throw "Expected -Target to declare ValidateSet values for supported rebuild scopes."
}

$expectedTargets = @("python", "workspace", "node")

$actualTargets = foreach ($arg in $validateSet.PositionalArguments) {
    if ($arg -is [System.Management.Automation.Language.ConstantExpressionAst]) {
        [string]$arg.Value
    }
    else {
        $rawValue = [string]$arg.Extent.Text
        $rawValue = $rawValue.Trim("'")
        $rawValue = $rawValue.Trim([char]34)
        $rawValue
    }
}

$missingTargets = $expectedTargets | Where-Object { $_ -notin $actualTargets }

if ($missingTargets.Count -gt 0) {
    throw "Missing expected -Target values: $($missingTargets -join ', ')"
}

if ("all" -in $actualTargets) {
    throw "Expected -Target all to be removed from supported values."
}

$buildOnlyParameter = $paramBlock.Parameters |
Where-Object { $_.Name.VariablePath.UserPath -eq "BuildOnly" } |
Select-Object -First 1

if (-not $buildOnlyParameter) {
    throw "Expected existing -BuildOnly switch to remain available for Python wheel-only workflows."
}

$cratesParameter = $paramBlock.Parameters |
Where-Object { $_.Name.VariablePath.UserPath -eq "Crates" } |
Select-Object -First 1

if (-not $cratesParameter) {
    throw "Expected positional crate/module filter parameter to remain available."
}

$cratesParameterAttr = $cratesParameter.Attributes |
Where-Object { $_.TypeName.Name -eq "Parameter" } |
Select-Object -First 1

$cratesParameterText = $cratesParameter.Extent.Text

$cratesHasRemainingArgsLiteral =
$cratesParameterText -match 'ValueFromRemainingArguments\s*=\s*\$true'

$cratesHasPositionZeroLiteral =
$cratesParameterText -match "Position\s*=\s*0"

$cratesPositionalNamedArg = $cratesParameterAttr.NamedArguments |
Where-Object { $_.ArgumentName -eq "Position" } |
Select-Object -First 1

$cratesPositionalValueIsZero = $false
if ($cratesPositionalNamedArg) {
    if ($cratesPositionalNamedArg.Argument -is [System.Management.Automation.Language.ConstantExpressionAst]) {
        $cratesPositionalValueIsZero = [int]$cratesPositionalNamedArg.Argument.Value -eq 0
    }
    else {
        $cratesPositionalValueIsZero = $cratesPositionalNamedArg.Argument.Extent.Text -eq "0"
    }
}

$cratesRemainingArg = $cratesParameterAttr.NamedArguments |
Where-Object { $_.ArgumentName -eq "ValueFromRemainingArguments" } |
Select-Object -First 1

$cratesAcceptsRemaining = $false
if ($cratesRemainingArg) {
    if ($cratesRemainingArg.Argument -is [System.Management.Automation.Language.ConstantExpressionAst]) {
        $cratesAcceptsRemaining = [bool]$cratesRemainingArg.Argument.Value
    }
    else {
        $cratesAcceptsRemaining = $cratesRemainingArg.Argument.Extent.Text -eq "$true"
    }
}

if ((-not $cratesAcceptsRemaining) -and (-not $cratesHasRemainingArgsLiteral)) {
    throw "Expected -Crates to keep ValueFromRemainingArguments for backward-compatible positional filters."
}

if ((-not $cratesPositionalValueIsZero) -and (-not $cratesHasPositionZeroLiteral)) {
    throw "Expected -Crates to stay at Position=0 for backward-compatible positional filters."
}

$debugBuildParameter = $paramBlock.Parameters |
Where-Object { $_.Name.VariablePath.UserPath -eq "DebugBuild" } |
Select-Object -First 1

if (-not $debugBuildParameter) {
    throw "Expected -DebugBuild switch for debug-oriented workspace/node rebuilds."
}

Write-Host "PASS: rebuild_rust.ps1 exposes general-purpose target selection metadata."
