# Phase 4: Bounded Cache Replacement - Research

**Researched:** 2026-04-05
**Domain:** Rust concurrent cache replacement, cache observability, binding-surface parity
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### Capacity Targets
- **D-01:** Treat `.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md` as the source of truth for cache capacities and phase numbering. Implement `YAML_CACHE=128`, `SETTINGS_CACHE=64`, and `HASH_CACHE=1024`. Ignore the older conflicting values in `.planning/research/SUMMARY.md`.

### CacheStats Contract
- **D-02:** The canonical typed `CacheStats` contract for all three caches is exactly: `hits`, `misses`, `hit_rate`, `size`, and `capacity`.
- **D-03:** Cache-specific detail stays outside that canonical struct. If YAML still needs byte totals or settings still needs key listings, expose those through separate helpers or adapter-specific surfaces rather than expanding the shared `CacheStats` contract.

### Binding Exposure
- **D-04:** Phase 4 aligns cache stats across all binding surfaces now, not just Rust core. Where a binding already exposes cache stats, update it to match the new shared contract. Where a binding lacks cache-stat exposure for one of these caches, add it in this phase.
- **D-05:** Existing public cache helpers may remain, but they should derive from or stay consistent with the canonical Phase 4 `CacheStats` contract instead of defining competing shapes.

### Behavior Preservation
- **D-06:** Preserve each cache's current runtime behavior while replacing the backing store. YAML remains mtime-aware, settings remains caller-managed/manual invalidation, and the hash cache remains path-keyed with explicit clear behavior. Phase 4 does not harmonize freshness rules across the three caches.

### Test Isolation
- **D-07:** Keep the existing public clear/reset entrypoints as the supported test-isolation surface. Do not add a new public `reset_for_tests()` API.
- **D-08:** Rewrite tests to assert through public behavior and stats rather than `DashMap` internals like iteration or `contains_key()`. Internal or `#[cfg(test)]` helpers are acceptable only if strictly necessary to preserve deterministic test isolation.

### the agent's Discretion
- The exact `quick_cache` wiring per crate, as long as it honors the locked capacities above and keeps concurrency-friendly reads.
- The internal accounting approach used to produce `size` and `capacity` consistently across all three caches.
- The exact DTO/function naming for new binding-facing cache-stat helpers, as long as all bindings converge on the same canonical stats shape.

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CACHE-01 | Replace unbounded `DashMap` in `YAML_CACHE` with `quick_cache::sync::Cache` (capacity 128) | Use `quick_cache::sync::Cache<PathBuf, CachedYaml>` with preserved mtime validation and manual hit/miss accounting. |
| CACHE-02 | Replace unbounded `DashMap` in `SETTINGS_CACHE` with `quick_cache::sync::Cache` (capacity 64) | Use `quick_cache::sync::Cache<String, Arc<Vec<Yaml>>>`; preserve manual invalidation and clear/reset helpers. |
| CACHE-03 | Replace unbounded `DashMap` in `HASH_CACHE` with `quick_cache::sync::Cache` (capacity 1024) | Use `quick_cache::sync::Cache<PathBuf, String>` and add explicit stats surface alongside existing clear behavior. |
| CONS-03 | Expose consistent `CacheStats` struct (hits, misses, hit rate, size, capacity) on all three bounded caches | Define one canonical Rust struct shape per crate boundary, then adapt Node/Python/C++ surfaces to that exact shape. |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- Prioritize active work in `classic-cli/`, `classic-gui/`, and `ClassicLib-rs/`.
- Keep all business logic in Rust; bindings and UI layers stay thin wrappers.
- Maintain a single shared Tokio runtime; do not introduce new runtimes.
- Keep docs synchronized with architecture or workflow changes.
- Never write to `NUL`/`nul` on Windows.
- Consult `docs/api/README.md` before changing public Rust, bridge, GUI-consumer, or binding-facing APIs; update affected `docs/api/` pages in the same change when contracts change.
- Never run C++ tests via raw binaries or `ctest`; use the repo PowerShell wrappers.
- Node bindings must stay in sync with Rust core logic.
- Python bindings must stay in sync with Rust core logic.

## Summary

Phase 4 should use the repo's existing `quick_cache::sync::Cache` pattern from `classic-file-io-core` as the standard bounded-cache implementation. The right implementation shape is: keep per-cache semantics in Rust core, keep binding layers as DTO adapters, preserve the public clear/reset APIs already used by tests, and standardize observability on a five-field `CacheStats` contract.

The biggest hidden risk was that the milestone wording said “LRU eviction,” but official `quick_cache` documentation describes the cache policy as **S3-FIFO**, not strict LRU. The phase has been clarified to target bounded `quick_cache` eviction semantics, so tasks and tests should verify **bounded memory + observable stats**, not exact LRU victim order.

Current source also shows real contract drift: YAML exposes `cachedFiles/totalBytes` in Node and `dict[str, int]` in Python, settings exposes `keys` in its canonical struct, hash cache exposes only `cache_size`, Python settings code has stats helpers but its `.pyi` omits them, and C++ currently only exposes YAML cache size. Phase 4 is therefore both a cache-store swap and a binding-contract normalization pass.

**Primary recommendation:** Use `quick_cache::sync::Cache` in all three Rust core caches, keep custom semantic hit/miss accounting in core, and update Node/Python/C++ to expose only `hits`, `misses`, `hit_rate`, `size`, and `capacity` as the canonical stats shape.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `quick_cache` | `0.6.21` | Concurrent bounded cache backing store | Already in workspace, already used in `classic-file-io-core`, supports `new`, `get`, `insert`, `remove`, `clear`, `len`, `capacity`, lifecycle hooks, and optional built-in stats. |
| `std::sync::LazyLock` | stdlib | Static cache initialization for touched globals | Matches the roadmap note that later phases sweep toward `LazyLock`; use it for newly replaced cache statics instead of introducing more `once_cell` usage. |
| `std::sync::atomic::AtomicU64` | stdlib | Canonical hit/miss counters | Preserves current YAML/settings semantics and avoids relying on `quick_cache` hit/miss behavior where it does not match phase semantics. |
| `serde` | workspace (`1.0.x`) | Serialize Rust-side stats DTOs | Existing canonical stats structs in core crates already derive `Serialize`; keep that pattern. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tracing` | workspace | Cache hit/miss instrumentation | Keep existing `trace!(cache = ..., ...)` logging on get/miss paths. |
| NAPI-RS `#[napi(object)]` DTOs | repo standard | Typed Node cache stats surface | Use for canonical Node `CacheStats` exports. |
| PyO3 dict/typed-stub adapter pattern | repo standard | Python cache stats surface | Return canonical keys from Rust; update `.pyi` to describe them explicitly. |
| CXX bridge Rust structs/helpers | repo standard | C++ cache stats exposure | Add explicit bridge entrypoints for any cache stats C++ must expose in Phase 4. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `quick_cache::sync::Cache` | `moka` | Official `quick_cache` docs explicitly point to Moka for TTL/event-listener-heavy cases, but this phase does not need those features and `quick_cache` is already locked and in-workspace. |
| Custom atomic stats | `quick_cache` built-in `stats` feature | Built-in stats can work for direct caches like settings/hash, but YAML has mtime-aware validation; custom counters keep semantic consistency across all three caches. |
| Canonical five-field `CacheStats` | Per-cache ad-hoc DTOs (`totalBytes`, `keys`, `cachedFiles`) | Violates locked Phase 4 contract and keeps parity drift alive. |

**Installation:**

Already present in workspace:

```toml
# ClassicLib-rs/Cargo.toml
quick_cache = "0.6"
```

**Version verification:**
- `cargo search quick_cache --limit 1` → latest registry version `0.6.21`
- `cargo info quick_cache` → resolved workspace version `0.6.21`, docs `https://docs.rs/quick_cache/0.6.21`
- `ClassicLib-rs/Cargo.lock` currently resolves `quick_cache` to `0.6.21`
- Publish date could not be confirmed reliably from first-party CLI output; version currency is HIGH confidence, exact release date is MEDIUM confidence.

## Architecture Patterns

### Recommended Project Structure
```text
ClassicLib-rs/
├── business-logic/
│   ├── classic-yaml-core/src/lib.rs        # mtime-aware YAML cache + canonical stats
│   ├── classic-settings-core/src/cache.rs  # manual-invalidation settings cache + canonical stats
│   └── classic-file-io-core/src/hash.rs    # path-keyed hash cache + canonical stats
├── node-bindings/classic-node/src/         # thin NAPI stats DTO adapters
├── python-bindings/*-py/src/               # thin PyO3 adapters + updated .pyi
└── cpp-bindings/classic-cpp-bridge/src/    # explicit bridge stats entrypoints where needed
```

### Pattern 1: Core-Owned Cache Semantics
**What:** Each Rust core crate owns its cache policy, invalidation semantics, and stats accounting.
**When to use:** For all three caches in this phase.
**Example:**
```rust
// Source: docs.rs quick_cache::sync::Cache + in-repo pattern in classic-file-io-core/src/core.rs
use std::sync::LazyLock;
use quick_cache::sync::Cache;

static SETTINGS_CACHE: LazyLock<Cache<String, Arc<Vec<Yaml>>>> =
    LazyLock::new(|| Cache::new(64));

pub fn get_cached(key: &str) -> Option<Arc<Vec<Yaml>>> {
    match SETTINGS_CACHE.get(key) {
        Some(value) => {
            CACHE_HITS.fetch_add(1, Ordering::Relaxed);
            Some(value)
        }
        None => {
            CACHE_MISSES.fetch_add(1, Ordering::Relaxed);
            None
        }
    }
}
```

### Pattern 2: Preserve Cache-Specific Freshness Rules
**What:** Swap the backing store without flattening semantics.
**When to use:** YAML must stay mtime-aware; settings must stay caller-invalidated; hash cache must stay path-keyed and explicit-clear.
**Example:**
```rust
// Source: current classic-yaml-core load path + docs.rs quick_cache::sync::Cache::{get,remove,insert}
if let Some(cached) = YAML_CACHE.get(&file_path) {
    if current_modified <= cached.modified {
        CACHE_HITS.fetch_add(1, Ordering::Relaxed);
        return Ok((*cached.data).clone());
    }

    let _ = YAML_CACHE.remove(&file_path);
}

CACHE_MISSES.fetch_add(1, Ordering::Relaxed);
let yaml = load_from_disk(&file_path)?;
YAML_CACHE.insert(file_path.clone(), cached_yaml_from(yaml.clone(), current_modified));
```

### Pattern 3: Canonical Stats in Core, Thin DTO Adaptation in Bindings
**What:** Rust core computes the canonical five fields; Node/Python/C++ only rename or transport them.
**When to use:** Every binding-facing cache stats export.
**Example:**
```rust
// Source: locked Phase 4 contract + existing NAPI/PyO3 adapter patterns
#[derive(Debug, Clone, Serialize)]
pub struct CacheStats {
    pub hits: u64,
    pub misses: u64,
    pub hit_rate: f64,
    pub size: usize,
    pub capacity: usize,
}
```

### Pattern 4: Preserve Existing Test-Isolation APIs
**What:** Keep `clear_global_yaml_cache()`, `clear_cache()`, and `reset_cache_stats()` as the test hooks.
**When to use:** All new and rewritten tests.
**Example:**
```rust
// Source: existing repo tests in classic-yaml-core and classic-settings-core
clear_global_yaml_cache();
reset_cache_stats();

let stats = cache_stats();
assert_eq!(stats.hits, 0);
assert_eq!(stats.misses, 0);
```

### Anti-Patterns to Avoid
- **Strict-LRU assertions:** `quick_cache` is officially documented as S3-FIFO, not strict LRU. Do not write tests that assume exact victim identity.
- **Using `quick_cache` built-in hits/misses as the only source of truth:** This is especially wrong for YAML because stale entries can be present but semantically count as misses after mtime validation.
- **Expanding canonical `CacheStats` with `keys` or `total_bytes`:** Keep those on separate helpers if still needed.
- **Binding-owned cache logic:** Bindings should not reimplement hit/miss semantics or maintain separate cache state.
- **Requiring internals in tests:** Current YAML tests still use `YAML_CACHE.contains_key(...)`; Phase 4 should pivot those to public stats/behavior checks.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Concurrent bounded eviction | Custom `DashMap` + manual eviction list | `quick_cache::sync::Cache` | Sharding, concurrency, eviction policy, and resize behavior are already implemented and documented. |
| Cache lifecycle notifications | Homegrown eviction callback plumbing | `quick_cache::Lifecycle` hooks | Official lifecycle hooks already exist if eviction-side effects are needed later. |
| Cross-binding stats contracts | Separate ad-hoc JSON/dict/size helpers per binding | One canonical Rust `CacheStats` shape, adapted outward | Prevents Node/Python/C++ drift and matches locked Phase 4 scope. |
| YAML/settings/hash stats counting from binding layers | JS/Python counters | Rust-core atomic counters | Preserves semantics at the real cache boundary and avoids parity drift. |

**Key insight:** The deceptive complexity here is not storing values; it is preserving per-cache semantics, boundedness, and consistent observability across Rust, Node, Python, and C++ without forking behavior.

## Common Pitfalls

### Pitfall 1: Assuming `quick_cache` Is Strict LRU
**What goes wrong:** Plan or tests assume exact LRU victim order.
**Why it happens:** Milestone wording says “LRU,” but official `quick_cache` docs describe S3-FIFO.
**How to avoid:** Treat `quick_cache` as the locked implementation, but validate bounded size and observable behavior rather than exact eviction order.
**Warning signs:** Tests insert `capacity + 1` items and assert a specific oldest key was evicted.

### Pitfall 2: Using Built-In Cache Stats Where Semantics Differ
**What goes wrong:** YAML stale-entry lookups get counted as hits or affect hotness incorrectly.
**Why it happens:** `quick_cache` stats/hotness operate at raw cache access level, while YAML has an extra mtime-validity layer.
**How to avoid:** Keep explicit atomic hit/miss counters in core and derive canonical stats from them.
**Warning signs:** YAML `CacheStats` jumps on stale lookups without returning cached content.

### Pitfall 3: Breaking Existing Test Isolation
**What goes wrong:** Tests become flaky because clear/reset entrypoints no longer fully reset state.
**Why it happens:** Backing-store swap happens, but public reset helpers are not updated to clear the new cache and counters together.
**How to avoid:** Ensure existing clear/reset APIs delegate to the new cache and preserve current semantics.
**Warning signs:** Tests only pass in isolation, not in crate-wide runs.

### Pitfall 4: Leaving Binding Contracts Half-Migrated
**What goes wrong:** Rust core exposes canonical stats, but Node/Python/C++ still expose `cachedFiles`, `totalBytes`, `keys`, or `cache_size` only.
**Why it happens:** Binding wrappers are treated as optional follow-up instead of in-scope Phase 4 work.
**How to avoid:** Plan binding updates and docs/stub/parity artifact updates in the same wave as core changes.
**Warning signs:** `index.d.ts` and `.pyi` still describe old shapes after Rust core changes.

### Pitfall 5: Ignoring `quick_cache` Value Cloning
**What goes wrong:** Reads become more expensive than expected if large values are stored directly.
**Why it happens:** `quick_cache::sync::Cache::get()` returns cloned values.
**How to avoid:** Keep expensive payloads wrapped in `Arc` (`Arc<Vec<Yaml>>`, `Arc<Yaml>` inside `CachedYaml`), and only store cheap-to-clone values directly (`String` hash outputs are fine).
**Warning signs:** Removing `Arc` wrappers during refactor or copying large parsed structures on every read.

## Code Examples

Verified patterns from official sources and in-repo precedent:

### Basic bounded concurrent cache
```rust
// Source: https://docs.rs/quick_cache/latest/quick_cache/sync/struct.Cache.html
use quick_cache::sync::Cache;

let cache: Cache<String, String> = Cache::new(64);
cache.insert("alpha".to_string(), "value".to_string());
assert_eq!(cache.get("alpha"), Some("value".to_string()));
assert_eq!(cache.len(), 1);
assert_eq!(cache.capacity(), 64);
```

### Repo-approved quick_cache access pattern
```rust
// Source: ClassicLib-rs/business-logic/classic-file-io-core/src/core.rs:219-235
if let Some(cached) = self.read_cache.get(path) {
    return Ok(cached);
}

let content = self.read_file_mmap(path).await?;
self.read_cache.insert(path.to_path_buf(), content.clone());
Ok(content)
```

### Canonical stats adapter
```rust
// Source: docs.rs quick_cache Cache::{len,capacity} + existing repo AtomicU64 stats pattern
pub fn cache_stats() -> CacheStats {
    let hits = CACHE_HITS.load(Ordering::Relaxed);
    let misses = CACHE_MISSES.load(Ordering::Relaxed);
    let total = hits + misses;

    CacheStats {
        hits,
        misses,
        hit_rate: if total > 0 { hits as f64 / total as f64 } else { 0.0 },
        size: CACHE.len(),
        capacity: CACHE.capacity() as usize,
    }
}
```

### YAML stale-entry invalidation on read
```rust
// Source: current classic-yaml-core semantics + docs.rs quick_cache get/remove/insert
if let Some(cached) = YAML_CACHE.get(&file_path) {
    if modified <= cached.modified {
        CACHE_HITS.fetch_add(1, Ordering::Relaxed);
        return Ok((*cached.data).clone());
    }

    let _ = YAML_CACHE.remove(&file_path);
}

CACHE_MISSES.fetch_add(1, Ordering::Relaxed);
let fresh = parse_yaml_file(&file_path)?;
YAML_CACHE.insert(file_path.clone(), fresh.clone());
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Unbounded `DashMap` globals with ad-hoc stats | `quick_cache::sync::Cache` for bounded concurrent caching | Current `quick_cache` docs/api verified at `0.6.21` | Bounded memory, better concurrency tooling, built-in capacity/len hooks. |
| “LRU” as generic shorthand | `quick_cache` officially documents S3-FIFO scan-resistant eviction | Verified in current README/docs | Do not test exact LRU victim order; plan for bounded eviction semantics instead. |
| Binding-specific stats shapes | One canonical five-field contract | Phase 4 locked decision | Reduces parity drift and docs/stub churn. |

**Deprecated/outdated:**
- `DashMap` as the primary cache store for these globals: outdated for this phase because it provides concurrency but no bound.
- YAML Node `cachedFiles/totalBytes` as the main stats contract: outdated for the canonical Phase 4 API.
- Settings `keys` inside canonical `CacheStats`: outdated for Phase 4; keep key listings separate if still needed.
- Hash `cache_size()` as the only observability surface: insufficient for Phase 4.

## Open Questions

1. **Does the milestone require literal LRU, or is `quick_cache`'s S3-FIFO acceptable?**
   - What we know: locked implementation is `quick_cache::sync::Cache`; official docs describe S3-FIFO, not strict LRU.
   - What's unclear: whether roadmap wording needs correction or is being used loosely.
   - Recommendation: proceed with `quick_cache`, and make plan/test language target bounded eviction rather than exact LRU victim identity.

2. **How far must C++ parity go in this phase?**
   - What we know: C++ currently exposes YAML cache clear/size only; settings/hash cache stats are not surfaced there today.
   - What's unclear: whether “all bindings” means adding explicit C++ stats exports for all three caches now, or just aligning any already-exposed cache surfaces.
   - Recommendation: planner should treat this as in-scope and explicitly decide whether to add new bridge entrypoints for settings/hash stats rather than leaving it implicit.

3. **What Python contract shape should represent canonical stats?**
   - What we know: current Python style returns dicts, and current `classic_settings.pyi` is already missing existing stats declarations.
   - What's unclear: whether maintainers prefer a plain `dict[str, float|int]` stub or a `TypedDict` alias.
   - Recommendation: keep runtime return values as dicts for consistency, but define a `TypedDict` in `.pyi` to make the canonical shape explicit.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Cargo | Rust crate validation | ✓ | `1.94.0` | — |
| rustc | Rust compilation | ✓ | `1.94.0` | — |
| Bun | Node binding tests/parity workflow | ✓ | `1.3.10` | Node-only runtime tests, but Bun remains the repo standard |
| Node.js | NAPI runtime tests / CLI build | ✓ | `v25.9.0` | — |
| Python | parity/stub tooling | ✓ | `3.14.3` | — |
| uv | Python env/bootstrap | ✓ | `0.11.3` | Use existing venv manually, but repo standard is uv |

**Missing dependencies with no fallback:**
- None found.

**Missing dependencies with fallback:**
- None found.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Rust `cargo test` + Bun test + Node runtime test + Python parity/stub validation |
| Config file | `ClassicLib-rs/Cargo.toml`, `ClassicLib-rs/node-bindings/classic-node/package.json`, Python parity scripts under `tools/` |
| Quick run command | `cargo test -p classic-yaml-core -p classic-settings-core -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml` |
| Full suite command | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings && bun run parity:gate:local && bun run test:bun && bun run test:node && python tools/python_api_parity/check_parity_gate.py --repo-root . && python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CACHE-01 | YAML cache is bounded at 128 and preserves mtime-aware behavior | Rust unit/integration | `cargo test -p classic-yaml-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ inline tests in `classic-yaml-core/src/lib.rs` |
| CACHE-02 | Settings cache is bounded at 64 and preserves manual invalidation helpers | Rust unit + Node binding | `cargo test -p classic-settings-core --manifest-path ClassicLib-rs/Cargo.toml && bun test __test__/settings.spec.ts` | ✅ core tests exist; ✅ Node tests exist |
| CACHE-03 | Hash cache is bounded at 1024 and exposes canonical stats | Rust unit + Node binding + Python surface | `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml && bun test __test__/fileio.spec.ts` | ✅ core hash tests exist; ✅ Node fileio tests exist; ❌ no current hash-stats binding tests |
| CONS-03 | All three caches expose the same `CacheStats` shape on all bindings | parity/integration | `bun run parity:gate:local && bun run test:bun && python tools/python_api_parity/check_parity_gate.py --repo-root . && python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings` | ✅ Node parity tests exist; ❌ Python stubs are incomplete today; ❌ C++ cache-stats coverage not evident |

### Sampling Rate
- **Per task commit:** `cargo test -p classic-yaml-core -p classic-settings-core -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml`
- **Per wave merge:** add `bun test __test__/yaml.spec.ts __test__/settings.spec.ts __test__/fileio.spec.ts` and relevant parity commands
- **Phase gate:** Rust crate tests + Node parity/tests + Python parity/stub validation green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] Rewrite YAML tests that currently rely on `YAML_CACHE.contains_key(...)` to assert through public stats/behavior.
- [ ] Add Rust hash-cache stats tests for hits/misses/hit_rate/size/capacity.
- [ ] Add Node tests for canonical YAML stats shape and new hash-cache stats surface.
- [ ] Add Python stub declarations/tests for settings cache stats and canonical YAML/hash stats shapes.
- [ ] If C++ gains new cache-stats entrypoints, add bridge-level tests or at minimum compile-checked coverage plus docs updates.

## Sources

### Primary (HIGH confidence)
- Context7 `/arthurprs/quick-cache/v0.6.18` - confirmed official quick_cache positioning, S3-FIFO policy, custom weights, and cache API overview
- `https://docs.rs/quick_cache/latest/quick_cache/sync/struct.Cache.html` - verified `new`, `get`, `peek`, `insert`, `remove`, `clear`, `len`, `capacity`, `hits`, `misses`, and approximate-capacity wording
- `https://docs.rs/quick_cache/latest/quick_cache/trait.Lifecycle.html` - verified eviction lifecycle hooks
- `cargo search quick_cache --limit 1` / `cargo info quick_cache` - verified current registry version `0.6.21`
- `ClassicLib-rs/business-logic/classic-file-io-core/src/core.rs` - in-repo quick_cache usage precedent
- `ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs` - current YAML cache semantics, stats, and internal-test dependencies
- `ClassicLib-rs/business-logic/classic-settings-core/src/cache.rs` - current settings cache semantics and stats contract
- `ClassicLib-rs/business-logic/classic-file-io-core/src/hash.rs` - current hash cache behavior and missing stats contract
- `docs/api/classic-yaml-core.md`, `docs/api/classic-settings-core.md`, `docs/api/classic-file-io-core.md`, `docs/api/classic-config-core.md` - current contributor-facing contract docs
- `ClassicLib-rs/node-bindings/classic-node/src/{yaml.rs,settings.rs,fileio.rs}` and related tests - current Node contract shape
- `ClassicLib-rs/python-bindings/*-py/src/*.rs`, `.pyi` files - current Python contract shape and gaps

### Secondary (MEDIUM confidence)
- `https://crates.io/crates/quick_cache` search results - confirmed latest published version surface, but publish-date metadata was inconsistent across search outputs

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - official docs, cargo registry verification, and in-repo usage all agree on `quick_cache`
- Architecture: MEDIUM - repo patterns are clear, but the roadmap's “LRU” wording conflicts with the chosen crate's documented S3-FIFO policy
- Pitfalls: HIGH - backed by official quick_cache docs plus concrete source/test drift in this repo

**Research date:** 2026-04-05
**Valid until:** 2026-05-05
