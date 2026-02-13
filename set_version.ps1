#Requires -Version 5.1
<#
.SYNOPSIS
    Sets the version number for all CLASSIC Rust crates and the main YAML database file.

.DESCRIPTION
    This script updates the version number across all Cargo.toml files in the rust directory
    and in the CLASSIC Data/databases/CLASSIC Main.yaml file.

.PARAMETER Version
    The new version number in semantic versioning format (e.g., "8.1.0", "8.2.0-beta.1").
    For the YAML file, this will be prefixed with "CLASSIC v".

.PARAMETER Date
    Optional. The version date in YY.MM.DD format. If not provided, today's date will be used.

.PARAMETER IsPrerelease
    Optional. Set to $true if this is a prerelease version (affects YAML is_prerelease field).

.EXAMPLE
    .\set_version.ps1 -Version "8.2.0"
    Updates all files to version 8.2.0 with today's date.

.EXAMPLE
    .\set_version.ps1 -Version "8.2.0-beta.1" -Date "26.01.28" -IsPrerelease $true
    Updates all files to version 8.2.0-beta.1 with specified date and prerelease flag.

.NOTES
    File paths are relative to the script execution directory.
    The script will create backups of modified files in the version_backups/ directory
    before making changes.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $false, Position = 0, HelpMessage = "Version number (e.g., 8.2.0)")]
    [ValidatePattern('^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$')]
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
    Sets the version number for all CLASSIC Rust crates and the main YAML database file.

SYNTAX
    .\set_version.ps1 [-Version] <string> [[-Date] <string>] [[-IsPrerelease] <bool>] [-WhatIf] [-Confirm]
    .\set_version.ps1 -Help

DESCRIPTION
    This script updates the version number across all Cargo.toml files in the rust directory
    and in the CLASSIC Data/databases/CLASSIC Main.yaml file.

PARAMETERS
    -Version <string>
        The new version number in semantic versioning format (e.g., "8.1.0", "8.2.0-beta.1").
        For the YAML file, this will be prefixed with "CLASSIC v".
        Required unless -Help is specified.

    -Date <string>
        Optional. The version date in YY.MM.DD format.
        If not provided, today's date will be used.

    -IsPrerelease <bool>
        Optional. Set to `$true` if this is a prerelease version
        (affects YAML is_prerelease field).
        Default: `$false`

    -WhatIf
        Shows what would happen if the script runs without making changes.

    -Confirm
        Prompts for confirmation before making changes.

    -Help
        Displays this help information.

EXAMPLES
    .\set_version.ps1 -Version "8.2.0"
        Updates all files to version 8.2.0 with today's date.

    .\set_version.ps1 -Version "8.2.0-beta.1" -Date "26.01.28" -IsPrerelease `$true
        Updates all files to version 8.2.0-beta.1 with specified date and prerelease flag.

    .\set_version.ps1 -Version "8.3.0" -WhatIf
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
$RustDir = Join-Path $RootDir "rust"
$YamlFile = Join-Path $RootDir "CLASSIC Data" "databases" "CLASSIC Main.yaml"
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

        # Update version line: version: CLASSIC vX.Y.Z
        # NOTE: Use ${1} instead of $1 to disambiguate backreference from
        # version digits (e.g., "$1" + "9.0.0" = "$19.0.0" which .NET
        # interprets as group 19, corrupting the output).
        $VersionPattern = '(?m)^(\s*version:\s*CLASSIC\s+v)[^\n\r]*'
        $VersionReplacement = '${1}' + $NewVersion
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

# Validate paths
if (-not (Test-Path $RustDir)) {
    Write-ErrorCustom "Rust directory not found: $RustDir"
    exit 1
}

# Track statistics
$Stats = @{
    CargoFilesUpdated = 0
    CargoFilesSkipped = 0
    YamlUpdated       = $false
    YamlSkipped       = $false
}

# =============================================================================
# UPDATE CARGO.TOML FILES
# =============================================================================

Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Info "Scanning for Cargo.toml files..."
Write-Host ""

$CargoFiles = Get-CargoTomlFiles -Directory $RustDir

if ($CargoFiles.Count -eq 0) {
    Write-WarningCustom "No Cargo.toml files found in: $RustDir"
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

Write-Success "Version update completed!"
Write-Host ""
Write-Host "Note: Backup files were created in: $BackupDir" -ForegroundColor DarkGray
Write-Host "      You can remove them once you've verified the changes." -ForegroundColor DarkGray
Write-Host ""

# Return exit code based on success
if ($Stats.CargoFilesUpdated -gt 0 -or $Stats.YamlUpdated) {
    exit 0
}
else {
    exit 1
}
