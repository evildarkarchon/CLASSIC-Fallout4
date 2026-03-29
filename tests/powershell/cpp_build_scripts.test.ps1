param(
    [string]$GuiBuildScriptPath = (Join-Path (Join-Path $PSScriptRoot "../..") "classic-gui/build_gui.ps1"),
    [string]$CliBuildScriptPath = (Join-Path (Join-Path $PSScriptRoot "../..") "classic-cli/build_cli.ps1"),
    [string]$CliIntegrationScriptPath = (Join-Path (Join-Path $PSScriptRoot "../..") "classic-cli/test_cli.ps1")
)

$ErrorActionPreference = "Stop"

function Get-ScriptAst {
    param([string]$ScriptPath)

    if (-not (Test-Path $ScriptPath)) {
        throw "Expected script at '$ScriptPath'."
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

    return $ast
}

function Get-ParameterNames {
    param([System.Management.Automation.Language.Ast]$Ast)

    if (-not $Ast.ParamBlock) {
        throw "Expected script-level param block."
    }

    return @($Ast.ParamBlock.Parameters | ForEach-Object { $_.Name.VariablePath.UserPath })
}

$guiAst = Get-ScriptAst -ScriptPath $GuiBuildScriptPath
$guiText = Get-Content -Path (Resolve-Path $GuiBuildScriptPath) -Raw
$guiParamNames = Get-ParameterNames -Ast $guiAst

foreach ($parameterName in @("CTestName", "CTestArgs")) {
    if ($parameterName -notin $guiParamNames) {
        throw "Expected classic-gui/build_gui.ps1 to expose -$parameterName for selective CTest execution."
    }
}

if ($guiText -notmatch "ctest[\s\S]*-R") {
    throw "Expected classic-gui/build_gui.ps1 to pass a CTest name filter via -R when -CTestName is provided."
}

if ($guiText -notmatch '\$ctestRunArgs\s*\+=\s*\$CTestArgs') {
    throw "Expected classic-gui/build_gui.ps1 to forward -CTestArgs to the CTest invocation."
}

$cliAst = Get-ScriptAst -ScriptPath $CliBuildScriptPath
$cliText = Get-Content -Path (Resolve-Path $CliBuildScriptPath) -Raw
$cliParamNames = Get-ParameterNames -Ast $cliAst

foreach ($parameterName in @("CTestName", "CTestArgs", "IntegrationTestName")) {
    if ($parameterName -notin $cliParamNames) {
        throw "Expected classic-cli/build_cli.ps1 to expose -$parameterName for selective test execution."
    }
}

if ($cliText -notmatch "ctest[\s\S]*-R") {
    throw "Expected classic-cli/build_cli.ps1 to pass a CTest name filter via -R when -CTestName is provided."
}

if ($cliText -notmatch '\$ctestRunArgs\s*\+=\s*\$CTestArgs') {
    throw "Expected classic-cli/build_cli.ps1 to forward -CTestArgs to the CTest invocation."
}

if ($cliText -notmatch '&\s*\$integrationScript[\s\S]*-TestName\s+\$IntegrationTestName') {
    throw "Expected classic-cli/build_cli.ps1 to forward -IntegrationTestName to classic-cli/test_cli.ps1."
}

$integrationAst = Get-ScriptAst -ScriptPath $CliIntegrationScriptPath
$integrationText = Get-Content -Path (Resolve-Path $CliIntegrationScriptPath) -Raw
$integrationParamNames = Get-ParameterNames -Ast $integrationAst

if ("TestName" -notin $integrationParamNames) {
    throw "Expected classic-cli/test_cli.ps1 to expose -TestName for selective integration scenarios."
}

if ($integrationText -notmatch "Should-RunScenario") {
    throw "Expected classic-cli/test_cli.ps1 to gate scenarios through a Should-RunScenario helper."
}

foreach ($scenarioName in @("help", "version", "single-scan", "multi-scan", "max-concurrent", "empty-dir", "invalid-game", "report-content")) {
    if ($integrationText -notmatch [regex]::Escape($scenarioName)) {
        throw "Expected classic-cli/test_cli.ps1 to advertise '$scenarioName' as a selectable integration scenario name."
    }
}

Write-Host "PASS: C++ PowerShell build scripts expose selective test execution metadata."
