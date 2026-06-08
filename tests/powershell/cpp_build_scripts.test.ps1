param(
    [string]$GuiBuildScriptPath = (Join-Path (Join-Path $PSScriptRoot "../..") "classic-gui/build_gui.ps1"),
    [string]$CliBuildScriptPath = (Join-Path (Join-Path $PSScriptRoot "../..") "classic-cli/build_cli.ps1"),
    [string]$CliIntegrationScriptPath = (Join-Path (Join-Path $PSScriptRoot "../..") "classic-cli/test_cli.ps1"),
    [string]$CliCmakePath = (Join-Path (Join-Path $PSScriptRoot "../..") "classic-cli/CMakeLists.txt"),
    [string]$CliCmakePresetsPath = (Join-Path (Join-Path $PSScriptRoot "../..") "classic-cli/CMakePresets.json"),
    [string]$GuiCmakePath = (Join-Path (Join-Path $PSScriptRoot "../..") "classic-gui/CMakeLists.txt"),
    [string]$GuiCmakePresetsPath = (Join-Path (Join-Path $PSScriptRoot "../..") "classic-gui/CMakePresets.json"),
    [string]$TuiMainPath = (Join-Path (Join-Path $PSScriptRoot "../..") "ui-applications/classic-tui/src/main.rs")
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

function Invoke-TestNameNormalizer {
    param(
        [System.Management.Automation.Language.Ast]$Ast,
        [string[]]$TestNames,
        [string]$ScriptLabel
    )

    $normalizer = $Ast.Find({
            param($Node)
            $Node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $Node.Name -eq "Normalize-TestNameList"
        }, $true)

    if (-not $normalizer) {
        throw "Expected $ScriptLabel to define Normalize-TestNameList."
    }

    $runner = [scriptblock]::Create(@"
param([string[]]`$Names)
$($normalizer.Extent.Text)
Normalize-TestNameList -TestNames `$Names
"@)

    return @(& $runner -Names $TestNames)
}

function Assert-TestNameNormalizerAcceptsCommaLists {
    param(
        [System.Management.Automation.Language.Ast]$Ast,
        [string]$ScriptLabel
    )

    $actual = @(Invoke-TestNameNormalizer -Ast $Ast -ScriptLabel $ScriptLabel -TestNames @(
            "alpha,beta",
            " gamma ",
            "",
            "delta, epsilon"
        ))
    $expected = @("alpha", "beta", "gamma", "delta", "epsilon")

    if (($actual -join "`0") -ne ($expected -join "`0")) {
        throw "Expected $ScriptLabel to normalize comma-separated test names. Actual: $($actual -join ', ')"
    }
}

function Get-ConfigurePresetNames {
    param([string]$PresetsPath)

    if (-not (Test-Path $PresetsPath)) {
        throw "Expected CMake presets file at '$PresetsPath'."
    }

    $presetJson = Get-Content -Path (Resolve-Path $PresetsPath) -Raw | ConvertFrom-Json
    return @($presetJson.configurePresets | ForEach-Object { $_.name })
}

function Assert-ConfigurePresetsExist {
    param(
        [string[]]$ActualNames,
        [string[]]$ExpectedNames,
        [string]$PresetLabel
    )

    foreach ($expectedName in $ExpectedNames) {
        if ($expectedName -notin $ActualNames) {
            throw "Expected $PresetLabel to define configure preset '$expectedName'."
        }
    }
}

function Assert-BuildScriptSupportsCompilerSelection {
    param(
        [System.Management.Automation.Language.Ast]$Ast,
        [string]$ScriptText,
        [string]$ScriptLabel
    )

    $parameterNames = Get-ParameterNames -Ast $Ast
    if ("Compiler" -notin $parameterNames) {
        throw "Expected $ScriptLabel to expose -Compiler for selecting msvc or clang-cl."
    }

    if ($ScriptText -notmatch '\[ValidateSet\([^\)]*msvc[^\)]*clang-cl[^\)]*\)\]') {
        throw "Expected $ScriptLabel to validate -Compiler values as msvc and clang-cl."
    }

    if ($ScriptText -notmatch 'clang-cl\.exe') {
        throw "Expected $ScriptLabel to check clang-cl.exe availability when -Compiler clang-cl is selected."
    }

    if ($ScriptText -notmatch 'default-clang-cl') {
        throw "Expected $ScriptLabel to map clang-cl builds to clang-cl CMake presets."
    }

    if ($ScriptText -notmatch 'CXXFLAGS_x86_64-pc-windows-msvc' -or $ScriptText -notmatch '/EHsc') {
        throw "Expected $ScriptLabel to enable C++ exceptions for clang-cl Cargo cc-rs builds."
    }
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

Assert-TestNameNormalizerAcceptsCommaLists -Ast $guiAst -ScriptLabel "classic-gui/build_gui.ps1"
Assert-BuildScriptSupportsCompilerSelection -Ast $guiAst -ScriptText $guiText -ScriptLabel "classic-gui/build_gui.ps1"

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

Assert-TestNameNormalizerAcceptsCommaLists -Ast $cliAst -ScriptLabel "classic-cli/build_cli.ps1"
Assert-BuildScriptSupportsCompilerSelection -Ast $cliAst -ScriptText $cliText -ScriptLabel "classic-cli/build_cli.ps1"

$cliPresetNames = Get-ConfigurePresetNames -PresetsPath $CliCmakePresetsPath
Assert-ConfigurePresetsExist -ActualNames $cliPresetNames -ExpectedNames @(
    "default-clang-cl",
    "debug-clang-cl"
) -PresetLabel "classic-cli/CMakePresets.json"

$guiPresetNames = Get-ConfigurePresetNames -PresetsPath $GuiCmakePresetsPath
Assert-ConfigurePresetsExist -ActualNames $guiPresetNames -ExpectedNames @(
    "default-clang-cl",
    "debug-clang-cl",
    "system-fallback-clang-cl",
    "system-fallback-debug-clang-cl",
    "ci-clang-cl",
    "ci-debug-clang-cl"
) -PresetLabel "classic-gui/CMakePresets.json"

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

Assert-TestNameNormalizerAcceptsCommaLists -Ast $integrationAst -ScriptLabel "classic-cli/test_cli.ps1"

$cliCmake = Get-Content -Path (Resolve-Path $CliCmakePath) -Raw
$guiCmake = Get-Content -Path (Resolve-Path $GuiCmakePath) -Raw

foreach ($cmakeText in @($cliCmake, $guiCmake)) {
    if ($cmakeText -match 'ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include') {
        throw "Expected native CMake bridge include paths to stop referencing ClassicLib-rs/cpp-bindings/..."
    }
    if ($cmakeText -notmatch 'cpp-bindings/classic-cpp-bridge/include') {
        throw "Expected native CMake bridge include paths to use repo-root cpp-bindings/classic-cpp-bridge/include."
    }
}

$tuiMain = Get-Content -Path (Resolve-Path $TuiMainPath) -Raw
foreach ($required in @('env::args', '--version', '--help')) {
    if ($tuiMain -notmatch [regex]::Escape($required)) {
        throw "Expected classic-tui probe handling to mention '$required'."
    }
}

$probeIndex = $tuiMain.IndexOf('handle_cli_probe()')
$terminalSetupCallIndex = $tuiMain.IndexOf('TerminalStateGuard::enter()?')
$alternateScreenIndex = $tuiMain.IndexOf('EnterAlternateScreen')
$rawModeIndex = $tuiMain.IndexOf('enable_raw_mode()')
if ($probeIndex -lt 0 -or $terminalSetupCallIndex -lt 0 -or $alternateScreenIndex -lt 0 -or $rawModeIndex -lt 0) {
    throw "Expected classic-tui main.rs to contain probe handling and terminal setup markers."
}
if ($probeIndex -gt $terminalSetupCallIndex) {
    throw "Expected classic-tui CLI probe handling to run before alternate-screen or raw-mode setup."
}

Write-Host "PASS: C++ PowerShell build scripts expose selective test execution metadata."
