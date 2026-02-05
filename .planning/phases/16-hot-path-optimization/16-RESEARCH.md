# Phase 16: Hot Path Optimization (Data-Driven) - Research

**Researched:** 2026-02-04
**Domain:** Performance optimization, profiling analysis, Rust/Python hot path optimization
**Confidence:** HIGH

## Summary

This phase optimizes hot paths identified through profiling, measuring improvements against Phase 13 benchmark baselines. The existing infrastructure from Phase 13 (Criterion benchmarks) and Phase 14 (py-spy --native, cargo-flamegraph, dhat, cache instrumentation) provides all tooling needed. The primary work is: (1) collecting profiling data via full CLI scan workflow, (2) analyzing flamegraphs to identify top hot paths by CPU time, and (3) applying targeted optimizations.

The CLASSIC codebase has three benchmarked Rust crates (yaml-core, scanlog-core, file-io-core) and uses PyO3 for Python bindings. Optimization techniques should focus on: reducing FFI crossing overhead via batching, improving cache hit rates, eliminating redundant string allocations, and leveraging SIMD where applicable. Memory allocation optimization via alternative allocators (mimalloc) is a high-impact option.

**Primary recommendation:** Profile CLI scan workflow with py-spy --native, rank hot paths by cumulative CPU time, optimize top 3+ paths using batching/caching/SIMD techniques, validate 20%+ median improvement against Criterion baselines.

## Standard Stack

The established libraries/tools for optimization in this domain:

### Profiling Tools (Already Available)
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| py-spy | 0.3+ | Combined Python+Rust stack traces | --native captures PyO3 FFI boundaries |
| cargo-flamegraph | latest | Rust-only flamegraphs | One-command SVG generation |
| dhat | 0.3+ | Heap allocation profiling | Feature-gated, DHAT viewer compatible |
| Criterion | 0.5+ | Statistical benchmarking | Already configured in Phase 13 |

### Optimization Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| mimalloc | 0.1.43 | Alternative allocator | 5x faster under contention, drop-in replacement |
| memchr | 2.7+ | SIMD string search | Pattern matching in log parsing |
| rayon | 1.10+ | Parallel iterators | Already in use, verify optimal chunk sizes |
| smallvec | 1.13+ | Stack-allocated small vectors | Avoid heap for small collections |
| compact_str | 0.8+ | Small string optimization | Reduce allocations for short strings |

### Analysis Tools
| Tool | Purpose | Integration |
|------|---------|-------------|
| critcmp | Baseline comparison | Already integrated in compare_baselines.ps1 |
| speedscope | Interactive flamegraph viewer | py-spy --format speedscope |
| DHAT viewer | Heap profile analysis | Online at nnethercote.github.io/dh_view |

**Installation (if mimalloc selected):**
```toml
# In rust/Cargo.toml workspace dependencies
[workspace.dependencies]
mimalloc = { version = "0.1.43", default-features = false }

# In specific crate Cargo.toml
[dependencies]
mimalloc = { workspace = true }

# In lib.rs or main.rs
#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;
```

## Architecture Patterns

### Optimization Workflow Pattern
```
1. PROFILE (thorough mode, 5+ iterations)
   |
   v
2. IDENTIFY (rank by cumulative CPU time)
   |
   v
3. HYPOTHESIZE (optimization technique selection)
   |
   v
4. IMPLEMENT (minimal change first)
   |
   v
5. BENCHMARK (compare against baseline)
   |
   v
6. VALIDATE (20%+ median improvement, no regressions)
   |
   (loop back to 3 if not achieved)
```

### Pattern 1: FFI Batching for PyO3 Overhead Reduction
**What:** Combine multiple small FFI calls into single batch operation
**When to use:** py-spy shows significant time in PyO3 boundary code
**Example:**
```rust
// BEFORE: Many small FFI calls
#[pyfunction]
fn contains_plugin(line: &str, plugin: &str) -> bool { ... }

// AFTER: Batch operation amortizes FFI overhead
#[pyfunction]
fn contains_plugins_batch(lines: Vec<String>, plugins: Vec<String>) -> Vec<(usize, String)> {
    // Process all at once, return matches
    lines.par_iter()
        .enumerate()
        .filter_map(|(i, line)| {
            plugins.iter()
                .find(|p| line.contains(p.as_str()))
                .map(|p| (i, p.clone()))
        })
        .collect()
}
```

### Pattern 2: Cache Warming and Hit Rate Optimization
**What:** Pre-populate caches before hot loops, monitor hit rates
**When to use:** Cache instrumentation shows low hit rate (<80%)
**Example:**
```rust
// Pre-warm cache before scan loop
pub fn warm_yaml_cache(paths: &[PathBuf]) -> Result<(), YamlError> {
    // Batch load common configs before processing
    for path in paths {
        let _ = load_yaml_file(path)?;
    }
    Ok(())
}

// Monitor hit rate during optimization
let stats = cache_stats();
tracing::info!(hit_rate = %stats.hit_rate, "Cache performance");
```

### Pattern 3: String Allocation Reduction
**What:** Reuse buffers, use &str instead of String where possible
**When to use:** dhat shows many small string allocations in hot path
**Example:**
```rust
// BEFORE: Allocates String per line
fn process_lines(content: &str) -> Vec<String> {
    content.lines().map(|l| l.to_string()).collect()
}

// AFTER: Work with references, only allocate when needed
fn process_lines(content: &str) -> Vec<&str> {
    content.lines().collect()
}

// If mutation needed, reuse buffer
fn process_lines_mut(content: &str, buffer: &mut String) {
    for line in content.lines() {
        buffer.clear();
        buffer.push_str(line);
        // Process in-place
    }
}
```

### Pattern 4: SIMD Pattern Matching with memchr
**What:** Use SIMD-accelerated string search for pattern matching
**When to use:** FormID extraction, plugin detection in log lines
**Example:**
```rust
use memchr::memmem;

// SIMD-accelerated substring search
fn contains_formid_marker(line: &[u8]) -> bool {
    memmem::find(line, b"Form ID:").is_some()
}

// Multiple patterns
fn contains_any_plugin(line: &[u8], plugins: &[&[u8]]) -> Option<&[u8]> {
    for plugin in plugins {
        if memmem::find(line, plugin).is_some() {
            return Some(plugin);
        }
    }
    None
}
```

### Anti-Patterns to Avoid
- **Premature optimization:** Always profile first, never guess hot paths
- **Micro-benchmarking without integration:** A 50% improvement in a 1% path is negligible
- **Optimizing cold paths:** Focus on paths that consume >5% of total time
- **Breaking API contracts:** Add new faster APIs, deprecate old ones gracefully
- **Ignoring measurement noise:** Use >=5 iterations, report median not mean

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fast string search | Manual byte scanning | memchr crate | SIMD-optimized, handles edge cases |
| Alternative allocator | Custom allocator | mimalloc/jemalloc | Proven, drop-in replacement |
| Parallel iteration | Manual thread pools | rayon | Work-stealing, optimal chunking |
| Small string optimization | Manual inline storage | compact_str/smallvec | Tested, zero-cost abstraction |
| Flamegraph generation | Custom sampling | cargo-flamegraph/py-spy | Handles symbols, unwinding |

**Key insight:** Optimization libraries are heavily tested and tuned. Custom solutions rarely match their performance and add maintenance burden.

## Common Pitfalls

### Pitfall 1: Profiling Without Realistic Data
**What goes wrong:** Hot paths identified don't match production behavior
**Why it happens:** Using synthetic/trivial test data for profiling
**How to avoid:** Use actual crash logs from sample_logs/, realistic YAML configs
**Warning signs:** Flamegraph shows unexpected functions as hot

### Pitfall 2: Optimizing Based on Single Profile Run
**What goes wrong:** False positives from noise, temporary system state
**Why it happens:** Single profiling run has high variance
**How to avoid:** Run 5+ profiling iterations, use statistical analysis
**Warning signs:** Inconsistent hot path rankings between runs

### Pitfall 3: Regression in Non-Optimized Paths
**What goes wrong:** Optimization inadvertently slows other code paths
**Why it happens:** Shared code, cache pollution, resource contention
**How to avoid:** Run full benchmark suite after each optimization, not just target
**Warning signs:** >5% slowdown in any benchmark not being optimized

### Pitfall 4: Measuring Wrong Metric
**What goes wrong:** Claimed improvement doesn't match real-world impact
**Why it happens:** Optimizing latency when throughput matters, or vice versa
**How to avoid:** Match metric to use case (CLI: throughput, GUI: latency)
**Warning signs:** User-perceived performance doesn't improve

### Pitfall 5: FFI Overhead Masking Rust Performance
**What goes wrong:** Fast Rust code appears slow due to Python boundary
**Why it happens:** Many small FFI crossings accumulate overhead
**How to avoid:** Use py-spy --native to see combined stacks, batch FFI calls
**Warning signs:** PyO3 functions dominate flamegraph, Rust internals fast

### Pitfall 6: Cache Thrashing Under Parallel Load
**What goes wrong:** Multi-threaded optimization slower than single-threaded
**Why it happens:** Lock contention, false sharing, cache invalidation
**How to avoid:** Profile with realistic concurrency, use lock-free structures
**Warning signs:** rayon parallel worse than sequential

## Code Examples

Verified patterns from the existing codebase and official sources:

### Profiling Workflow (CLI Scan)
```powershell
# Step 1: Thorough profiling (5 iterations)
foreach ($i in 1..5) {
    ./scripts/profile/run_pyspy.ps1 -Mode thorough -EntryPoint CLASSIC_ScanLogs.py `
        -Output "target/profiling/pyspy/scan-run-$i.svg" -Native
}

# Step 2: Analyze with speedscope for interactive exploration
./scripts/profile/run_pyspy.ps1 -Mode thorough -EntryPoint CLASSIC_ScanLogs.py `
    -Format speedscope -Output "target/profiling/pyspy/scan-interactive.json"
# Open at https://speedscope.app
```

### Baseline Comparison Workflow
```powershell
# Establish pre-optimization baseline
./scripts/bench/run_benchmarks.ps1 -Mode thorough -SaveBaseline -BaselineName "pre-opt-phase16"

# After optimization, compare
./scripts/bench/run_benchmarks.ps1 -Mode thorough -Compare -BaselineName "pre-opt-phase16"

# Export for documentation
./scripts/bench/compare_baselines.ps1 -Baseline "pre-opt-phase16" -ExportJson "phase16-results.json"
```

### Criterion Regression Threshold Configuration
```rust
// Current config in benches/common/config.rs
// Thorough mode: 1% noise threshold
// Quick mode: 3% noise threshold

// For optimization validation, use thorough mode
// 20% improvement target exceeds noise threshold significantly
```

### Alternative Allocator Integration
```rust
// In rust/business-logic/classic-scanlog-core/src/lib.rs
// Only enable via feature flag for benchmarking comparison

#[cfg(feature = "mimalloc")]
#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

// Cargo.toml
[features]
default = []
mimalloc = ["dep:mimalloc"]

[dependencies]
mimalloc = { version = "0.1.43", optional = true }
```

### Cache Statistics Integration
```python
# From Phase 14 infrastructure
import classic_yaml
import classic_settings

# Before optimization
pre_stats = {
    'yaml': classic_yaml.cache_stats(),
    'settings': classic_settings.cache_stats()
}

# Run workload...

# After optimization
post_stats = {
    'yaml': classic_yaml.cache_stats(),
    'settings': classic_settings.cache_stats()
}

# Compare hit rates
print(f"YAML hit rate: {pre_stats['yaml']['hit_rate']:.2%} -> {post_stats['yaml']['hit_rate']:.2%}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| glibc malloc | mimalloc/jemalloc | 2020+ | 5x faster under contention |
| Manual pattern matching | memchr SIMD | 2018+ | 10x faster substring search |
| py-spy Python-only | py-spy --native | 2020+ | Combined Python+Rust stacks |
| Guessing hot paths | Data-driven profiling | Always | Correct optimization targets |
| Mean benchmark results | Median benchmark results | Best practice | More stable, outlier-resistant |

**Deprecated/outdated:**
- Perl flamegraph scripts: Use cargo-flamegraph/inferno
- Manual sampling profilers: Use py-spy for Python, cargo-flamegraph for Rust
- String::from() in hot loops: Use &str references or pre-allocated buffers

## Open Questions

Things that couldn't be fully resolved:

1. **Which specific hot paths will be revealed?**
   - What we know: Phase 14 infrastructure ready, target/profiling/ currently empty
   - What's unclear: Actual hot paths won't be known until profiling runs
   - Recommendation: First plan task is profiling data collection; subsequent tasks TBD based on results

2. **mimalloc vs jemalloc for this workload?**
   - What we know: mimalloc generally faster for short-lived allocations; jemalloc better for long-running services
   - What's unclear: Which suits CLASSIC's allocation pattern (batch processing with caching)
   - Recommendation: Try mimalloc first (simpler integration); benchmark both if results unclear

3. **Optimal rayon chunk size for log processing?**
   - What we know: Default chunk sizing works, may not be optimal
   - What's unclear: Ideal chunk size depends on log size distribution
   - Recommendation: Profile with different chunk sizes if rayon appears in hot path

4. **Python startup overhead contribution?**
   - What we know: Rust orchestrator handles processing; Python does orchestration
   - What's unclear: How much of CLI time is Python import/startup vs actual work
   - Recommendation: Profile full lifecycle; if startup dominates, may need lazy imports

## Sources

### Primary (HIGH confidence)
- [py-spy GitHub](https://github.com/benfred/py-spy) - Native extension profiling documentation
- [Criterion.rs Documentation](https://bheisler.github.io/criterion.rs/book/) - Benchmark configuration, statistical analysis
- [The Rust Performance Book](https://nnethercote.github.io/perf-book/) - Heap allocations, profiling tools
- [memchr GitHub](https://github.com/BurntSushi/memchr) - SIMD string search API
- Phase 13/14 verification reports - Existing infrastructure details

### Secondary (MEDIUM confidence)
- [PyO3 Performance Guide](https://pyo3.rs/main/performance) - FFI overhead reduction strategies
- [mimalloc GitHub](https://github.com/microsoft/mimalloc) - Allocator performance benchmarks
- [Brendan Gregg's Flamegraphs](https://www.brendangregg.com/flamegraphs.html) - Flamegraph interpretation

### Tertiary (LOW confidence)
- WebSearch results on Rust optimization techniques (various blog posts)
- Community discussions on PyO3 performance (GitHub issues)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Tools already established in Phase 13/14
- Optimization techniques: HIGH - Well-documented Rust patterns
- Architecture patterns: MEDIUM - Specific application depends on profiling results
- Hot path identification: LOW - Requires actual profiling data (not yet collected)

**Research date:** 2026-02-04
**Valid until:** 60 days (optimization techniques stable, profiling results determine specifics)
