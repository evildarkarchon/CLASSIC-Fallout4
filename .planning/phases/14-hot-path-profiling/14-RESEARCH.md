# Phase 14: Hot Path Profiling & Cache Instrumentation - Research

**Researched:** 2026-02-04
**Domain:** Rust profiling, flamegraph generation, memory allocation analysis, DashMap cache instrumentation
**Confidence:** HIGH

## Summary

This phase implements developer tooling for performance analysis in the CLASSIC hybrid Python-Rust application. The tooling enables flamegraph generation for Rust hot paths, combined Python+Rust stack traces via py-spy, memory allocation profiling via dhat, and DashMap cache hit/miss observability via tracing instrumentation.

The Rust ecosystem provides mature, well-documented tools for all requirements. cargo-flamegraph with inferno backend is the standard for flamegraph generation on Windows. py-spy supports profiling native extensions with the `--native` flag on Windows x86-64. dhat provides heap profiling via feature flag toggling. The tracing crate integrates naturally with the existing logging setup for cache instrumentation.

**Primary recommendation:** Use cargo-flamegraph (with blondie backend on Windows) for flamegraph generation, py-spy with `--native` for combined stacks, dhat via feature flag for heap profiling, and tracing events at TRACE/DEBUG levels for DashMap cache observability.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| cargo-flamegraph | latest | Flamegraph generation from perf/DTTrace/ETW | Rust-native, no Perl dependency, Windows support via blondie |
| inferno | 0.11+ | SVG flamegraph rendering library | 20x faster than Perl, used by cargo-flamegraph |
| py-spy | 0.3+ | Python sampling profiler with native extension support | Rust-based, --native flag for PyO3 stacks, Windows x86-64 support |
| dhat | 0.3+ | Heap allocation profiler | Pure Rust, feature-flag gated, DHAT viewer compatible |
| tracing | 0.1.44 | Instrumentation for cache metrics | Already in workspace, structured logging, level filtering |
| tracing-subscriber | 0.3.22 | Subscriber configuration | Already in workspace, layer composition |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| serde_json | 1.0 | Cache statistics JSON serialization | Already in workspace, for JSON output |
| chrono | 0.4 | Timestamped filenames | Already in workspace, for output naming |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| cargo-flamegraph | samply | Better interactive UI (Firefox Profiler), but Windows support newer and less tested |
| dhat | jemalloc profiling | More comprehensive but requires allocator swap, complex setup |
| manual DashMap wrapping | metrics crate | metrics provides full Prometheus export, but heavier for dev-only instrumentation |

**Installation:**
```bash
# Profiling tools (system-level)
cargo install flamegraph
cargo install cargo-flamegraph
pip install py-spy  # Or: cargo install py-spy

# dhat is a dev-dependency in Cargo.toml, no system install needed
```

## Architecture Patterns

### Recommended Profiling Output Structure
```
target/profiling/
├── flamegraphs/
│   ├── flamegraph-2026-02-04-143022.svg
│   ├── flamegraph-2026-02-04-152315.svg
│   └── ...
├── py-spy/
│   ├── combined-2026-02-04-143022.svg
│   └── ...
├── dhat/
│   ├── dhat-heap-2026-02-04-143022.json
│   └── ...
└── cache-stats/
    ├── cache-stats-2026-02-04-143022.json
    └── ...
```

### Pattern 1: Feature-Flag Gated dhat Profiling
**What:** Enable dhat heap profiling via Cargo feature flag
**When to use:** Memory allocation analysis sessions
**Example:**
```rust
// In Cargo.toml
[features]
dhat-heap = []

[dependencies]
dhat = { version = "0.3", optional = true }

// In lib.rs or main.rs
#[cfg(feature = "dhat-heap")]
#[global_allocator]
static ALLOC: dhat::Alloc = dhat::Alloc;

fn main() {
    #[cfg(feature = "dhat-heap")]
    let _profiler = dhat::Profiler::new_heap();

    // ... rest of application
}
```

### Pattern 2: Tracing-Based Cache Instrumentation
**What:** Use tracing events for cache hit/miss observability
**When to use:** DashMap cache performance analysis
**Example:**
```rust
// Source: tracing crate documentation
use tracing::{debug, trace, instrument};
use dashmap::DashMap;
use std::sync::atomic::{AtomicU64, Ordering};

pub struct InstrumentedCache<K, V> {
    inner: DashMap<K, V>,
    hits: AtomicU64,
    misses: AtomicU64,
}

impl<K: std::hash::Hash + Eq, V: Clone> InstrumentedCache<K, V> {
    pub fn get(&self, key: &K) -> Option<V> {
        match self.inner.get(key) {
            Some(entry) => {
                self.hits.fetch_add(1, Ordering::Relaxed);
                trace!(cache = %std::any::type_name::<Self>(), "cache hit");
                Some(entry.value().clone())
            }
            None => {
                self.misses.fetch_add(1, Ordering::Relaxed);
                trace!(cache = %std::any::type_name::<Self>(), "cache miss");
                None
            }
        }
    }

    pub fn stats(&self) -> CacheStats {
        let hits = self.hits.load(Ordering::Relaxed);
        let misses = self.misses.load(Ordering::Relaxed);
        let total = hits + misses;
        CacheStats {
            hits,
            misses,
            hit_rate: if total > 0 { hits as f64 / total as f64 } else { 0.0 },
            size: self.inner.len(),
        }
    }
}

#[derive(serde::Serialize)]
pub struct CacheStats {
    pub hits: u64,
    pub misses: u64,
    pub hit_rate: f64,
    pub size: usize,
}
```

### Pattern 3: Quick/Thorough Profile Mode (Matching Phase 13)
**What:** Environment variable controls profiling depth
**When to use:** All profiling operations
**Example:**
```rust
// Profile mode matching benchmark mode pattern
pub enum ProfileMode {
    Quick,    // Lower sampling rate, shorter duration
    Thorough, // Higher sampling rate, longer duration
}

impl ProfileMode {
    pub fn from_env() -> Self {
        match std::env::var("PROFILE_MODE").as_deref() {
            Ok("thorough") => ProfileMode::Thorough,
            _ => ProfileMode::Quick,
        }
    }

    pub fn sampling_rate(&self) -> u32 {
        match self {
            ProfileMode::Quick => 99,      // 99 Hz
            ProfileMode::Thorough => 997,  // 997 Hz (prime to avoid aliasing)
        }
    }

    pub fn duration_secs(&self) -> u32 {
        match self {
            ProfileMode::Quick => 10,
            ProfileMode::Thorough => 60,
        }
    }
}
```

### Pattern 4: PowerShell Profiling Script Structure
**What:** Consistent script interface matching rebuild_rust.ps1
**When to use:** All profiling invocations
**Example:**
```powershell
# profile_flamegraph.ps1
param(
    [ValidateSet("quick", "thorough")]
    [string]$Mode = "quick",

    [string]$Target = "",  # Specific crate or binary

    [string]$Output = "",  # Custom output path

    [switch]$Open          # Open SVG in browser after generation
)

$env:PROFILE_MODE = $Mode

$timestamp = Get-Date -Format "yyyy-MM-dd-HHmmss"
$outputDir = "target/profiling/flamegraphs"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$outputFile = if ($Output) { $Output } else { "$outputDir/flamegraph-$timestamp.svg" }

# ... profiling logic
```

### Anti-Patterns to Avoid
- **Profiling debug builds:** Always use release builds with debug=true for accurate measurements
- **Hardcoded sampling rates:** Use environment variables for configurable rates
- **Leaving dhat enabled in production:** Feature flag ensures it's only in profiling builds
- **Per-key tracing in hot paths by default:** Use TRACE level and filter, not always-on logging
- **Mixing profiling with benchmarking:** Keep scripts separate (profilers diagnose, benchmarks measure)

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Flamegraph SVG generation | Custom SVG rendering | inferno/cargo-flamegraph | Interactive features, zoom, search, color schemes |
| Stack frame symbolization | Manual addr2line parsing | cargo-flamegraph --release-debug | Automatic symbol resolution with debug info |
| Python+Rust combined stacks | Custom frame stitching | py-spy --native | Handles FFI boundary correctly |
| Heap allocation tracking | Custom allocator wrapper | dhat | Proven, viewer integration, JSON export |
| Cache metrics aggregation | Manual counter management | tracing + AtomicU64 | Thread-safe, level-filtered, structured |

**Key insight:** Profiling tools have complex edge cases (symbol resolution, stack unwinding, sampling synchronization). Using established tools prevents subtle measurement errors that invalidate results.

## Common Pitfalls

### Pitfall 1: Missing Debug Symbols in Release Builds
**What goes wrong:** Flamegraphs show only addresses, no function names
**Why it happens:** Release profile strips debug info by default
**How to avoid:** Add to Cargo.toml: `[profile.release] debug = true`
**Warning signs:** Flamegraph shows hex addresses like `0x55a3b2c4d5e6` instead of function names

### Pitfall 2: py-spy --native Without Symbols
**What goes wrong:** Rust frames show as `<unknown>` in combined traces
**Why it happens:** Rust extension .pyd/.dll lacks debug symbols
**How to avoid:** Build with `CARGO_PROFILE_RELEASE_DEBUG=true` or use `release-with-debug` profile
**Warning signs:** Python frames visible but Rust frames are blank/unknown

### Pitfall 3: dhat in Debug Builds
**What goes wrong:** Profiling is extremely slow, measurements meaningless
**Why it happens:** Debug builds have no optimizations
**How to avoid:** Always run dhat with `--release` flag; dhat docs explicitly warn about this
**Warning signs:** 100x slower execution than normal release builds

### Pitfall 4: TRACE Level Logging in Production
**What goes wrong:** Massive performance degradation from per-key cache logging
**Why it happens:** Leaving detailed tracing subscriber active
**How to avoid:** Use `tracing_subscriber` with `EnvFilter`, default to INFO level
**Warning signs:** Console flooded with cache hit/miss messages during normal operation

### Pitfall 5: Flamegraph During GIL-Holding Operations
**What goes wrong:** Flamegraph shows Python waiting, not Rust work
**Why it happens:** py-spy samples Python threads; GIL contention visible as waits
**How to avoid:** Profile pure Rust operations separately with cargo-flamegraph; use py-spy for combined view
**Warning signs:** Large `PyGILState_Ensure` blocks in flamegraph

### Pitfall 6: Inconsistent Timestamp Formats
**What goes wrong:** Cannot correlate profiling outputs across tools
**Why it happens:** Each script uses different timestamp format
**How to avoid:** Standardize on ISO-8601 derived format: `yyyy-MM-dd-HHmmss`
**Warning signs:** Files like `flamegraph_20260204.svg` vs `dhat-heap-2026-02-04-143022.json`

## Code Examples

Verified patterns from official sources:

### Cargo.toml Configuration for Profiling
```toml
# Source: cargo-flamegraph and dhat documentation
[profile.release]
debug = true  # Enable debug symbols for flamegraphs

[profile.release-with-debug]
inherits = "release"
debug = true

# dhat feature for optional heap profiling
[features]
dhat-heap = ["dep:dhat"]

[dependencies]
dhat = { version = "0.3", optional = true }
```

### .cargo/config.toml Aliases
```toml
# Source: cargo-flamegraph usage patterns
[alias]
# Flamegraph aliases
flame = "flamegraph"
flame-bench = "flamegraph --bench"

# Profile-specific builds
build-profile = "build --profile release-with-debug"
```

### Tracing Subscriber Setup for Cache Metrics
```rust
// Source: tracing-subscriber documentation
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

pub fn init_profiling_tracing() {
    // Default to INFO, allow TRACE for cache stats via RUST_LOG
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("info,classic_yaml_core::cache=debug"));

    tracing_subscriber::registry()
        .with(filter)
        .with(tracing_subscriber::fmt::layer())
        .init();
}
```

### Cache Statistics Collection and Export
```rust
// Source: serde_json + tracing patterns
use serde::Serialize;
use std::collections::HashMap;

#[derive(Serialize)]
pub struct AllCacheStats {
    pub timestamp: String,
    pub caches: HashMap<String, CacheStats>,
}

pub fn dump_all_cache_stats() -> AllCacheStats {
    let mut stats = HashMap::new();

    // Collect from each instrumented cache
    stats.insert("yaml_cache".to_string(), yaml_core::cache_stats());
    stats.insert("settings_cache".to_string(), settings_core::cache_stats());
    stats.insert("hash_cache".to_string(), file_io_core::hash_cache_stats());

    AllCacheStats {
        timestamp: chrono::Utc::now().format("%Y-%m-%d-%H%M%S").to_string(),
        caches: stats,
    }
}

pub fn write_cache_stats_json(path: &std::path::Path) -> std::io::Result<()> {
    let stats = dump_all_cache_stats();
    let json = serde_json::to_string_pretty(&stats)?;
    std::fs::write(path, json)
}
```

### py-spy Profiling Script (PowerShell)
```powershell
# profile_pyspy.ps1
param(
    [ValidateSet("quick", "thorough")]
    [string]$Mode = "quick",

    [string]$EntryPoint = "CLASSIC_Interface.py",

    [switch]$Native,  # Include Rust frames

    [string]$Output = ""
)

$timestamp = Get-Date -Format "yyyy-MM-dd-HHmmss"
$outputDir = "target/profiling/py-spy"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$outputFile = if ($Output) { $Output } else { "$outputDir/profile-$timestamp.svg" }

$rate = if ($Mode -eq "thorough") { 997 } else { 99 }
$duration = if ($Mode -eq "thorough") { 60 } else { 10 }

$args = @(
    "record",
    "-o", $outputFile,
    "-r", $rate,
    "-d", $duration,
    "--"
)

if ($Native) {
    $args = @("record", "--native", "-o", $outputFile, "-r", $rate, "-d", $duration, "--")
}

Write-Host "Running py-spy with rate=$rate Hz, duration=$duration s"
Write-Host "Output: $outputFile"

py-spy @args uv run python $EntryPoint

if (Test-Path $outputFile) {
    Write-Host "Profile saved to $outputFile" -ForegroundColor Green
} else {
    Write-Host "Profile generation failed!" -ForegroundColor Red
    exit 1
}
```

### dhat Profiling Integration
```rust
// In a dedicated profiling harness or test binary
// Source: dhat crate documentation

#[cfg(feature = "dhat-heap")]
#[global_allocator]
static ALLOC: dhat::Alloc = dhat::Alloc;

fn main() {
    #[cfg(feature = "dhat-heap")]
    let _profiler = {
        // Custom output path with timestamp
        let timestamp = chrono::Utc::now().format("%Y-%m-%d-%H%M%S");
        let path = format!("target/profiling/dhat/dhat-heap-{}.json", timestamp);
        dhat::Profiler::builder()
            .file_name(&path)
            .build()
    };

    // Run the workload to profile
    run_workload();

    // Profiler drops here, writes JSON file
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Perl FlameGraph scripts | inferno/cargo-flamegraph | 2019+ | 20x faster, no Perl dependency |
| Valgrind DHAT | dhat-rs | 2020+ | Cross-platform, Rust-native |
| Manual profiler integration | cargo-flamegraph | 2020+ | One-command flamegraph generation |
| Windows ETW manual | blondie backend | 2021+ | Native Windows support in cargo-flamegraph |
| py-spy without --native | py-spy --native | 2020+ | Combined Python+C/Rust stacks |

**Deprecated/outdated:**
- Perl-based flamegraph.pl: Still works but inferno is faster and Rust-native
- `perf record` manual workflows: cargo-flamegraph automates this
- Custom allocator wrappers for heap profiling: dhat provides this out of box

## Open Questions

Things that couldn't be fully resolved:

1. **py-spy Rust Thread Visibility**
   - What we know: py-spy --native shows Rust frames in the main thread
   - What's unclear: Whether Rust threads spawned via std::thread::spawn are visible (some reports suggest they're not)
   - Recommendation: Test with actual PyO3 extension; fall back to separate cargo-flamegraph if Rust threads aren't captured

2. **dhat JSON Viewer Compatibility**
   - What we know: dhat outputs JSON compatible with DHAT viewer
   - What's unclear: Whether all features of Valgrind DHAT viewer work with dhat-rs output
   - Recommendation: Use the online viewer at https://nnethercote.github.io/dh_view/dh_view.html; document any limitations found

3. **Tracing Performance Impact**
   - What we know: TRACE level with filtering should have minimal overhead
   - What's unclear: Exact overhead of AtomicU64 increments in hot paths
   - Recommendation: Benchmark cache operations with/without instrumentation to quantify; document findings

## Sources

### Primary (HIGH confidence)
- [cargo-flamegraph GitHub](https://github.com/flamegraph-rs/flamegraph) - Installation, Windows support, usage
- [inferno GitHub](https://github.com/jonhoo/inferno) - Library interface, performance benchmarks
- [dhat docs.rs](https://docs.rs/dhat/latest/dhat/) - Feature flag setup, profiler builder API
- [py-spy GitHub](https://github.com/benfred/py-spy) - Native extension profiling, Windows support
- [tracing docs.rs](https://docs.rs/tracing) - Event macros, level configuration

### Secondary (MEDIUM confidence)
- [Rust Performance Book - Profiling](https://nnethercote.github.io/perf-book/profiling.html) - Tool ecosystem overview
- [PyO3 Tracing Guide](https://pyo3.rs/v0.27.1/ecosystem/tracing.html) - PyO3 + tracing integration patterns

### Tertiary (LOW confidence)
- Blog posts on py-spy Rust thread limitations (GitHub issue #332)
- Community reports on samply Windows support

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Tools are mature, well-documented, widely used
- Architecture: HIGH - Based on existing Phase 13 patterns and official tool documentation
- Pitfalls: HIGH - Documented in official tool READMEs and issues
- py-spy Rust thread visibility: MEDIUM - Reported limitations, needs validation

**Research date:** 2026-02-04
**Valid until:** 60 days (profiling tools are stable, change infrequently)
