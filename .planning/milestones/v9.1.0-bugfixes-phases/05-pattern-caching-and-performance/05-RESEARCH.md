# Phase 05: Pattern Caching and Performance - Research

**Researched:** 2026-04-05
**Domain:** Rust hot-path matcher caching, Aho-Corasick migration, and Criterion performance validation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### Important-mod matcher
- **D-01:** `detect_mods_important` moves from per-entry `Regex::new(...)` calls to an `Aho-Corasick` matcher.
- **D-02:** The matcher should use `LeftmostLongest` semantics when overlaps need disambiguation.
- **D-03:** Matching should continue to operate over one combined lowercase text surface built from plugin names plus XSE module names, to stay closest to current behavior.
- **D-04:** The old regex-per-entry path must not be removed until fixture-backed parity is proven against the existing behavior.

### Shared pattern cache
- **D-05:** `detect_mods_single`, `detect_mods_double`, and `detect_mods_batch` should share internal compile/normalization helpers where that directly reduces duplicated hot-path setup, but they should not be forced into one universal cache abstraction.
- **D-06:** Compiled pattern caches should be process-wide and bounded, not per-run and not unbounded.
- **D-07:** The cache/backend pattern should reuse the established `LazyLock` + `quick_cache` approach already used for new global caches in this repo.
- **D-08:** Cache keys should come from normalized content hashes of the mod-list inputs, and normal lifecycle should be hash-keyed reuse plus bounded eviction rather than manual reset hooks.

### Benchmark proof
- **D-09:** Phase 5 benchmark proof should extend the existing `classic-scanlog-core` Criterion bench setup rather than introducing a new bridge-only benchmark harness by default.
- **D-10:** Benchmarks should use both real crash-log fixtures and synthetic hotspot-focused inputs so the work is both realistic and isolatable.
- **D-11:** Before/after evidence should use local Criterion baseline save/compare flows; raw baseline captures should stay out of git unless a later request explicitly asks for a shareable export.
- **D-12:** Each locked hotspot should show measurable improvement, or the implementation should explain why a chosen structural change is still required.

### Optimization breadth
- **D-13:** Phase 5 may take a broader cleanup pass inside the already-touched `mod_detector` and C++ bridge files instead of limiting itself to the exact current call sites.
- **D-14:** Adjacent regex/static-init cleanup inside those touched files is in scope when it directly supports the locked hotspot work.
- **D-15:** Supporting cleanup may still land even if it is not independently benchmark-visible, as long as it directly enables the locked Phase 5 performance changes or removes duplicate hot-path setup.
- **D-16:** Similar hotspots discovered outside the locked Phase 5 paths should be recorded and deferred, not folded into scope automatically.

### the agent's Discretion
- Exact cache capacities and key-shape details for the new pattern caches, as long as they stay bounded and hash-keyed.
- Exact helper names and internal factoring used to share compile/normalization logic across the touched functions.
- Exact benchmark group names, input sizes, and how the bridge crash-pattern hotspot is represented inside the existing scanlog bench harness.

### Deferred Ideas (OUT OF SCOPE)
- `ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs` has separate synchronous parser utilities that also construct `LogParser::new(None)` per call; note this as a later hotspot unless Phase 5 work proves it is required for the locked goals.
- Repo-wide `once_cell::sync::Lazy` to `LazyLock` conversion remains Phase 7, not Phase 5.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PERF-01 | Cache compiled regex patterns in `detect_mods_single`, `detect_mods_double`, `detect_mods_batch` keyed by hash of mod list contents | Shared helper + bounded `quick_cache` + normalized content hash guidance |
| PERF-02 | Replace per-entry `Regex::new` in `detect_mods_important` with `str::contains` or AhoCorasick for large lists | Prescribed `Aho-Corasick` + `MatchKind::LeftmostLongest` + parity blocker/test strategy |
| PERF-03 | Replace per-call `LogParser::new(None)` in C++ bridge `detect_crash_pattern` with module-level `LazyLock<LogParser>` | Thin-bridge `LazyLock` reuse pattern and bridge test/bench guidance |
| PERF-04 | Add criterion benchmarks for `detect_mods_important`, `detect_mods_single`/`batch`, `detect_crash_pattern`, and mmap read throughput with before/after measurements | Existing harness extension plan, baseline commands, real+synthetic input strategy |
| CONS-04 | Use `LazyLock` with `Regex::new().unwrap()` for static patterns in `mod_detector` to move compilation failure to startup | `LazyLock` startup-init guidance and static-regex cleanup rules |
</phase_requirements>

## Summary

Phase 5 should stay entirely in Rust core plus the thin C++ bridge wrapper: cache compiled matchers process-wide with `LazyLock<quick_cache::sync::Cache<...>>`, migrate `detect_mods_important` from per-entry literal regex compilation to a single `Aho-Corasick` automaton, and reuse one module-level `LogParser` in `detect_crash_pattern`. This matches the repo’s Phase 4 cache pattern, the repo-wide move toward `LazyLock`, and the locked decision to keep bridge layers adapter-only.

The biggest hidden risk is semantic drift, not implementation difficulty. `detect_mods_important` currently searches one combined lowercase plugin/XSE text surface and has output quirks that tests already codify. `Aho-Corasick` can preserve the needed leftmost disambiguation, but only if parity is proven before deleting the old regex path. The second hidden risk is false benchmark proof: Criterion must measure the hot path without accidentally benchmarking setup noise, and baseline captures must remain local.

**Primary recommendation:** Build function-specific bounded matcher caches with `LazyLock + quick_cache`, migrate `detect_mods_important` to `Aho-Corasick` with `MatchKind::LeftmostLongest`, keep the legacy path until fixture parity passes, and extend the existing `scanlog_benchmarks.rs` harness with local Criterion baselines.

## Project Constraints (from AGENTS.md)

- Prioritize active work in `classic-cli/`, `classic-gui/`, and `ClassicLib-rs/`.
- Keep all business logic in Rust; shared behavior, validation, persistence rules, and state transitions belong in Rust core crates unless the task is explicitly interface-only.
- Keep non-interface layers thin; C++, Python, Node, and other bindings should wrap Rust APIs rather than reimplement logic.
- Maintain a single shared Tokio runtime from Rust core facilities; do not introduce independent runtimes.
- Keep docs synchronized with architecture or workflow changes, especially `README.md` and `AGENTS.md`.
- Never write to `NUL` or `nul` as a file path on Windows.
- Consult `docs/api/README.md` before changing public Rust, bridge, GUI-consumer, or binding-facing APIs; if contract-shaping behavior changes, update the affected `docs/api/` pages in the same change.
- Never run C++ tests by invoking test binaries or raw `ctest`; use the repo PowerShell wrappers for C++ tests.
- Native C++ targets are Windows-focused and MSVC-based.
- Node and Python bindings should stay in sync with Rust core logic.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `std::sync::LazyLock` | std 1.94.1 docs verified | Process-wide lazy singleton init | Repo is actively standardizing new statics on `LazyLock`; current docs confirm thread-safe lazy init for statics |
| `quick_cache::sync::Cache` | workspace `0.6` (`0.6.21` latest, crates.io 2026-03-19) | Bounded concurrent matcher caches | Phase 4 already established this exact repo pattern; docs confirm concurrent, shard-based cache access |
| `aho-corasick` | workspace `1.1.4` (latest `1.1.4`, crates.io 2025-10-28) | Replace literal regex-per-entry scanning in `detect_mods_important` | Official docs support `MatchKind::LeftmostLongest` and explain why it matches POSIX-style longest alternation semantics |
| `regex` | workspace `1.12.2` (`1.12.3` latest, crates.io 2026-02-03) | Combined regex for `single`/`double`/`batch` matcher compilation | Already in use; keep it for alternation-based matchers that are not pure literal dictionary search |
| `xxhash-rust` | workspace `0.8` (`0.8.15` latest, crates.io 2024-12-30) | Fast normalized-content hash keys | Already present specifically for cache-key use; appropriate for fast non-cryptographic process-local keys |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `criterion` | pinned `0.6.0` (`0.8.2` latest, crates.io 2026-02-04) | Benchmark harness and baseline comparison | Use the existing repo harness; do **not** upgrade Criterion in this phase |
| `rayon` | workspace `1.10` | Parallel batch processing in `detect_mods_batch` | Keep for batch fan-out after compile/cache work is hoisted out of the closure |
| `indexmap` | workspace `2.7` | Preserve input order for parity-sensitive flows | Use wherever YAML order or first-match priority still matters |
| `HashSet` / `Arc` | std | Presence tracking and cheap cached-value cloning | Use `Arc<T>` inside `quick_cache` because cache `get` clones values |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `Aho-Corasick` for `detect_mods_important` | `RegexSet` / one giant alternation | Worse fit because inputs are escaped literals and overlap semantics are more explicit in `Aho-Corasick` |
| `quick_cache` | `DashMap` + manual eviction | Violates repo pattern and reopens unbounded-cache risk |
| `LazyLock` | `once_cell::sync::Lazy` | Repo direction is `LazyLock`; Phase 7 handles global sweep, but new Phase 5 statics should use `LazyLock` now |
| Criterion baselines | ad hoc `Instant` timing | No statistical comparison, no baseline save/load flows, weaker regression signal |

**Installation:**

No new dependencies are required for the locked implementation. `aho-corasick`, `regex`, `quick_cache`, `xxhash-rust`, and Criterion are already present in the workspace.

**Version verification:**

- `aho-corasick`: latest `1.1.4` (crates.io API, published 2025-10-28)
- `quick_cache`: latest `0.6.21` (crates.io API, published 2026-03-19)
- `regex`: latest `1.12.3` (crates.io API, published 2026-02-03)
- `criterion`: latest `0.8.2` (crates.io API, published 2026-02-04); repo intentionally pins `0.6.0`
- `xxhash-rust`: latest `0.8.15` (crates.io API, published 2024-12-30)

## Architecture Patterns

### Recommended Project Structure
```text
ClassicLib-rs/
├── business-logic/classic-scanlog-core/
│   ├── src/mod_detector.rs          # shared normalization, compile helpers, caches
│   └── benches/scanlog_benchmarks.rs# Criterion proof, real + synthetic inputs
└── cpp-bindings/classic-cpp-bridge/
    └── src/scanner.rs               # thin LazyLock<LogParser> bridge adapter
```

### Pattern 1: Function-specific bounded compile caches
**What:** Use separate process-wide caches per matcher family, but share normalization and compile helper code.

**When to use:** `detect_mods_single`, `detect_mods_double`, and `detect_mods_batch` where compile/setup cost dominates and matcher value types differ.

**Prescriptive rules:**
- Cache compiled values, not raw inputs.
- Cache key must be a normalized-content hash, not pointer identity and not raw YAML bytes.
- Put `Arc<Regex>` / `Arc<CompiledMatcher>` in `quick_cache`; `Cache::get` clones values.
- Do not force `single`/`double`/`batch` into one universal cache type.

**Example:**
```rust
// Source: repo Phase 4 cache pattern + std LazyLock docs + quick_cache docs
use quick_cache::sync::Cache;
use regex::Regex;
use std::sync::{Arc, LazyLock};

static SINGLE_PATTERN_CACHE: LazyLock<Cache<u64, Arc<Regex>>> =
    LazyLock::new(|| Cache::new(64));
```

### Pattern 2: Literal matcher migration for `detect_mods_important`
**What:** Build one `Aho-Corasick` automaton over lowercased `entry.detect` literals, search one combined lowercased plugin/XSE surface, then interpret matches against the original entry list.

**When to use:** `detect_mods_important` only.

**Prescriptive rules:**
- Lowercase patterns before building the automaton; the locked haystack is already lowercased.
- Use `MatchKind::LeftmostLongest`.
- Treat Aho matches as detection evidence; still apply existing `exclude_when`, GPU, and output formatting logic in source order.
- Keep the old regex path available until fixture parity passes.

**Example:**
```rust
// Source: aho-corasick MatchKind docs
use aho_corasick::{AhoCorasick, MatchKind};

let patterns: Vec<String> = entries.iter().map(|e| e.detect.to_lowercase()).collect();
let ac = AhoCorasick::builder()
    .match_kind(MatchKind::LeftmostLongest)
    .build(&patterns)
    .unwrap();
let found = ac.is_match(&all_text_lower);
```

### Pattern 3: Thin bridge singleton reuse
**What:** Replace per-call parser allocation in the C++ bridge with a module-level `LazyLock<LogParser>`.

**When to use:** `detect_crash_pattern` and only similar bridge-local parser helpers in the touched file.

**Example:**
```rust
// Source: std LazyLock docs + current bridge call site
use classic_scanlog_core::LogParser;
use std::sync::LazyLock;

static CRASH_PATTERN_PARSER: LazyLock<LogParser> =
    LazyLock::new(|| LogParser::new(None).expect("default parser should compile"));
```

### Pattern 4: Benchmark inside the existing Criterion harness
**What:** Add Phase 5 benches to `benches/scanlog_benchmarks.rs` instead of creating a new harness.

**When to use:** All before/after proof for this phase.

**Prescriptive rules:**
- Use existing real crash-log fixtures for realism.
- Add synthetic plugin/XSE lists to isolate compile-vs-match cost.
- Benchmark setup outside the inner loop when measuring match speed; benchmark compile cost in a separate group.
- Use local baselines (`--save-baseline`, `--baseline`); do not commit raw baseline directories.

### Anti-Patterns to Avoid
- **Recompiling inside Rayon closures:** compile once, then parallelize per-log work.
- **One shared “universal” matcher cache:** different matcher semantics and value types will make it fragile.
- **Using overlapping Aho APIs with `LeftmostLongest`:** official docs say leftmost modes do not support overlapping searches.
- **Keying caches on unordered or incomplete normalization:** if values/order affect behavior, the hash must reflect that exact normalized representation.
- **Asserting exact eviction victim order:** Phase 4 established validating boundedness via size/capacity/stats, not victim identity.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-literal hot-path search | per-entry escaped regex loop | `aho-corasick` | Officially supports `LeftmostLongest`; better fit for literal dictionaries |
| Process-wide bounded matcher cache | `Mutex<HashMap<...>>` + custom eviction | `LazyLock<quick_cache::sync::Cache<...>>` | Repo-standard, concurrent, bounded, already proven in Phase 4 |
| Lazy singleton lifecycle | manual `Once` / ad hoc globals | `std::sync::LazyLock` | Simpler, standard, matches repo direction |
| Performance proof | custom `Instant` logging | Criterion baselines | Save/compare workflow and statistical reporting already exist |
| Cache hashing | ad hoc string concatenation without normalization contract | normalized content + `xxhash-rust` | Fast and explicit; avoids accidental cache collisions or misses |

**Key insight:** The risky part here is semantics, not plumbing. Reuse battle-tested crates for matching, caching, hashing, and benchmarking so the phase only changes behavior where the milestone explicitly requires it.

## Common Pitfalls

### Pitfall 1: Losing parity when replacing literal regexes
**What goes wrong:** `detect_mods_important` starts matching different literals or different winners on overlaps.

**Why it happens:** Switching algorithms without preserving combined-text search and leftmost-longest disambiguation.

**How to avoid:** Build the automaton on lowercased literals, search the single combined lowercase surface, and compare new-vs-old outputs on fixtures before deleting the legacy path.

**Warning signs:** Aho results differ on prefix pairs or fixture outputs change only for similarly named mods.

### Pitfall 2: Cache keys that do not fully represent behavior
**What goes wrong:** Wrong compiled matcher is reused for a different mod list.

**Why it happens:** Hash key ignores lowercasing, sort policy, warning payload, or function-specific compile mode.

**How to avoid:** Hash the exact normalized representation consumed by the compiler helper. If output semantics differ by function, keep separate caches.

**Warning signs:** Intermittent wrong matches after YAML changes, especially across tests that reuse process state.

### Pitfall 3: Expensive value cloning from `quick_cache`
**What goes wrong:** Cache hits still allocate heavily.

**Why it happens:** `quick_cache::sync::Cache::get` clones the stored value.

**How to avoid:** Store `Arc<T>` for compiled matchers.

**Warning signs:** Allocation counts stay high even when hit rate is high.

### Pitfall 4: Accidentally changing `detect_mods_important` display semantics
**What goes wrong:** “not installed” lines or GPU mismatch lines appear/disappear incorrectly.

**Why it happens:** Current function has specific gating: missing universal mods only emit when `user_gpu` is known; GPU-specific entries behave differently.

**How to avoid:** Treat matching as a drop-in replacement only. Leave exclusion/GPU/output branches untouched.

**Warning signs:** Existing unit tests around GPU or `exclude_when` start failing.

### Pitfall 5: Benchmarking setup noise instead of the hotspot
**What goes wrong:** Bench numbers hide the improvement or show fake regressions.

**Why it happens:** Parser/matcher construction occurs inside the measured closure, or baseline workflows are skipped.

**How to avoid:** Separate compile/create benches from match/use benches; use Criterion baselines locally.

**Warning signs:** “Optimized” path is still dominated by constructor cost, or quick-mode results fluctuate wildly without a saved baseline.

### Pitfall 6: Assuming missing `gnuplot` blocks Criterion
**What goes wrong:** Benchmark work is unnecessarily descoped.

**Why it happens:** `criterion.toml` prefers gnuplot, but the local environment does not have it.

**How to avoid:** Use the built-in plotters fallback. Local listing already showed: `Gnuplot not found, using plotters backend`.

**Warning signs:** Bench commands fail only because the plan incorrectly assumes gnuplot is mandatory.

## Code Examples

Verified patterns from official sources and repo code:

### `Aho-Corasick` leftmost-longest matcher
```rust
// Source: https://docs.rs/aho-corasick/latest/aho_corasick/enum.MatchKind.html
use aho_corasick::{AhoCorasick, MatchKind};

let ac = AhoCorasick::builder()
    .match_kind(MatchKind::LeftmostLongest)
    .build(["sam", "samwise"])
    .unwrap();
assert!(ac.is_match("samwise"));
```

### Repo-standard bounded cache wrapper
```rust
// Source: classic-settings-core/src/cache.rs and classic-yaml-core/src/lib.rs
use quick_cache::sync::Cache;
use std::sync::{Arc, LazyLock};

static PATTERN_CACHE: LazyLock<Cache<u64, Arc<String>>> =
    LazyLock::new(|| Cache::new(64));
```

### Module-level `LazyLock` parser reuse
```rust
// Source: std LazyLock docs + cpp bridge detect_crash_pattern hotspot
use classic_scanlog_core::LogParser;
use std::sync::LazyLock;

static PARSER: LazyLock<LogParser> =
    LazyLock::new(|| LogParser::new(None).expect("parser init should succeed"));
```

### Criterion baseline workflow
```powershell
# Source: Criterion.rs command-line docs
$env:BENCH_MODE = "thorough"
cargo bench -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml --bench scanlog_benchmarks -- --save-baseline phase5-before

# after implementation
cargo bench -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml --bench scanlog_benchmarks -- --baseline phase5-before
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-entry escaped regex for literal dictionaries | `Aho-Corasick` with explicit match semantics | Mature/current (`aho-corasick` 1.1.x) | Faster multi-literal scans and clearer overlap control |
| `once_cell::sync::Lazy` for new statics | `std::sync::LazyLock` | In std since 1.80; repo now prefers it for new work | Standard-library lazy init; matches Phase 4/7 direction |
| Unbounded global caches | bounded `quick_cache` | Already established in Phase 4 | Prevents long-lived process growth |
| Ad hoc benchmark timing | Criterion save/load baselines | Current repo benchmark policy | Statistical comparison and local baseline preservation |

**Deprecated/outdated:**
- Per-entry regex compilation for escaped literals in a hot path
- New `once_cell::sync::Lazy` usage in touched Phase 5 code
- Committing raw Criterion baseline directories by default

## Open Questions

1. **What exact cache capacities should Phase 5 start with?**
   - What we know: caches must be bounded and process-wide; repo precedent uses fixed capacities (64/128/1024).
   - What's unclear: the real cardinality of distinct mod-list shapes in long-lived workloads.
   - Recommendation: start with small fixed capacities (64 per matcher-family cache) and validate with hit/miss stats plus benches, not guesswork.

2. **How should parity proof keep the old `detect_mods_important` path alive?**
   - What we know: the old path must remain until fixture parity is proven.
   - What's unclear: whether the legacy implementation should stay inline, move behind a private helper, or live only in tests.
   - Recommendation: move the current regex implementation behind a private test-callable helper in the same file, then delete it only after fixture-backed parity lands.

3. **How should `detect_crash_pattern` be benchmarked without a new bridge harness?**
   - What we know: the lock is to use the existing scanlog Criterion harness.
   - What's unclear: the best synthetic workload shape for repeated `parse_crash_header` calls.
   - Recommendation: add a scanlog benchmark group that repeatedly calls a small Rust helper mirroring the bridge’s `detect_crash_pattern` logic, once with per-call parser construction and once with cached parser reuse.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `cargo` | Rust tests and Criterion benches | ✓ | 1.94.0 | — |
| `rustc` | Compile/test/bench | ✓ | 1.94.0 | — |
| Python | Optional docs/parity side work only | ✓ | 3.14.3 | Not required for locked Phase 5 core work |
| `gnuplot` | Preferred Criterion plotting backend | ✗ | — | Criterion already falls back to `plotters` |

**Missing dependencies with no fallback:**
- None.

**Missing dependencies with fallback:**
- `gnuplot` — use Criterion’s `plotters` fallback.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Rust unit tests + Criterion `0.6.0` bench harness |
| Config file | `ClassicLib-rs/Cargo.toml`, `ClassicLib-rs/criterion.toml`, `ClassicLib-rs/benches/common/config.rs` |
| Quick run command | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml detect_mods_important` |
| Full suite command | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml && cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml detect_crash_pattern && cargo bench -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml --bench scanlog_benchmarks -- --test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PERF-01 | Shared cached regex compilation for `single`/`double`/`batch` | unit + focused bench | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml detect_mods_single` | ❌ Wave 0 |
| PERF-02 | `detect_mods_important` parity with `Aho-Corasick` | unit + fixture parity | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml detect_mods_important` | ❌ Wave 0 |
| PERF-03 | Cached parser reuse in bridge helper | unit + focused bench | `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml detect_crash_pattern` | ❌ Wave 0 |
| PERF-04 | Bench proof for all locked hotspots | benchmark | `cargo bench -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml --bench scanlog_benchmarks -- --list` | ✅ |
| CONS-04 | Static regexes in touched file compile at startup via `LazyLock` | unit/build | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml detect_mods_important`
- **Per wave merge:** `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml && cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml detect_crash_pattern`
- **Phase gate:** save a local baseline, run before/after comparison, and keep unit tests green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] Add fixture-backed parity tests that compare legacy-regex and new-Aho implementations for `detect_mods_important`
- [ ] Add cache-reuse tests for `detect_mods_single` / `detect_mods_double` / `detect_mods_batch` that prove compile helpers are reused without asserting eviction victim order
- [ ] Add at least one positive `detect_crash_pattern` bridge test, not just the existing empty-input test
- [ ] Extend `benches/scanlog_benchmarks.rs` with dedicated Phase 5 groups for `detect_mods_important`, cached regex paths, and bridge-style crash-pattern parsing

## Sources

### Primary (HIGH confidence)
- Repo source: `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs` - current hotspot behavior, existing tests, parity-sensitive output rules
- Repo source: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` - current per-call `LogParser::new(None)` hotspot and existing bridge tests
- Repo source: `ClassicLib-rs/business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs` - existing Criterion harness and fixtures
- Repo source: `ClassicLib-rs/business-logic/classic-settings-core/src/cache.rs` and `classic-yaml-core/src/lib.rs` - canonical `LazyLock + quick_cache` repo pattern
- Context7 `/burntsushi/aho-corasick` - match semantics, overlapping limitations, case-insensitive builder usage
- Official docs: https://docs.rs/aho-corasick/latest/aho_corasick/enum.MatchKind.html - `LeftmostLongest` semantics and overlap restrictions
- Official docs: https://doc.rust-lang.org/std/sync/struct.LazyLock.html - lazy static behavior and poisoning model
- Official docs: https://docs.rs/quick_cache/latest/quick_cache/sync/struct.Cache.html - concurrent cache semantics, cloning-on-get behavior
- Context7 `/bheisler/criterion.rs` + official docs: https://bheisler.github.io/criterion.rs/book/user_guide/command_line_options.html - baseline save/load/compare workflow

### Secondary (MEDIUM confidence)
- crates.io API for `aho-corasick`, `quick_cache`, `regex`, `criterion`, `xxhash-rust` - current version and publish-date verification

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - repo source, official docs, and crates.io version verification agree
- Architecture: HIGH - directly constrained by CONTEXT.md plus existing Phase 4 repo pattern
- Pitfalls: HIGH - most are visible in current source/tests or explicitly documented by official Aho/quick_cache/Criterion docs

**Research date:** 2026-04-05
**Valid until:** 2026-05-05
