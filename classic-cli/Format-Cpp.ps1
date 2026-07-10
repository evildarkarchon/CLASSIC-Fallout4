[CmdletBinding()]
param(
    [string] $Root = $PSScriptRoot
)

$ErrorActionPreference = 'Stop'

$rootPath = (Resolve-Path -LiteralPath $Root).ProviderPath

$formatExtensions = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($extension in @('.cc', '.cpp', '.h', '.hpp')) {
    [void] $formatExtensions.Add($extension)
}

$excludedDirectoryNames = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($directoryName in @('TES5Edit', 'tests', 'build', 'CMakeFiles', 'Testing', 'vcpkg_installed')) {
    [void] $excludedDirectoryNames.Add($directoryName)
}

function Get-FormatCppFile {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Directory
    )

    foreach ($entry in Get-ChildItem -LiteralPath $Directory -Force) {
        if ($entry.PSIsContainer) {
            if ($excludedDirectoryNames.Contains($entry.Name)) {
                continue
            }

            Get-FormatCppFile -Directory $entry.FullName
            continue
        }

        if ($formatExtensions.Contains($entry.Extension)) {
            $entry
        }
    }
}

$formattedCount = 0

foreach ($file in Get-FormatCppFile -Directory $rootPath) {
    $relativePath = [System.IO.Path]::GetRelativePath($rootPath, $file.FullName)
    Write-Host "Formatting $relativePath"

    & clang-format -i $file.FullName
    if ($LASTEXITCODE -ne 0) {
        throw "clang-format failed for '$relativePath' with exit code $LASTEXITCODE."
    }

    $formattedCount++
}

Write-Host "Formatted $formattedCount file(s)."
