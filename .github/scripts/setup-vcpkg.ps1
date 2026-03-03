param(
    [string]$VcpkgRoot = "$env:USERPROFILE\vcpkg",
    [int]$BootstrapAttempts = 3,
    [int]$BaseBackoffSeconds = 2,
    [int]$FallbackCurlRetries = 5
)

$ErrorActionPreference = "Stop"

function Invoke-Bootstrap {
    param(
        [string]$Root,
        [int]$MaxAttempts,
        [int]$BackoffSeconds
    )

    $bootstrapBat = Join-Path $Root "bootstrap-vcpkg.bat"
    if (-not (Test-Path $bootstrapBat)) {
        throw "bootstrap-vcpkg.bat not found at '$bootstrapBat'."
    }

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        Write-Host "vcpkg bootstrap attempt $attempt/$MaxAttempts"
        & $bootstrapBat
        $exitCode = $LASTEXITCODE
        $vcpkgExe = Join-Path $Root "vcpkg.exe"

        if ($exitCode -eq 0 -and (Test-Path $vcpkgExe)) {
            Write-Host "vcpkg bootstrap succeeded."
            return $true
        }

        Write-Warning "vcpkg bootstrap failed with exit code $exitCode."
        if ($attempt -lt $MaxAttempts) {
            $delay = $BackoffSeconds * [Math]::Pow(2, $attempt - 1)
            Write-Host "Retrying bootstrap in $delay seconds..."
            Start-Sleep -Seconds $delay
        }
    }

    return $false
}

function Get-BootstrapToolUrl {
    param([string]$Root)

    $bootstrapPs1 = Join-Path $Root "scripts\bootstrap.ps1"
    if (-not (Test-Path $bootstrapPs1)) {
        throw "bootstrap.ps1 not found at '$bootstrapPs1'."
    }

    $content = Get-Content -Raw -Path $bootstrapPs1
    $pattern = "https://github\.com/microsoft/vcpkg-tool/releases/download/[^/]+/vcpkg\.exe"
    $match = [regex]::Match($content, $pattern)
    if ($match.Success) {
        return $match.Value
    }

    Write-Warning "Could not parse pinned vcpkg tool URL from bootstrap.ps1. Using latest release endpoint."
    return "https://github.com/microsoft/vcpkg-tool/releases/latest/download/vcpkg.exe"
}

function Invoke-FallbackDownload {
    param(
        [string]$Root,
        [int]$Retries
    )

    $toolUrl = Get-BootstrapToolUrl -Root $Root
    $destination = Join-Path $Root "vcpkg.exe"

    Write-Host "Fallback download: $toolUrl -> $destination"
    & curl.exe -fL --retry $Retries --retry-delay 2 --retry-all-errors `
        --connect-timeout 20 --max-time 300 `
        -o $destination $toolUrl

    if ($LASTEXITCODE -ne 0) {
        throw "Fallback download failed with exit code $LASTEXITCODE."
    }

    if (-not (Test-Path $destination)) {
        throw "Fallback download finished but '$destination' was not created."
    }

    Write-Host "Fallback download succeeded."
}

Write-Host "Preparing vcpkg at '$VcpkgRoot'"
if (-not (Test-Path $VcpkgRoot)) {
    Write-Host "Cloning microsoft/vcpkg..."
    git clone https://github.com/microsoft/vcpkg "$VcpkgRoot"
    if ($LASTEXITCODE -ne 0) {
        throw "git clone for vcpkg failed with exit code $LASTEXITCODE."
    }
}
else {
    Write-Host "Using existing vcpkg root at '$VcpkgRoot'."
}

$bootstrapped = Invoke-Bootstrap -Root $VcpkgRoot -MaxAttempts $BootstrapAttempts -BackoffSeconds $BaseBackoffSeconds
if (-not $bootstrapped) {
    Write-Warning "All bootstrap attempts failed. Running fallback download via curl.exe."
    Invoke-FallbackDownload -Root $VcpkgRoot -Retries $FallbackCurlRetries
}

$vcpkgExe = Join-Path $VcpkgRoot "vcpkg.exe"
if (-not (Test-Path $vcpkgExe)) {
    throw "vcpkg.exe is still missing after bootstrap + fallback."
}

& $vcpkgExe version
if ($LASTEXITCODE -ne 0) {
    throw "vcpkg.exe validation failed with exit code $LASTEXITCODE."
}

if ($env:GITHUB_ENV) {
    "VCPKG_ROOT=$VcpkgRoot" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
    Write-Host "Exported VCPKG_ROOT to GITHUB_ENV."
}
else {
    Write-Warning "GITHUB_ENV is not set. Exporting VCPKG_ROOT in current process only."
    $env:VCPKG_ROOT = $VcpkgRoot
}
