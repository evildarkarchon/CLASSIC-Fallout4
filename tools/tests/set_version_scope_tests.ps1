#Requires -Version 5.1
$ErrorActionPreference = "Stop"

function Assert-Contains {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Haystack,

        [Parameter(Mandatory = $true)]
        [string]$Needle
    )

    if (-not $Haystack.Contains($Needle)) {
        throw "Expected output to contain: $Needle"
    }
}

$RepoRoot = Resolve-Path (Join-Path (Join-Path $PSScriptRoot "..") "..")
$SourceScript = Join-Path $RepoRoot "set_version.ps1"
$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("classic-set-version-test-" + [System.Guid]::NewGuid().ToString("N"))
$CargoDir = [System.IO.Path]::Combine($TempRoot, "foundation", "sample")
$YamlDir = [System.IO.Path]::Combine($TempRoot, "CLASSIC Data", "databases")
$YamlPath = Join-Path $YamlDir "CLASSIC Main.yaml"

try {
    New-Item -ItemType Directory -Path $TempRoot | Out-Null
    New-Item -ItemType Directory -Path $CargoDir -Force | Out-Null
    New-Item -ItemType Directory -Path $YamlDir -Force | Out-Null

    Copy-Item -Path $SourceScript -Destination (Join-Path $TempRoot "set_version.ps1")

    @'
[package]
name = "sample"
version = "0.1.0"
'@ | Set-Content -Path (Join-Path $CargoDir "Cargo.toml") -Encoding UTF8

    @'
schema_version: "2.0"

CLASSIC_Info:
  version: v9.1.0
  version_date: 26.04.19
  is_prerelease: false

Game_Data:
  Fallout4:
    version: "1.10.163.0"
    script_extender:
      versions:
        - version: "1.37.0"
    compatible_version: "0.6.23"
'@ | Set-Content -Path $YamlPath -Encoding UTF8

    $ScriptUnderTest = Join-Path $TempRoot "set_version.ps1"
    & $ScriptUnderTest -Version "9.2.0" -Date "26.05.01" -IsPrerelease $true | Out-Host

    $UpdatedYaml = Get-Content -Path $YamlPath -Raw -Encoding UTF8

    Assert-Contains -Haystack $UpdatedYaml -Needle "  version: v9.2.0"
    Assert-Contains -Haystack $UpdatedYaml -Needle "  version_date: 26.05.01"
    Assert-Contains -Haystack $UpdatedYaml -Needle "  is_prerelease: true"
    Assert-Contains -Haystack $UpdatedYaml -Needle '    version: "1.10.163.0"'
    Assert-Contains -Haystack $UpdatedYaml -Needle '        - version: "1.37.0"'
    Assert-Contains -Haystack $UpdatedYaml -Needle '    compatible_version: "0.6.23"'

    Write-Host "set_version.ps1 YAML scope regression passed."
}
finally {
    if (Test-Path $TempRoot) {
        Remove-Item -Path $TempRoot -Recurse -Force
    }
}
