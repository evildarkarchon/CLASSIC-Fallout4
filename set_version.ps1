#Requires -Version 5.1
<#
.SYNOPSIS
    Sets the MAJOR.MINOR.PATCH version for all CLASSIC Rust crates and the main YAML database file.

.DESCRIPTION
    This script updates the version number across all Cargo.toml files in the
    Rust layer directories (foundation/, business-logic/, cpp-bindings/,
    node-bindings/, python-bindings/, ui-applications/), the
    CLASSIC Data/databases/CLASSIC Main.yaml file, and the CMake project
    version lines in classic-cli/CMakeLists.txt and classic-gui/CMakeLists.txt.

    CLASSIC ships release-only SemVer: `CLASSIC_Info.version` is always a
    bare MAJOR.MINOR.PATCH (optionally prefixed by a literal `v`). SemVer
    prerelease suffixes (e.g. `-beta.N`, `-rc.N`, `-alpha`) and build
    metadata (e.g. `+build.N`) are forbidden in the YAML field and in this
    script's `-Version` argument. Prerelease status is signaled instead via
    `-IsPrerelease $true` (which writes `is_prerelease: true` to the YAML)
    paired with a bumped `-Date`; the publish workflow mirrors the same
    boolean through `gh release --prerelease=true/false`. See the
    `yaml-app-version-field` capability spec
    (openspec/specs/yaml-app-version-field/spec.md) for the normative
    contract.

    The CLI's CMakeLists configures a build-time guard that compares its
    project(VERSION) against CLASSIC_Info.version in CLASSIC Main.yaml; this
    script bumps both in lockstep so the guard keeps passing. The CMake
    writer still strips any `-...` / `+...` suffix as defense-in-depth, but
    the `-Version` parameter validator now rejects suffixed input upstream,
    so the strip is no longer on the happy path.

.PARAMETER Version
    The new version number as a bare MAJOR.MINOR.PATCH triple (e.g., "9.2.0").
    SemVer prerelease suffixes (`-beta.N`, `-rc.N`) and build metadata
    (`+build.N`) are rejected at parameter binding — use `-IsPrerelease $true`
    plus a bumped `-Date` to signal a prerelease publish. The YAML writer
    prepends a literal "v" to this value (e.g., `v9.2.0`); the legacy
    "CLASSIC " display prefix was dropped in schema_version 2.0.

.PARAMETER Date
    Optional. The version date in YY.MM.DD format. If not provided, today's date will be used.

.PARAMETER IsPrerelease
    Optional. Set to $true to mark the publish as a prerelease; writes
    `is_prerelease: true` to CLASSIC Main.yaml. The version string itself
    stays a bare MAJOR.MINOR.PATCH — never add a SemVer suffix.

.EXAMPLE
    .\set_version.ps1 -Version "9.2.0"
    Updates all files to version 9.2.0 (stable) with today's date.

.EXAMPLE
    .\set_version.ps1 -Version "9.2.0" -Date "26.05.01" -IsPrerelease $true
    Publishes 9.2.0 as a prerelease on 2026-05-01. Writes
    `CLASSIC_Info.version: v9.2.0`, `version_date: 26.05.01`,
    `is_prerelease: true` to CLASSIC Main.yaml; no SemVer suffix is
    written anywhere.

.NOTES
    File paths are relative to the script execution directory.
    The script will create backups of modified files in the version_backups/ directory
    before making changes.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $false, Position = 0, HelpMessage = "Version number (e.g., 9.2.0) — bare MAJOR.MINOR.PATCH only, no leading zeros")]
    # Strict SemVer §2 numeric identifiers: each of MAJOR/MINOR/PATCH is
    # either a bare `0` or a 1-9-led digit string. Leading zeros
    # (`01.2.3`, `1.02.3`) are rejected here so the producer agrees with
    # `validate_release_semver_shape()` on the consumer side — otherwise
    # a bumped YAML value would slip past this script and then crash the
    # runtime loader with `MainYamlVersionError::VersionInvalid`.
    [ValidatePattern('^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$')]
    [string]$Version,

    [Parameter(Mandatory = $false, HelpMessage = "Version date in YY.MM.DD format")]
    [ValidatePattern('^\d{2}\.\d{2}\.\d{2}$')]
    [string]$Date = (Get-Date -Format "yy.MM.dd"),

    [Parameter(Mandatory = $false, HelpMessage = "Mark as prerelease")]
    [bool]$IsPrerelease = $false,

    [Parameter(Mandatory = $false, HelpMessage = "Show help information")]
    [switch]$Help
)

# Error handling
$ErrorActionPreference = "Stop"

# =============================================================================
# HELP DISPLAY
# =============================================================================

function Show-Help {
    @"
NAME
    set_version.ps1

SYNOPSIS
    Sets the MAJOR.MINOR.PATCH version for all CLASSIC Rust crates and the main YAML database file.

SYNTAX
    .\set_version.ps1 [-Version] <string> [[-Date] <string>] [[-IsPrerelease] <bool>] [-WhatIf] [-Confirm]
    .\set_version.ps1 -Help

DESCRIPTION
    This script updates the version number across all Cargo.toml files in the
    Rust layer directories (foundation/, business-logic/, cpp-bindings/,
    node-bindings/, python-bindings/, ui-applications/), the
    CLASSIC Data/databases/CLASSIC Main.yaml file, and the CMake project
    version lines in classic-cli/CMakeLists.txt and classic-gui/CMakeLists.txt.

    CLASSIC ships release-only SemVer: CLASSIC_Info.version is always a
    bare MAJOR.MINOR.PATCH (optionally prefixed by a literal ``v``). SemVer
    prerelease suffixes (``-beta.N``, ``-rc.N``, ``-alpha``) and build
    metadata (``+build.N``) are forbidden in the YAML field and in this
    script's -Version argument. Prerelease status is signaled instead via
    -IsPrerelease ``$true`` (which writes ``is_prerelease: true`` to the
    YAML) paired with a bumped -Date; the publish workflow mirrors the
    same boolean through ``gh release --prerelease=true/false``. See the
    yaml-app-version-field capability spec
    (openspec/specs/yaml-app-version-field/spec.md) for the normative
    contract.

    The CLI's CMakeLists configures a build-time guard that compares its
    project(VERSION) against CLASSIC_Info.version in CLASSIC Main.yaml; this
    script bumps both in lockstep so the guard keeps passing. The CMake
    writer still strips any ``-...`` / ``+...`` suffix as defense-in-depth,
    but the -Version parameter validator now rejects suffixed input
    upstream, so the strip is no longer on the happy path.

PARAMETERS
    -Version <string>
        The new version number as a bare MAJOR.MINOR.PATCH triple (e.g., "9.2.0").
        SemVer prerelease suffixes (``-beta.N``, ``-rc.N``) and build metadata
        (``+build.N``) are rejected at parameter binding — use -IsPrerelease
        ``$true`` plus a bumped -Date to signal a prerelease publish. The
        YAML writer prepends a literal "v" (e.g., ``v9.2.0``).
        Required unless -Help is specified.

    -Date <string>
        Optional. The version date in YY.MM.DD format.
        If not provided, today's date will be used.

    -IsPrerelease <bool>
        Optional. Set to ``$true`` to mark the publish as a prerelease;
        writes ``is_prerelease: true`` to CLASSIC Main.yaml. The version
        string itself stays a bare MAJOR.MINOR.PATCH — never add a SemVer
        suffix.
        Default: ``$false``

    -WhatIf
        Shows what would happen if the script runs without making changes.

    -Confirm
        Prompts for confirmation before making changes.

    -Help
        Displays this help information.

EXAMPLES
    .\set_version.ps1 -Version "9.2.0"
        Updates all files to version 9.2.0 (stable) with today's date.

    .\set_version.ps1 -Version "9.2.0" -Date "26.05.01" -IsPrerelease ``$true
        Publishes 9.2.0 as a prerelease on 2026-05-01. Writes
        CLASSIC_Info.version: v9.2.0, version_date: 26.05.01, and
        is_prerelease: true to CLASSIC Main.yaml; no SemVer suffix is
        written anywhere.

    .\set_version.ps1 -Version "9.3.0" -WhatIf
        Shows what changes would be made without actually modifying files.

NOTES
    File paths are relative to the script execution directory.
    The script will create backups of modified files before making changes.
    Backup files are stored in the version_backups/ directory with the naming format:
    <filename>.backup.<timestamp>

"@
}

# Check for Help parameter first
if ($Help) {
    Show-Help
    exit 0
}

# Validate that Version is provided when not using Help
if (-not $Version) {
    Write-Error "The -Version parameter is required. Use -Help for usage information."
    exit 1
}

# =============================================================================
# CONFIGURATION
# =============================================================================

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = if ($ScriptDir) { $ScriptDir } else { "." }

# Paths relative to root directory
# Rust crates live under repo-root layer directories after the ClassicLib-rs
# migration; see docs/workspace-migration-matrix.md.
$RustLayerDirs = @(
    (Join-Path $RootDir "foundation"),
    (Join-Path $RootDir "business-logic"),
    (Join-Path $RootDir "cpp-bindings"),
    (Join-Path $RootDir "node-bindings"),
    (Join-Path $RootDir "python-bindings"),
    (Join-Path $RootDir "ui-applications")
)
$YamlFile = Join-Path $RootDir "CLASSIC Data" "databases" "CLASSIC Main.yaml"
# CMake project files whose `project(... VERSION x.y.z ...)` line tracks the
# application version. The CLI's CMakeLists has a build-time guard that
# compares this value against CLASSIC_Info.version in CLASSIC Main.yaml,
# so the two MUST stay in lockstep — the script bumps both together. The
# GUI's CMake project version is also kept aligned for uniform packaging.
# Hardcoded (rather than discovered via Get-ChildItem -Recurse) so we never
# accidentally rewrite unrelated CMakeLists.txt files in subdirectories.
$CMakeListsFiles = @(
    (Join-Path $RootDir "classic-cli" "CMakeLists.txt"),
    (Join-Path $RootDir "classic-gui" "CMakeLists.txt")
)
$BackupDir = Join-Path $RootDir "version_backups"

# =============================================================================
# FUNCTIONS
# =============================================================================

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-WarningCustom {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-ErrorCustom {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Backup-File {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(Mandatory = $true)]
        [string]$BackupDirectory
    )

    if (-not (Test-Path $FilePath)) {
        return
    }

    # Create backup directory if it doesn't exist
    if (-not (Test-Path $BackupDirectory)) {
        try {
            New-Item -ItemType Directory -Path $BackupDirectory -Force | Out-Null
        }
        catch {
            Write-ErrorCustom "Failed to create backup directory: $BackupDirectory"
            throw
        }
    }

    $FileName = [System.IO.Path]::GetFileName($FilePath)
    $BackupPath = Join-Path $BackupDirectory "$FileName.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    try {
        Copy-Item -Path $FilePath -Destination $BackupPath -Force
        Write-Info "Created backup: $BackupPath"
        return $BackupPath
    }
    catch {
        Write-ErrorCustom "Failed to create backup for: $FilePath"
        throw
    }
}

function Update-CargoToml {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(Mandatory = $true)]
        [string]$NewVersion
    )

    if (-not (Test-Path $FilePath)) {
        Write-WarningCustom "File not found: $FilePath"
        return $false
    }

    try {
        $Content = Get-Content -Path $FilePath -Raw -Encoding UTF8
        $OriginalContent = $Content

        # Pattern to match version = "X.Y.Z" in [package] section
        # This regex matches: version = "any version" (with optional whitespace)
        $Pattern = '(?m)^(\s*version\s*=\s*)"[^"]*"'
        $Replacement = '${1}"' + $NewVersion + '"'

        $NewContent = $Content -replace $Pattern, $Replacement

        if ($NewContent -eq $OriginalContent) {
            Write-WarningCustom "No version field found or already up to date in: $FilePath"
            return $false
        }

        if ($PSCmdlet.ShouldProcess($FilePath, "Update version to $NewVersion")) {
            Backup-File -FilePath $FilePath -BackupDirectory $BackupDir
            Set-Content -Path $FilePath -Value $NewContent -NoNewline -Encoding UTF8
            Write-Success "Updated: $FilePath"
        }
        return $true
    }
    catch {
        Write-ErrorCustom "Failed to update $FilePath : $_"
        throw
    }
}

function Update-YamlFile {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(Mandatory = $true)]
        [string]$NewVersion,

        [Parameter(Mandatory = $true)]
        [string]$NewDate,

        [Parameter(Mandatory = $true)]
        [bool]$Prerelease
    )

    if (-not (Test-Path $FilePath)) {
        Write-WarningCustom "YAML file not found: $FilePath"
        return $false
    }

    try {
        $Content = Get-Content -Path $FilePath -Raw -Encoding UTF8
        $OriginalContent = $Content

        # Update CLASSIC_Info.version line: version: v<X.Y.Z>
        # The pattern is anchored to the top-level CLASSIC_Info section so
        # game-specific `version:` fields elsewhere in the YAML are never
        # rewritten. It captures the section prefix and ONLY the "  version: "
        # prefix (non-capturing group tolerates legacy "CLASSIC v" / bare "v" /
        # no-prefix forms in the input so this script can upgrade a
        # pre-schema_version-2.0 YAML cleanly), and the replacement appends a
        # literal "v" before the version so output is always the schema_version
        # 2.0 canonical shape.
        #
        # NOTE: Use ${1} instead of $1 to disambiguate backreference from
        # version digits (e.g., "$1" + "9.0.0" = "$19.0.0" which .NET
        # interprets as group 19, corrupting the output).
        $VersionPattern = '(?m)(^CLASSIC_Info:[^\r\n]*(?:\r?\n(?!\S)[^\r\n]*)*?\r?\n)([ \t]*version:[ \t]*)(?:CLASSIC[ \t]+v|v)?[^\r\n]*'
        $VersionReplacement = '${1}${2}v' + $NewVersion
        $NewContent = $Content -replace $VersionPattern, $VersionReplacement

        # Update version_date line: version_date: YY.MM.DD
        $DatePattern = '(?m)^(\s*version_date:\s*)\d{2}\.\d{2}\.\d{2}'
        $DateReplacement = '${1}' + $NewDate
        $NewContent = $NewContent -replace $DatePattern, $DateReplacement

        # Update is_prerelease line: is_prerelease: true/false
        $PrereleasePattern = '(?m)^(\s*is_prerelease:\s*)\w+'
        $PrereleaseValue = if ($Prerelease) { "true" } else { "false" }
        $PrereleaseReplacement = '${1}' + $PrereleaseValue
        $NewContent = $NewContent -replace $PrereleasePattern, $PrereleaseReplacement

        if ($NewContent -eq $OriginalContent) {
            Write-WarningCustom "No changes needed in YAML file: $FilePath"
            return $false
        }

        if ($PSCmdlet.ShouldProcess($FilePath, "Update version to $NewVersion, date to $NewDate, prerelease to $PrereleaseValue")) {
            Backup-File -FilePath $FilePath -BackupDirectory $BackupDir
            Set-Content -Path $FilePath -Value $NewContent -NoNewline -Encoding UTF8
            Write-Success "Updated YAML: $FilePath"
        }
        return $true
    }
    catch {
        Write-ErrorCustom "Failed to update YAML file $FilePath : $_"
        throw
    }
}

function Update-CMakeListsTxt {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(Mandatory = $true)]
        [string]$NewVersion
    )

    if (-not (Test-Path $FilePath)) {
        Write-WarningCustom "CMakeLists.txt not found: $FilePath"
        return $false
    }

    # CMake's `project(... VERSION ...)` only accepts MAJOR.MINOR.PATCH
    # (or an optional .TWEAK fourth component) — SemVer pre-release/build
    # suffixes like `-beta.1` or `+build.5` are rejected by `project()`.
    # Defense-in-depth: the `-Version` parameter's `[ValidatePattern]` now
    # enforces a bare MAJOR.MINOR.PATCH triple upstream (per the
    # `yaml-app-version-field` capability spec, which forbids SemVer
    # prerelease/build suffixes on `CLASSIC_Info.version`), so no suffix
    # should ever reach this line via the normal CLI entry point. The
    # strip remains as a safety net for callers that dot-source this file
    # and invoke `Update-CMakeListsTxt` directly.
    $CMakeVersion = $NewVersion -replace '[-+].*$', ''

    try {
        $Content = Get-Content -Path $FilePath -Raw -Encoding UTF8
        $OriginalContent = $Content

        # Match `project(<name> VERSION <X.Y.Z>[.tweak]<trailing>)`. The
        # lazy `[^\)]*?` keeps the project-name + VERSION-keyword span
        # minimal so we never reach into a different `project(...)` call.
        # Group 1: leading (project + name + VERSION ).
        # Group 2: optional `.tweak` (deliberately dropped on rewrite —
        #          callers supply 3-part SemVer so we collapse to that).
        # Group 3: trailing args + close paren (e.g. ` LANGUAGES CXX)`).
        # Use ${N} backreferences in the replacement to avoid the
        # `$1<digits>` parsing ambiguity called out in Update-YamlFile.
        $Pattern = '(?m)^(\s*project\s*\([^\)]*?VERSION\s+)\d+\.\d+\.\d+(\.\d+)?((?:\s+[^\)]*)?\))'
        $Replacement = '${1}' + $CMakeVersion + '${3}'

        $NewContent = $Content -replace $Pattern, $Replacement

        if ($NewContent -eq $OriginalContent) {
            Write-WarningCustom "No project(VERSION ...) line found or already up to date in: $FilePath"
            return $false
        }

        if ($PSCmdlet.ShouldProcess($FilePath, "Update project VERSION to $CMakeVersion")) {
            Backup-File -FilePath $FilePath -BackupDirectory $BackupDir
            Set-Content -Path $FilePath -Value $NewContent -NoNewline -Encoding UTF8
            Write-Success "Updated CMake: $FilePath -> project(VERSION $CMakeVersion)"
        }
        return $true
    }
    catch {
        Write-ErrorCustom "Failed to update CMakeLists.txt $FilePath : $_"
        throw
    }
}

function Get-CargoTomlFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Directory
    )

    if (-not (Test-Path $Directory)) {
        Write-WarningCustom "Directory not found: $Directory"
        return @()
    }

    $CargoFiles = Get-ChildItem -Path $Directory -Recurse -Filter "Cargo.toml" -File
    return $CargoFiles
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host "  CLASSIC Version Update Script" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

Write-Info "Target Version: $Version"
Write-Info "Target Date: $Date"
Write-Info "Is Prerelease: $IsPrerelease"
Write-Info "Working Directory: $(Resolve-Path $RootDir)"
Write-Host ""

# Validate paths: at least one Rust layer directory must exist
$ExistingRustLayerDirs = @($RustLayerDirs | Where-Object { Test-Path $_ })
if ($ExistingRustLayerDirs.Count -eq 0) {
    Write-ErrorCustom "No Rust layer directories found. Expected one or more of:"
    foreach ($Dir in $RustLayerDirs) {
        Write-ErrorCustom "  $Dir"
    }
    exit 1
}

$MissingRustLayerDirs = @($RustLayerDirs | Where-Object { -not (Test-Path $_) })
foreach ($Dir in $MissingRustLayerDirs) {
    Write-WarningCustom "Rust layer directory not found (skipping): $Dir"
}

# Track statistics
$Stats = @{
    CargoFilesUpdated = 0
    CargoFilesSkipped = 0
    YamlUpdated       = $false
    YamlSkipped       = $false
    CMakeFilesUpdated = 0
    CMakeFilesSkipped = 0
}

# =============================================================================
# UPDATE CARGO.TOML FILES
# =============================================================================

Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Info "Scanning for Cargo.toml files..."
Write-Host ""

$CargoFiles = @()
foreach ($Dir in $ExistingRustLayerDirs) {
    $LayerFiles = Get-CargoTomlFiles -Directory $Dir
    if ($LayerFiles.Count -gt 0) {
        $CargoFiles += $LayerFiles
    }
}

if ($CargoFiles.Count -eq 0) {
    Write-WarningCustom "No Cargo.toml files found in Rust layer directories:"
    foreach ($Dir in $ExistingRustLayerDirs) {
        Write-WarningCustom "  $Dir"
    }
}
else {
    Write-Info "Found $($CargoFiles.Count) Cargo.toml file(s)"
    Write-Host ""

    foreach ($File in $CargoFiles) {
        $RelativePath = $File.FullName.Substring((Resolve-Path $RootDir).Path.Length + 1)
        Write-Info "Processing: $RelativePath"

        $Updated = Update-CargoToml -FilePath $File.FullName -NewVersion $Version

        if ($Updated) {
            $Stats.CargoFilesUpdated++
        }
        else {
            $Stats.CargoFilesSkipped++
        }
    }
}

Write-Host ""

# =============================================================================
# UPDATE YAML FILE
# =============================================================================

Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Info "Processing YAML database file..."
Write-Host ""

if (Test-Path $YamlFile) {
    $RelativeYamlPath = $YamlFile.Substring((Resolve-Path $RootDir).Path.Length + 1)
    Write-Info "Processing: $RelativeYamlPath"

    $Updated = Update-YamlFile -FilePath $YamlFile -NewVersion $Version -NewDate $Date -Prerelease $IsPrerelease

    if ($Updated) {
        $Stats.YamlUpdated = $true
    }
    else {
        $Stats.YamlSkipped = $true
    }
}
else {
    Write-WarningCustom "YAML file not found: $YamlFile"
    $Stats.YamlSkipped = $true
}

Write-Host ""

# =============================================================================
# UPDATE CMAKELISTS.TXT FILES
# =============================================================================

Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Info "Processing CMakeLists.txt project versions..."
Write-Host ""

foreach ($CMakePath in $CMakeListsFiles) {
    if (Test-Path $CMakePath) {
        $RelativeCMakePath = $CMakePath.Substring((Resolve-Path $RootDir).Path.Length + 1)
        Write-Info "Processing: $RelativeCMakePath"

        $Updated = Update-CMakeListsTxt -FilePath $CMakePath -NewVersion $Version

        if ($Updated) {
            $Stats.CMakeFilesUpdated++
        }
        else {
            $Stats.CMakeFilesSkipped++
        }
    }
    else {
        Write-WarningCustom "CMakeLists.txt not found (skipping): $CMakePath"
        $Stats.CMakeFilesSkipped++
    }
}

Write-Host ""

# =============================================================================
# SUMMARY
# =============================================================================

Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Host "  SUMMARY" -ForegroundColor Blue
Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Host ""

Write-Host "Cargo.toml Files:"
Write-Host "  Updated: $($Stats.CargoFilesUpdated)" -ForegroundColor Green
Write-Host "  Skipped: $($Stats.CargoFilesSkipped)" -ForegroundColor Yellow
Write-Host ""

Write-Host "YAML Database File:"
if ($Stats.YamlUpdated) {
    Write-Host "  Status: Updated" -ForegroundColor Green
}
elseif ($Stats.YamlSkipped) {
    Write-Host "  Status: Skipped or Not Found" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "CMakeLists.txt Files:"
Write-Host "  Updated: $($Stats.CMakeFilesUpdated)" -ForegroundColor Green
Write-Host "  Skipped: $($Stats.CMakeFilesSkipped)" -ForegroundColor Yellow
Write-Host ""

Write-Success "Version update completed!"
Write-Host ""
Write-Host "Note: Backup files were created in: $BackupDir" -ForegroundColor DarkGray
Write-Host "      You can remove them once you've verified the changes." -ForegroundColor DarkGray
Write-Host ""

# Return exit code based on success
if ($Stats.CargoFilesUpdated -gt 0 -or $Stats.YamlUpdated -or $Stats.CMakeFilesUpdated -gt 0) {
    exit 0
}
else {
    exit 1
}
