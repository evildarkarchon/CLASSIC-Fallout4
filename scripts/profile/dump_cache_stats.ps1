<#
.SYNOPSIS
    Dumps cache statistics from CLASSIC Rust caches.

.DESCRIPTION
    Imports CLASSIC Python modules and extracts cache statistics from
    instrumented DashMap caches. Outputs to console and optionally JSON file.

    This script provides visibility into cache performance, including:
    - Hit/miss counts
    - Hit rate percentage
    - Cache size (number of entries)
    - Cache keys (for settings cache)

.PARAMETER Output
    Optional JSON output file path.
    If not specified with -Format json/both, generates timestamped file.

.PARAMETER Format
    Output format: 'console' (default), 'json', 'both'.

.EXAMPLE
    .\dump_cache_stats.ps1
    # Console output of all cache stats

.EXAMPLE
    .\dump_cache_stats.ps1 -Format json
    # JSON output to stdout

.EXAMPLE
    .\dump_cache_stats.ps1 -Format both -Output cache-stats.json
    # Console output and JSON file

.NOTES
    Requires the CLASSIC Python environment with Rust extensions built.
    Run `uv sync` and `./rebuild_rust.ps1` if modules are not found.
#>

[CmdletBinding()]
param(
    [Parameter(HelpMessage = "JSON output file path")]
    [string]$Output,

    [Parameter(HelpMessage = "Output format: console, json, or both")]
    [ValidateSet('console', 'json', 'both')]
    [string]$Format = 'console'
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " CLASSIC Cache Statistics" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Resolve script and project paths
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Get-Item "$scriptDir/../..").FullName

# Python script to extract cache stats
$pythonScript = @'
import json
import sys
from datetime import datetime

stats = {
    "timestamp": datetime.now().isoformat(),
    "caches": {}
}

# Try to get yaml cache stats
try:
    import classic_yaml
    ops = classic_yaml.YamlOperations()
    yaml_stats = ops.get_cache_stats()
    stats["caches"]["yaml"] = yaml_stats
except ImportError as e:
    stats["caches"]["yaml"] = {"error": f"Module not found: {e}"}
except AttributeError as e:
    stats["caches"]["yaml"] = {"error": f"Method not available: {e}"}
except Exception as e:
    stats["caches"]["yaml"] = {"error": str(e)}

# Try to get settings cache stats
try:
    import classic_settings
    settings_stats = classic_settings.cache_stats()
    # Convert to dict if it's a Rust struct
    if hasattr(settings_stats, '__dict__'):
        stats["caches"]["settings"] = vars(settings_stats)
    elif hasattr(settings_stats, 'hits'):
        stats["caches"]["settings"] = {
            "hits": settings_stats.hits,
            "misses": settings_stats.misses,
            "hit_rate": settings_stats.hit_rate,
            "size": settings_stats.size,
            "keys": list(settings_stats.keys) if hasattr(settings_stats, 'keys') else [],
        }
    else:
        stats["caches"]["settings"] = settings_stats
except ImportError as e:
    stats["caches"]["settings"] = {"error": f"Module not found: {e}"}
except AttributeError as e:
    stats["caches"]["settings"] = {"error": f"Method not available: {e}"}
except Exception as e:
    stats["caches"]["settings"] = {"error": str(e)}

# Output format based on argument
output_format = sys.argv[1] if len(sys.argv) > 1 else "console"
output_path = sys.argv[2] if len(sys.argv) > 2 else None

def format_hit_rate(rate):
    """Format hit rate as percentage."""
    if isinstance(rate, (int, float)):
        return f"{rate * 100:.2f}%"
    return str(rate)

if output_format in ("console", "both"):
    print()
    print("=== Cache Statistics ===")
    print(f"Timestamp: {stats['timestamp']}")
    print()

    for cache_name, cache_stats in stats["caches"].items():
        print(f"[{cache_name.upper()}]")
        if "error" in cache_stats:
            print(f"  Error: {cache_stats['error']}")
        else:
            for key, value in cache_stats.items():
                if key == "hit_rate":
                    print(f"  {key}: {format_hit_rate(value)}")
                elif key == "keys" and isinstance(value, list):
                    print(f"  {key}: [{len(value)} keys]")
                    if value and len(value) <= 10:
                        for k in value:
                            print(f"    - {k}")
                    elif value:
                        for k in value[:5]:
                            print(f"    - {k}")
                        print(f"    ... and {len(value) - 5} more")
                else:
                    print(f"  {key}: {value}")
        print()

    # Summary
    total_hits = 0
    total_misses = 0
    total_size = 0
    for cache_stats in stats["caches"].values():
        if "error" not in cache_stats:
            total_hits += cache_stats.get("hits", 0)
            total_misses += cache_stats.get("misses", 0)
            total_size += cache_stats.get("size", 0)

    total = total_hits + total_misses
    overall_rate = (total_hits / total * 100) if total > 0 else 0

    print("=== Summary ===")
    print(f"Total hits: {total_hits}")
    print(f"Total misses: {total_misses}")
    print(f"Overall hit rate: {overall_rate:.2f}%")
    print(f"Total cached entries: {total_size}")
    print()

if output_format in ("json", "both"):
    if output_path:
        with open(output_path, "w") as f:
            json.dump(stats, f, indent=2)
        print(f"JSON written to: {output_path}")
    elif output_format == "json":
        print(json.dumps(stats, indent=2))
'@

# Setup output if specified
$outputArg = ""
if ($Output) {
    $outputDir = Split-Path $Output -Parent
    if ($outputDir -and -not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
    }
    $outputArg = if ([System.IO.Path]::IsPathRooted($Output)) {
        $Output
    } else {
        Join-Path $projectRoot $Output
    }
} elseif ($Format -in @('json', 'both')) {
    $timestamp = Get-Date -Format "yyyy-MM-dd-HHmmss"
    $outputDir = Join-Path $projectRoot "target/profiling/cache-stats"
    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
    }
    $outputArg = Join-Path $outputDir "cache-stats-$timestamp.json"
}

# Run Python script
Push-Location $projectRoot
try {
    $pythonScript | uv run python - $Format $outputArg
    $exitCode = $LASTEXITCODE
} catch {
    Write-Host "[Error] $_" -ForegroundColor Red
    $exitCode = 1
} finally {
    Pop-Location
}

if ($exitCode -ne 0) {
    Write-Host "[Error] Failed to get cache statistics" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Run 'uv sync' to ensure Python environment is set up" -ForegroundColor DarkGray
    Write-Host "  2. Run './rebuild_rust.ps1' to build Rust extensions" -ForegroundColor DarkGray
    Write-Host "  3. Check that classic_yaml and classic_settings modules exist" -ForegroundColor DarkGray
    exit 1
}

Write-Host ""
