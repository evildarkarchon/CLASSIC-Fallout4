<#
.SYNOPSIS
    Shared code signing functions for CLASSIC build scripts.

.DESCRIPTION
    Provides self-signed certificate lifecycle management and binary signing
    using signtool.exe. Designed to be dot-sourced by build scripts.

    Signing is opt-in: builds succeed without error when signtool.exe or
    a certificate is unavailable.

.NOTES
    Never redirect output to nul on Windows -- use Out-Null or
    -ErrorAction SilentlyContinue instead.
#>

function Find-SignTool {
    <#
    .SYNOPSIS
        Locates signtool.exe on this machine.
    .OUTPUTS
        [string] Full path to signtool.exe, or $null if not found.
    #>

    # 1. Check PATH first (covers VS Dev Shell and manual setup)
    $inPath = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($inPath) { return $inPath.Source }

    # 2. Check Windows SDK registry key
    $sdkRoot = $null
    try {
        $sdkRoot = (Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows Kits\Installed Roots" `
            -Name KitsRoot10 -ErrorAction SilentlyContinue).KitsRoot10
    } catch {
        # Registry key not found -- no Windows SDK installed
    }
    if (-not $sdkRoot) { return $null }

    # 3. Glob for signtool.exe under the SDK bin directory, pick latest version
    $binDir = Join-Path $sdkRoot "bin"
    if (-not (Test-Path $binDir)) { return $null }

    $signtoolPaths = Get-ChildItem -Path $binDir -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^\d+\.\d+\.\d+\.\d+$' } |
        Sort-Object { [version]$_.Name } -Descending |
        ForEach-Object {
            $candidate = Join-Path $_.FullName "x64" "signtool.exe"
            if (Test-Path $candidate) { $candidate }
        } |
        Select-Object -First 1

    if ($signtoolPaths) { return $signtoolPaths }
    return $null
}

function Ensure-SigningCert {
    <#
    .SYNOPSIS
        Ensures a valid PFX code signing certificate exists at the given path.
    .DESCRIPTION
        If no PFX exists, generates a new self-signed code signing certificate.
        If the existing PFX expires within the renewal window, regenerates it.
        Otherwise, reports the remaining validity period.
    .PARAMETER PfxPath
        Full path to the PFX file.
    .PARAMETER Password
        Password for the PFX file.
    .PARAMETER RenewalWindowDays
        Number of days before expiration to trigger auto-renewal.
    .PARAMETER ValidityYears
        Number of years the generated certificate is valid.
    #>
    param(
        [Parameter(Mandatory)]
        [string]$PfxPath,
        [string]$Password = "classic-dev-signing",
        [int]$RenewalWindowDays = 30,
        [int]$ValidityYears = 1
    )

    $needsGeneration = $false
    $secPassword = ConvertTo-SecureString -String $Password -Force -AsPlainText

    if (-not (Test-Path $PfxPath)) {
        Write-Host "No signing certificate found. Generating..." -ForegroundColor Yellow
        $needsGeneration = $true
    } else {
        # Check expiration of existing certificate
        try {
            $existing = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new(
                $PfxPath, $secPassword
            )
            $daysLeft = ($existing.NotAfter - (Get-Date)).Days
            $existing.Dispose()

            if ($daysLeft -le $RenewalWindowDays) {
                Write-Host "Signing certificate expires in $daysLeft days. Regenerating..." -ForegroundColor Yellow
                $needsGeneration = $true
            } else {
                Write-Host "Signing certificate valid for $daysLeft more days." -ForegroundColor DarkGray
            }
        } catch {
            Write-Host "Could not read signing certificate: $_. Regenerating..." -ForegroundColor Yellow
            $needsGeneration = $true
        }
    }

    if ($needsGeneration) {
        # Create cert in user cert store (required by New-SelfSignedCertificate)
        $cert = New-SelfSignedCertificate `
            -Type CodeSigningCert `
            -Subject "CN=CLASSIC Dev Signing, O=CLASSIC Project" `
            -FriendlyName "CLASSIC Code Signing" `
            -CertStoreLocation "Cert:\CurrentUser\My" `
            -NotAfter (Get-Date).AddYears($ValidityYears) `
            -KeyExportPolicy Exportable `
            -KeyAlgorithm RSA `
            -KeyLength 2048 `
            -HashAlgorithm SHA256

        # Ensure output directory exists
        $certDir = Split-Path -Parent $PfxPath
        if (-not (Test-Path $certDir)) {
            New-Item -ItemType Directory -Path $certDir -Force | Out-Null
        }

        # Export to PFX on disk
        Export-PfxCertificate `
            -Cert $cert `
            -FilePath $PfxPath `
            -Password $secPassword `
            -CryptoAlgorithmOption AES256_SHA256 | Out-Null

        # Remove from cert store immediately (we only want the PFX file)
        Remove-Item -Path "Cert:\CurrentUser\My\$($cert.Thumbprint)"

        Write-Host "Generated signing certificate: $PfxPath" -ForegroundColor Green
    }
}

function Sign-Binary {
    <#
    .SYNOPSIS
        Signs a single binary with signtool.exe using a PFX certificate.
    .PARAMETER SignToolPath
        Full path to signtool.exe.
    .PARAMETER PfxPath
        Full path to the PFX certificate file.
    .PARAMETER Password
        Password for the PFX file.
    .PARAMETER BinaryPath
        Full path to the binary to sign.
    .OUTPUTS
        [bool] $true if signing succeeded, $false otherwise.
    #>
    param(
        [Parameter(Mandatory)]
        [string]$SignToolPath,
        [Parameter(Mandatory)]
        [string]$PfxPath,
        [Parameter(Mandatory)]
        [string]$Password,
        [Parameter(Mandatory)]
        [string]$BinaryPath
    )

    if (-not (Test-Path $BinaryPath)) {
        Write-Warning "Binary not found for signing: $BinaryPath"
        return $false
    }

    & $SignToolPath sign /f $PfxPath /p $Password /fd SHA256 /d "CLASSIC" $BinaryPath
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Failed to sign: $BinaryPath"
        return $false
    }

    Write-Host "Signed: $BinaryPath" -ForegroundColor Green
    return $true
}

function Invoke-CodeSigning {
    <#
    .SYNOPSIS
        Entry point for code signing, called by build scripts after install.
    .DESCRIPTION
        Locates signtool.exe, ensures a valid certificate exists, and signs
        each specified binary. All errors are caught so signing failures
        never block the build.
    .PARAMETER InstallDir
        Directory containing the installed binaries.
    .PARAMETER Binaries
        Array of EXE filenames to sign (e.g., @("classic-cli.exe")).
    #>
    param(
        [Parameter(Mandatory)]
        [string]$InstallDir,
        [Parameter(Mandatory)]
        [string[]]$Binaries
    )

    try {
        # Locate signtool.exe
        $signtool = Find-SignTool
        if (-not $signtool) {
            Write-Host "signtool.exe not found. Skipping code signing." -ForegroundColor DarkGray
            return
        }
        Write-Host "Using signtool: $signtool" -ForegroundColor DarkGray

        # Resolve PFX path: env var override or default location
        $pfxPath = $env:CLASSIC_SIGNING_PFX
        if (-not $pfxPath) {
            $repoRoot = Split-Path $PSScriptRoot -Parent
            $pfxPath = Join-Path $repoRoot "tools" "certs" "classic-signing.pfx"
        }

        # Resolve PFX password: env var override or default
        $pfxPassword = $env:CLASSIC_SIGNING_PASSWORD
        if (-not $pfxPassword) {
            $pfxPassword = "classic-dev-signing"
        }

        # Ensure certificate exists and is valid
        Ensure-SigningCert -PfxPath $pfxPath -Password $pfxPassword

        # Sign each binary
        foreach ($binary in $Binaries) {
            $binaryPath = Join-Path $InstallDir $binary
            Sign-Binary -SignToolPath $signtool -PfxPath $pfxPath `
                -Password $pfxPassword -BinaryPath $binaryPath | Out-Null
        }
    } catch {
        Write-Warning "Code signing encountered an error: $_"
        Write-Warning "Build will continue without code signing."
    }
}
