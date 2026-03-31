# Quick Task: Self-signing of compiled code in build scripts - Research

**Researched:** 2026-03-31
**Domain:** Windows code signing (signtool.exe, self-signed certificates, PowerShell PKI)
**Confidence:** HIGH

## Summary

Self-signing Windows binaries with `signtool.exe` is straightforward. The workflow is: (1) create a self-signed code signing certificate via `New-SelfSignedCertificate`, (2) export it as a PFX, (3) sign binaries with `signtool.exe sign /f cert.pfx /fd SHA256`. Certificate expiry can be checked via `[X509Certificate2]::new()` to implement the 30-day renewal window.

**Primary recommendation:** Create a shared `tools/sign-binaries.ps1` script that both build scripts call after install/package. Keep signing opt-in so builds work without certificates or SDK.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use `signtool.exe` from Windows SDK
- PFX file on disk (not cert store) in a known/configurable location
- Sign EXEs and project DLLs only -- NOT third-party DLLs (Qt, MSVC runtime, vcpkg deps)
- PFX must be `.gitignore`d

### Claude's Discretion
- Exact PFX file path and naming convention
- Certificate subject/CN naming
- How the 30-day renewal window check is implemented
- Integration point in build scripts (after build vs after install vs after package)

### Deferred Ideas
None stated.
</user_constraints>

## Project Constraints (from CLAUDE.md)

- Never output to `nul` on Windows -- creates undeletable files
- C++ builds use PowerShell wrapper scripts (`build_cli.ps1`, `build_gui.ps1`), never raw ctest
- Commit prefix convention: `Feat:`, `Fix:`, `Docs:`, `Refactor:`, `Chore:`, `Update:`

## Findings

### 1. Binaries to Sign

Based on build output analysis:

| Binary | Location (build) | Location (install) | Type |
|--------|-------------------|--------------------|------|
| `classic-cli.exe` | `classic-cli/build/classic-cli.exe` | `classic-cli/install/classic-cli.exe` | Project EXE |
| `CLASSIC.exe` | `classic-gui/build/CLASSIC.exe` | `classic-gui/install/CLASSIC.exe` | Project EXE |

The `classic-cpp-bridge` is a **static library** (`.lib`), not a DLL. Static libraries cannot and do not need to be signed. All DLLs in the install directories are third-party (Qt6, vcpkg deps) and should NOT be signed per user decision.

**Confidence:** HIGH -- verified by inspecting actual build and install directories.

### 2. Creating a Self-Signed Code Signing Certificate

PowerShell's `New-SelfSignedCertificate` has a built-in `-Type CodeSigningCert` parameter that sets the correct EKU (1.3.6.1.5.5.7.3.3) and key usage:

```powershell
# Create a code signing certificate valid for 1 year
$cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject "CN=CLASSIC Dev Signing, O=CLASSIC Project" `
    -FriendlyName "CLASSIC Code Signing" `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -NotAfter (Get-Date).AddYears(1) `
    -KeyExportPolicy Exportable `
    -KeyAlgorithm RSA `
    -KeyLength 2048 `
    -HashAlgorithm SHA256
```

Then export to PFX:

```powershell
$password = ConvertTo-SecureString -String "changeme" -Force -AsPlainText
Export-PfxCertificate `
    -Cert $cert `
    -FilePath $pfxPath `
    -Password $password `
    -CryptoAlgorithmOption AES256_SHA256
```

Then remove from the cert store (we only want the PFX on disk):

```powershell
Remove-Item -Path "Cert:\CurrentUser\My\$($cert.Thumbprint)"
```

**Confidence:** HIGH -- `-Type CodeSigningCert` parameter verified in `Get-Help` output on this machine.

### 3. Signing Binaries with signtool.exe

The exact command for PFX-based signing:

```powershell
signtool.exe sign /f "$pfxPath" /p "$password" /fd SHA256 /d "CLASSIC" "$binaryPath"
```

Key flags:
- `/f <file>` -- PFX file path (required for file-based signing)
- `/p <password>` -- PFX password
- `/fd SHA256` -- File digest algorithm (**mandatory** in current signtool; omitting it causes an error)
- `/d <desc>` -- Description embedded in signature (optional but good practice)
- `/t` or `/tr` -- Timestamp server URL (optional for self-signed dev builds; skip to avoid external dependency)

**Confidence:** HIGH -- verified by running `signtool.exe sign /?` on this machine with SDK 10.0.26100.0.

### 4. Checking PFX Expiration Date

The `Get-PfxCertificate` cmdlet prompts for a password interactively, which is unsuitable for scripts. Use `X509Certificate2` constructor directly:

```powershell
$pfxPassword = ConvertTo-SecureString -String "changeme" -Force -AsPlainText
$cert = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new(
    $pfxPath, $pfxPassword
)
$daysUntilExpiry = ($cert.NotAfter - (Get-Date)).Days
$needsRenewal = $daysUntilExpiry -le 30
$cert.Dispose()
```

**Confidence:** HIGH -- `X509Certificate2` is part of .NET BCL, available in all PowerShell 5.1+ environments.

### 5. signtool.exe Path Discovery

signtool.exe is NOT in the default PATH. It lives under the Windows SDK installation directory. Multiple SDK versions may be installed.

**Discovery strategies (in priority order):**

1. **Already in PATH** (VS Dev Shell or manual setup): `Get-Command signtool.exe -ErrorAction SilentlyContinue`
2. **Windows SDK registry key**: `HKLM:\SOFTWARE\Microsoft\Windows Kits\Installed Roots` has `KitsRoot10` value
3. **Glob the SDK bin directory**: `"${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe"` and pick the latest version

Recommended approach for the build scripts:

```powershell
function Find-SignTool {
    # Check PATH first (covers VS Dev Shell)
    $inPath = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($inPath) { return $inPath.Source }

    # Check Windows SDK installation
    $sdkRoot = (Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows Kits\Installed Roots" `
        -Name KitsRoot10 -ErrorAction SilentlyContinue).KitsRoot10
    if (-not $sdkRoot) { return $null }

    # Find latest SDK version with signtool
    $signtoolPaths = Get-ChildItem -Path (Join-Path $sdkRoot "bin") -Recurse `
        -Filter "signtool.exe" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match "\\x64\\" } |
        Sort-Object { [version]($_.FullName -replace '.*\\(\d+\.\d+\.\d+\.\d+)\\.*','$1') } -Descending
    if ($signtoolPaths) { return $signtoolPaths[0].FullName }

    return $null
}
```

On this machine, signtool is at: `C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe`

**Confidence:** HIGH -- verified SDK paths and registry key on this machine.

### 6. Certificate Subject/CN Naming Recommendation

For self-signed dev builds, the CN should clearly indicate it is a development/self-signed certificate:

**Recommended:** `CN=CLASSIC Dev Signing, O=CLASSIC Project`

- Includes project name for identification
- "Dev Signing" makes it clear this is not a CA-issued certificate
- Windows SmartScreen will still warn users (expected for self-signed)

### 7. Integration Point Recommendation

**Sign after Install, before Package.** Rationale:
- The install step copies project binaries to a clean directory separate from third-party DLLs
- Package (CPack ZIP) should contain already-signed binaries
- Signing build-dir binaries is fragile (mixed with test executables, temp files)
- Signing install-dir binaries is clean (known set of files)

For the CLI build script (no install step unless `-Install`), sign the build output directly since there is no separate install layout by default. But when `-Install` or `-Package` is used, sign the installed copy.

### 8. PFX File Location Recommendation

**Recommended path:** `tools/certs/classic-signing.pfx`

- `tools/` directory already exists in the repo
- `certs/` subdirectory makes purpose clear
- The whole `tools/certs/` directory should be in `.gitignore`
- Allow override via environment variable: `$env:CLASSIC_SIGNING_PFX`

## Common Pitfalls

### Pitfall 1: Forgetting `/fd SHA256`
**What goes wrong:** signtool.exe errors out with "You must specify the file digest algorithm"
**Why it happens:** Recent signtool versions removed the default digest algorithm
**How to avoid:** Always pass `/fd SHA256`

### Pitfall 2: Certificate not exportable
**What goes wrong:** `Export-PfxCertificate` fails silently or errors
**Why it happens:** Default `KeyExportPolicy` may not allow export
**How to avoid:** Always pass `-KeyExportPolicy Exportable` to `New-SelfSignedCertificate`

### Pitfall 3: Leftover cert in cert store
**What goes wrong:** Cert store accumulates old signing certs on each renewal
**Why it happens:** `New-SelfSignedCertificate` creates in store, then we export to PFX
**How to avoid:** Remove from cert store immediately after PFX export

### Pitfall 4: Password in script
**What goes wrong:** PFX password visible in build logs
**Why it happens:** Hard-coded password string
**How to avoid:** For self-signed dev certs, a simple known password is acceptable (the cert itself provides no trust chain). Use a constant but don't echo it. If paranoid, use an environment variable.

### Pitfall 5: `nul` on Windows
**What goes wrong:** The project CLAUDE.md and global instructions both forbid outputting to `nul`
**How to avoid:** Use `Out-Null` or `$null =` for discarding output, never redirect to `nul` or `NUL`

## Code Examples

### Full certificate generation + renewal check function

```powershell
function Ensure-SigningCert {
    param(
        [string]$PfxPath,
        [string]$Password = "classic-dev-signing",
        [int]$RenewalWindowDays = 30,
        [int]$ValidityYears = 1
    )

    $needsGeneration = $false

    if (-not (Test-Path $PfxPath)) {
        Write-Host "No signing certificate found. Generating..." -ForegroundColor Yellow
        $needsGeneration = $true
    } else {
        # Check expiration
        $secPassword = ConvertTo-SecureString -String $Password -Force -AsPlainText
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
        $secPassword = ConvertTo-SecureString -String $Password -Force -AsPlainText

        # Create cert in cert store (required by New-SelfSignedCertificate)
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

        # Remove from cert store (we only want the PFX file)
        Remove-Item -Path "Cert:\CurrentUser\My\$($cert.Thumbprint)"

        Write-Host "Generated signing certificate: $PfxPath" -ForegroundColor Green
    }
}
```

### Signing function

```powershell
function Sign-Binary {
    param(
        [string]$SignToolPath,
        [string]$PfxPath,
        [string]$Password,
        [string]$BinaryPath
    )

    if (-not (Test-Path $BinaryPath)) {
        Write-Warning "Binary not found for signing: $BinaryPath"
        return $false
    }

    $signArgs = @("sign", "/f", $PfxPath, "/p", $Password, "/fd", "SHA256",
                  "/d", "CLASSIC", $BinaryPath)
    & $SignToolPath @signArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Failed to sign: $BinaryPath"
        return $false
    }

    Write-Host "Signed: $BinaryPath" -ForegroundColor Green
    return $true
}
```

## Architecture Recommendation

### Shared script approach

Create `tools/sign-binaries.ps1` with `Ensure-SigningCert`, `Find-SignTool`, and `Sign-Binary` functions. Both build scripts dot-source it and call signing after their Install step.

```
tools/
  sign-binaries.ps1      # Shared signing functions
  certs/                  # .gitignore'd directory
    classic-signing.pfx   # Auto-generated PFX
```

### Integration in build scripts

Add after Step 5 (Install) in both `build_cli.ps1` and `build_gui.ps1`:

```powershell
# ── Step 5.5: Sign (optional, after install) ────────────────────
if ($Install) {
    $signScript = Join-Path (Split-Path $ScriptDir -Parent) "tools" "sign-binaries.ps1"
    if (Test-Path $signScript) {
        . $signScript
        $signtool = Find-SignTool
        if ($signtool) {
            $pfxPath = if ($env:CLASSIC_SIGNING_PFX) { $env:CLASSIC_SIGNING_PFX }
                       else { Join-Path (Split-Path $ScriptDir -Parent) "tools" "certs" "classic-signing.pfx" }
            Ensure-SigningCert -PfxPath $pfxPath
            Sign-Binary -SignToolPath $signtool -PfxPath $pfxPath `
                -Password "classic-dev-signing" -BinaryPath (Join-Path $installDir "classic-cli.exe")
        } else {
            Write-Host "signtool.exe not found. Skipping code signing." -ForegroundColor DarkGray
        }
    }
}
```

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| signtool.exe | Binary signing | Yes | SDK 10.0.26100.0 | Skip signing (opt-in) |
| PowerShell PKI module | Cert generation | Yes | Built into Windows | -- |
| Windows SDK | signtool location | Yes | 10.0.26100.0 + 10.0.19041.0 | Skip signing |

**Missing dependencies:** None -- all required tools are available on this machine. Signing is designed to be opt-in regardless.

## Sources

### Primary (HIGH confidence)
- `signtool.exe sign /?` help output -- verified on this machine (SDK 10.0.26100.0)
- `Get-Help New-SelfSignedCertificate` -- verified `-Type CodeSigningCert` parameter
- `Get-Help Export-PfxCertificate` -- verified export syntax
- `Get-Help Get-PfxCertificate` -- confirmed interactive password prompt limitation
- Build script analysis: `classic-cli/build_cli.ps1`, `classic-gui/build_gui.ps1`
- Install directory inspection: `classic-gui/install/` showing project vs third-party binaries

## Metadata

**Confidence breakdown:**
- Certificate creation: HIGH -- verified cmdlet parameters on this machine
- signtool usage: HIGH -- verified help output and flag requirements
- Expiry checking: HIGH -- standard .NET X509Certificate2 API
- SDK path discovery: HIGH -- verified registry key and paths on this machine
- Build integration point: HIGH -- read both build scripts, understand install step structure

**Research date:** 2026-03-31
**Valid until:** Indefinite (Windows SDK signing APIs are stable)
