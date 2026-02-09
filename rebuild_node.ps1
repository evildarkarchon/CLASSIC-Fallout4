<#
.SYNOPSIS
    Build the CLASSIC Node.js/Bun native addon.
.DESCRIPTION
    Builds the classic-node NAPI-RS crate and generates JS/TS glue files.
.PARAMETER Clean
    Perform a clean build (removes previous artifacts).
.PARAMETER Debug
    Build in debug mode instead of release.
.EXAMPLE
    ./rebuild_node.ps1           # Release build
    ./rebuild_node.ps1 -Debug    # Debug build
    ./rebuild_node.ps1 -Clean    # Clean release build
#>
param(
    [switch]$Clean,
    [switch]$Debug
)

$ErrorActionPreference = "Stop"
$nodeDir = Join-Path (Join-Path (Join-Path $PSScriptRoot "rust") "node-bindings") "classic-node"

if (-not (Test-Path $nodeDir)) {
    Write-Error "Node bindings directory not found: $nodeDir"
    exit 1
}

Push-Location $nodeDir
try {
    # Ensure dependencies are installed
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing dependencies..." -ForegroundColor Cyan
        bun install
    }

    if ($Clean) {
        Write-Host "Cleaning previous build artifacts..." -ForegroundColor Yellow
        Remove-Item -Force -ErrorAction SilentlyContinue *.node
        Remove-Item -Force -ErrorAction SilentlyContinue index.js
        Remove-Item -Force -ErrorAction SilentlyContinue index.d.ts
        cargo clean -p classic-node
    }

    if ($Debug) {
        Write-Host "Building classic-node (debug)..." -ForegroundColor Cyan
        bun run build:debug
    } else {
        Write-Host "Building classic-node (release)..." -ForegroundColor Cyan
        bun run build
    }

    Write-Host "Build complete!" -ForegroundColor Green

    # Verify the build produced expected files
    $nodeFile = Get-ChildItem -Filter "*.node" -ErrorAction SilentlyContinue
    if ($nodeFile) {
        Write-Host "  Native addon: $($nodeFile.Name) ($([math]::Round($nodeFile.Length / 1MB, 2)) MB)" -ForegroundColor Gray
    }
    if (Test-Path "index.d.ts") {
        Write-Host "  TypeScript types: index.d.ts" -ForegroundColor Gray
    }
} finally {
    Pop-Location
}
