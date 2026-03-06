param(
    [string]$ScriptPath = (Join-Path $PSScriptRoot "../.." "tools/enter_vs_dev_shell.ps1")
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ScriptPath)) {
    throw "Expected VS Dev Shell wrapper script at '$ScriptPath'."
}

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
    throw "Expected script-level param block in tools/enter_vs_dev_shell.ps1."
}

$expectedParameters = @("Command", "WorkingDirectory", "Arch", "Interactive")

foreach ($parameterName in $expectedParameters) {
    $parameter = $paramBlock.Parameters |
        Where-Object { $_.Name.VariablePath.UserPath -eq $parameterName } |
        Select-Object -First 1

    if (-not $parameter) {
        throw "Expected tools/enter_vs_dev_shell.ps1 to expose -$parameterName."
    }
}

$archParameter = $paramBlock.Parameters |
    Where-Object { $_.Name.VariablePath.UserPath -eq "Arch" } |
    Select-Object -First 1

$validateSet = $archParameter.Attributes |
    Where-Object { $_.TypeName.Name -eq "ValidateSet" } |
    Select-Object -First 1

if (-not $validateSet) {
    throw "Expected -Arch to define a ValidateSet for supported Visual Studio architectures."
}

$actualArchValues = foreach ($arg in $validateSet.PositionalArguments) {
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

$expectedArchValues = @("amd64", "x86", "arm64")
$missingArchValues = $expectedArchValues | Where-Object { $_ -notin $actualArchValues }
if ($missingArchValues.Count -gt 0) {
    throw "Missing expected -Arch values: $($missingArchValues -join ', ')"
}

$scriptText = Get-Content -Path $resolvedScriptPath.Path -Raw

if ($scriptText -notmatch "vswhere\.exe") {
    throw "Expected tools/enter_vs_dev_shell.ps1 to locate Visual Studio via vswhere.exe."
}

if ($scriptText -notmatch "Launch-VsDevShell\.ps1") {
    throw "Expected tools/enter_vs_dev_shell.ps1 to launch the Visual Studio Dev Shell script."
}

if ($scriptText -notmatch "pwsh\s+-NoExit") {
    throw "Expected tools/enter_vs_dev_shell.ps1 to support launching an interactive PowerShell session in the initialized environment."
}

if ($scriptText -notmatch "Set-Location") {
    throw "Expected tools/enter_vs_dev_shell.ps1 to honor a requested working directory."
}

Write-Host "PASS: tools/enter_vs_dev_shell.ps1 exposes expected VS Dev Shell wrapper metadata."
