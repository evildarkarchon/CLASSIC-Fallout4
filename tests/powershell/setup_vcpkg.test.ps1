param(
    [string]$SetupScriptPath = (Join-Path (Join-Path $PSScriptRoot "../..") ".github/scripts/setup-vcpkg.ps1")
)

$ErrorActionPreference = "Stop"
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    (Resolve-Path -LiteralPath $SetupScriptPath).Path,
    [ref]$tokens,
    [ref]$parseErrors
)
if ($parseErrors.Count -gt 0) {
    throw "vcpkg setup script has a PowerShell parse error: $($parseErrors[0].Message)"
}

$probe = $ast.Find({
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $node.Name -eq "Test-VcpkgTool"
    }, $true)
if (-not $probe) {
    throw "Expected vcpkg setup to validate a cached tool before bootstrapping."
}

$runner = [scriptblock]::Create(@"
param([string]`$ToolPath)
$($probe.Extent.Text)
Test-VcpkgTool -ToolPath `$ToolPath
"@)
$gitPath = (Get-Command git.exe -ErrorAction Stop).Source
$pythonPath = (Get-Command python.exe -ErrorAction Stop).Source
if (-not (& $runner -ToolPath $gitPath)) {
    throw "Expected a cached executable with a successful version command to be reused."
}
if (& $runner -ToolPath $pythonPath) {
    throw "Expected a cached executable with a failed version command to be rejected."
}
if (& $runner -ToolPath (Join-Path $PSScriptRoot "missing-vcpkg.exe")) {
    throw "Expected a missing cached executable to be rejected."
}

Write-Host "PASS: vcpkg cache-hit validation accepts only a runnable tool."
