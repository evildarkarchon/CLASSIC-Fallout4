# Phase 6: mmap TOCTOU Safety - Research

**Researched:** 2026-04-06
**Domain:** Rust file-backed mmap safety and Criterion throughput validation on Windows
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
## Implementation Decisions

### Canonical mmap contract
- **D-01:** The Phase 6 target is `MmapOptions::map_copy_read_only()`, not `MmapOptions::map_copy()` and not `Mmap::map()`.
- **D-02:** Treat `.planning/ROADMAP.md`, `.planning/STATE.md`, and the repo research notes as canonical for this phase's mmap contract; the older `map_copy()` wording in `.planning/PROJECT.md` and `.planning/REQUIREMENTS.md` should be aligned to the `map_copy_read_only()` decision during planning/execution.

### Benchmark proof location
- **D-03:** Put the Phase 6 throughput proof in `ClassicLib-rs/business-logic/classic-file-io-core/benches/file_io_benchmarks.rs` rather than creating a new mmap-only harness or reusing the scanlog benchmark harness.
- **D-04:** Follow the established benchmark-proof pattern from Phase 5: raw Criterion baselines stay local-only, while the committed artifact is a markdown proof summary with the commands, compared variants, and results.

### Benchmark coverage
- **D-05:** The representative throughput proof should use near-threshold plus larger synthetic inputs so the mmap branch is definitely exercised and scaling above the 1 MB cutoff is visible.

### Rollout policy
- **D-06:** After the benchmark work lands, `read_file_mmap()` should use the safer mapping on all platforms. Windows benchmarking is the required validation target because that is the risky platform, but the rollout itself is not Windows-only.

### the agent's Discretion
- Exact benchmark sizes, as long as they bracket the 1 MB mmap cutoff and include larger synthetic files.
- Exact Criterion group names, baseline names, and helper structure inside `file_io_benchmarks.rs`.
- Exact doc-alignment edits across planning docs and API docs, as long as they converge on the locked `map_copy_read_only()` contract.

### Deferred Ideas (OUT OF SCOPE)
## Deferred Ideas

None - discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SAFE-05 | Switch `read_file_mmap` from `Mmap::map()` to the locked `MmapOptions::map_copy_read_only()` contract and prove acceptable throughput with Criterion | Standard stack confirms `memmap2` already exposes `map_copy_read_only()`, architecture keeps the change in `classic-file-io-core`, and benchmark guidance reuses `file_io_benchmarks.rs` with Windows-focused validation and committed markdown proof |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- Prioritize active work in `classic-cli/`, `classic-gui/`, and `ClassicLib-rs/`.
- Keep shared behavior and safety semantics in Rust core crates; bindings stay thin wrappers.
- Maintain a single shared Tokio runtime from Rust core facilities; do not introduce another runtime.
- Consult `docs/api/README.md` before changing public Rust or binding-facing behavior; update affected `docs/api/` pages in the same change.
- Keep docs synchronized with architecture/workflow changes.
- Never write to `NUL`/`nul` on Windows.
- Never run C++ tests via raw `ctest` or test binaries; use repo PowerShell wrappers.

## Summary

Phase 6 should be implemented as a narrow Rust-core change in `ClassicLib-rs/business-logic/classic-file-io-core/src/core.rs`: keep the 1 MB branch and decode pipeline intact, but replace the large-file mapping constructor with `MmapOptions::map_copy_read_only()`. Do not fork by platform and do not widen the API surface. Python bindings should inherit the behavior automatically because they already forward to `FileIOCore`.

Benchmark proof should stay in the existing `classic-file-io-core` Criterion harness. Add one focused Phase 6 group that compares `map()`, `map_copy()`, and `map_copy_read_only()` over near-threshold and larger synthetic files, reports `Throughput::Bytes`, and uses the repo's existing baseline workflow: raw Criterion baselines remain local-only, while the committed artifact is a markdown proof summary.

**Primary recommendation:** Keep production code to one constructor swap plus doc alignment, and prove the decision with a focused Windows benchmark in the existing `file_io_benchmarks.rs` harness.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `memmap2` | 0.9.10 resolved (`Cargo.lock`), workspace spec `0.9.9`; latest verified 0.9.10 published 2026-02-15 | File-backed mmap strategies: `map`, `map_copy`, `map_copy_read_only` | Already in workspace; official docs expose the exact locked API |
| `criterion` | 0.6.0 in repo; latest verified 0.8.2 published 2026-02-04 | Benchmark harness, baseline compare, HTML reports | Already used in repo benchmark proofs; upgrading is out of scope for this phase |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tempfile` | 3.27.0 resolved; latest verified 3.27.0 published 2026-03-11 | Create synthetic files for mmap benchmarks/tests | Use for benchmark fixtures and focused mmap tests |
| `tokio` | 1.49.0 workspace | Async metadata/read path around `read_file_mmap()` | Keep existing async function shape; do not introduce a new runtime |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `map_copy_read_only()` | `map_copy()` | Reintroduces writable COW semantics the scan path does not need; Microsoft documents whole-view commit charge for copy-on-write views |
| Existing `file_io_benchmarks.rs` | New mmap-only harness | Adds maintenance and breaks repo benchmark-proof pattern for no gain |
| All-platform split logic | Windows-only safer path | Violates locked rollout decision and creates avoidable divergence |

**Installation:**
```bash
# No new dependencies for this phase.
```

**Version verification:**
- `memmap2` latest verified via docs.rs/crates.io: 0.9.10 (2026-02-15)
- `criterion` repo pin verified via crates.io: 0.6.0 (2025-05-17); latest available is 0.8.2, but this phase should keep the repo-pinned 0.6.0
- `tempfile` latest verified via docs.rs/crates.io: 3.27.0 (2026-03-11)

## Architecture Patterns

### Recommended Project Structure
```text
ClassicLib-rs/
├── business-logic/classic-file-io-core/
│   ├── src/core.rs                  # Production mmap strategy change
│   ├── benches/file_io_benchmarks.rs # Phase 6 benchmark group
│   └── Cargo.toml                   # Existing Criterion bench target
└── ../docs/api/classic-file-io-core.md # Public behavior contract update
```

### Pattern 1: Single Rust-core implementation point
**What:** Change only `FileIOCore::read_file_mmap()` in `classic-file-io-core`; let Python and other consumers inherit behavior through existing wrappers.
**When to use:** Always for this phase.
**Example:**
```rust
// Source: https://docs.rs/memmap2/latest/memmap2/struct.MmapOptions.html
use memmap2::MmapOptions;
use std::fs::File;

let file = File::open("README.md")?;
let mmap = unsafe { MmapOptions::new().map_copy_read_only(&file)? };
assert!(!mmap.is_empty());
```

### Pattern 2: Compare mmap variants inside one Criterion benchmark group
**What:** Benchmark the three mapping variants as siblings in one group, keyed by file size.
**When to use:** For the committed Phase 6 throughput proof.
**Example:**
```rust
// Source: https://github.com/bheisler/criterion.rs/blob/master/book/src/user_guide/benchmarking_with_inputs.md
use criterion::{BenchmarkId, Criterion, Throughput};

fn mmap_variants(c: &mut Criterion) {
    let mut group = c.benchmark_group("phase6_mmap_variants");
    for size in [1_048_576usize + 4_096, 4 * 1_048_576, 16 * 1_048_576] {
        group.throughput(Throughput::Bytes(size as u64));
        group.bench_with_input(BenchmarkId::new("map_copy_read_only", size), &size, |b, size| {
            b.iter(|| run_variant(*size));
        });
    }
    group.finish();
}
```

### Pattern 3: Benchmark the production cost, not setup noise
**What:** Measure the same mapping + encoding-detect + decode path that production pays, but exclude unrelated cache warmup and temp-file creation from the timed loop.
**When to use:** For all Phase 6 benchmark variants.
**Example:**
```rust
// Source: Criterion FAQ + existing repo benchmark pattern
use std::hint::black_box;

b.iter(|| {
    let output = decode_variant(black_box(&path), black_box(Variant::MapCopyReadOnly));
    black_box(output)
});
```

### Anti-Patterns to Avoid
- **Windows-only production branch:** benchmark on Windows, but ship one locked safer path on all platforms.
- **New benchmark harness:** reuse `file_io_benchmarks.rs`.
- **Benchmarking `read_file()` cache hits:** that hides the mmap decision behind unrelated caching.
- **Claiming upstream safety guarantees that docs do not make:** `memmap2` still marks file-backed constructors `unsafe` at the type level.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Safer snapshot-like mmap behavior | Manual `read_to_end` snapshot layer or custom OS-specific mapping wrapper | `MmapOptions::map_copy_read_only()` | Existing crate already exposes the locked API and keeps the change small |
| Benchmark runner / comparison format | Custom scripts, ad hoc timers, committed raw Criterion directories | Existing Criterion harness + local baselines + markdown proof | Matches repo policy and Phase 5 precedent |
| Binding-specific safety logic | Python-side or bridge-side file-read workaround | Rust core behavior change only | Repo rule: business logic stays in Rust core |
| Plot/report generation | Hard dependency on external plotting tooling | Criterion default/report flow | `gnuplot` is missing locally; bench output still has a viable fallback path |

**Key insight:** The hidden complexity here is not the constructor swap; it is making the benchmark evidence trustworthy and keeping contract wording precise.

## Common Pitfalls

### Pitfall 1: Preserving stale `map_copy()` wording in milestone docs
**What goes wrong:** Planning implements `map_copy_read_only()` but leaves milestone docs claiming `map_copy()`.
**Why it happens:** `.planning/PROJECT.md` and `.planning/REQUIREMENTS.md` still carry the older contract.
**How to avoid:** Treat `06-CONTEXT.md`, `.planning/ROADMAP.md`, and `.planning/STATE.md` as canonical; align stale docs in the same phase.
**Warning signs:** PR or plan text still says `map_copy()` after code uses `map_copy_read_only()`.

### Pitfall 2: Using `map_copy()` because it sounds close enough
**What goes wrong:** The code moves from `map()` to `map_copy()` instead of the locked `map_copy_read_only()` target.
**Why it happens:** `map_copy()` is older and more familiar.
**How to avoid:** Follow the locked contract exactly. Official `memmap2` docs show `map_copy()` returns `MmapMut` and permits writes, while `map_copy_read_only()` returns `Mmap` and only needs read access.
**Warning signs:** The new code needs a writable file handle or introduces mutable mmap usage.

### Pitfall 3: Underestimating Windows copy-on-write cost
**What goes wrong:** The benchmark proves nothing because it skips `map_copy()` or uses only tiny files.
**Why it happens:** Small inputs never force the mmap branch, and Windows-specific COW commit behavior is easy to miss.
**How to avoid:** Benchmark `map()`, `map_copy()`, and `map_copy_read_only()` on files above the 1 MB threshold. Microsoft documents that `FILE_MAP_COPY` takes commit charge for the entire view.
**Warning signs:** Bench inputs at or below 1 MB, or proof text compares only two variants.

### Pitfall 4: Overstating what upstream guarantees
**What goes wrong:** Docs or comments claim `memmap2` now guarantees file-backed concurrent modification is universally safe.
**Why it happens:** The project decision is stronger than the upstream type-level docs.
**How to avoid:** Say Phase 6 adopts the locked safer snapshot-style mapping for this repo and validates it empirically on Windows; do not rewrite the unsafe rationale as if upstream removed it.
**Warning signs:** New comments say the operation is fully safe simply because `map_copy_read_only()` is used.

### Pitfall 5: Benchmarking setup instead of the variant cost
**What goes wrong:** Temp-file creation, runtime creation, or cache priming dominate measurements.
**Why it happens:** The current `file_io_benchmarks.rs` pattern creates temp data outside the loop; Phase 6 must preserve that discipline.
**How to avoid:** Prepare files and runtime outside `b.iter`, then benchmark only the variant helper.
**Warning signs:** Bench closures create files, allocate runtimes, or rewrite fixture contents.

## Code Examples

Verified patterns from official sources:

### `map_copy_read_only()` usage
```rust
// Source: https://docs.rs/memmap2/latest/memmap2/struct.MmapOptions.html
use memmap2::MmapOptions;
use std::fs::File;
use std::io::Read;

let mut file = File::open("README.md")?;
let mut contents = Vec::new();
file.read_to_end(&mut contents)?;

let mmap = unsafe { MmapOptions::new().map_copy_read_only(&file)? };
assert_eq!(&contents[..], &mmap[..]);
```

### Criterion baseline workflow
```text
// Source: https://github.com/bheisler/criterion.rs/blob/master/book/src/user_guide/command_line_options.md
cargo bench -- --save-baseline <name>
cargo bench -- --baseline <name>
```

### Benchmark over multiple input sizes with throughput
```rust
// Source: https://github.com/bheisler/criterion.rs/blob/master/book/src/user_guide/benchmarking_with_inputs.md
use criterion::{BenchmarkId, Criterion, Throughput};

fn bench_sizes(c: &mut Criterion) {
    let mut group = c.benchmark_group("phase6_mmap_variants");
    for size in [1024usize, 2048, 4096].iter() {
        group.throughput(Throughput::Bytes(*size as u64));
        group.bench_with_input(BenchmarkId::from_parameter(size), size, |b, &size| {
            b.iter(|| vec![0u8; size]);
        });
    }
    group.finish();
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Mmap::map()` on large files | `MmapOptions::map_copy_read_only()` for this phase | Locked by Phase 6 context on 2026-04-06 | Keeps the production API shape but changes the mmap strategy |
| Treat `map_copy()` as the target | Treat `map_copy_read_only()` as canonical | Repo decisions updated by Roadmap/State/Phase 6 context | Planning must align stale docs instead of following older wording |
| Ad hoc benchmark ownership ambiguity | mmap proof explicitly owned by SAFE-05 / Phase 6 | Clarified in Phase 5 proof and updated requirements on 2026-04-06 | Keeps proof in `file_io_benchmarks.rs`, not Phase 5 harness |

**Deprecated/outdated:**
- `map_copy()` as the milestone target: outdated for this phase even though older repo docs still mention it.
- Assuming raw Criterion baselines belong in git: outdated for this repo; committed artifact should be markdown proof only.

## Open Questions

1. **How strong should the public safety wording be after the swap?**
   - What we know: upstream `memmap2` still marks all file-backed map constructors `unsafe` if the underlying file is modified after mapping.
   - What's unclear: whether repo docs should say “safe on Windows” or “safer / snapshot-style mitigation validated on Windows.”
   - Recommendation: keep the implementation locked to `map_copy_read_only()`, but phrase docs conservatively unless empirical validation and code comments can justify stronger wording.

2. **Which older documents must be updated in-phase vs. merely noted as historical?**
   - What we know: `.planning/PROJECT.md` and `.planning/REQUIREMENTS.md` are definitely stale; `FEATURES.md` and `CONCERNS.md` also still reference `map_copy()`.
   - What's unclear: whether all research artifacts are treated as living contracts.
   - Recommendation: planning must at minimum update the living milestone docs named in Phase 6 context and note any remaining historical drift explicitly.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Windows host | Required validation target | ✓ | `win32` host | None |
| `cargo` | Rust tests and Criterion benches | ✓ | 1.94.0 | — |
| `rustc` | Build/test/bench execution | ✓ | 1.94.0 | — |
| `pwsh` | Repo-standard wrapper/docs commands | ✓ | 7.6.0 | — |
| `gnuplot` | Preferred Criterion plots only | ✗ | — | Criterion report generation without `gnuplot` |

**Missing dependencies with no fallback:**
- None.

**Missing dependencies with fallback:**
- `gnuplot` — not installed locally; acceptable because the benchmark proof is markdown-first and the repo Criterion config comments already anticipate fallback behavior.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Rust built-in test harness + `tokio::test`; Criterion 0.6.0 for benchmark proof |
| Config file | `ClassicLib-rs/business-logic/classic-file-io-core/Cargo.toml`, `ClassicLib-rs/criterion.toml` |
| Quick run command | `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml read_file_mmap -- --nocapture` |
| Full suite command | `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml && cargo bench -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --bench file_io_benchmarks -- --test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SAFE-05 | Large-file branch still returns correct content after constructor swap | unit | `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml read_file_mmap_large_file -- --nocapture` | ✅ |
| SAFE-05 | Benchmark harness contains the three-way mmap comparison and compiles | benchmark-smoke | `cargo bench -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --bench file_io_benchmarks -- --test` | ❌ Wave 0 |
| SAFE-05 | Windows throughput proof for `map`, `map_copy`, `map_copy_read_only` is captured as markdown | benchmark-proof | Local save/compare commands in proof artifact | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml read_file_mmap -- --nocapture`
- **Per wave merge:** `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml && cargo bench -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --bench file_io_benchmarks -- --test`
- **Phase gate:** Windows benchmark proof captured and committed as markdown before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] Add a focused Phase 6 benchmark group in `ClassicLib-rs/business-logic/classic-file-io-core/benches/file_io_benchmarks.rs`.
- [ ] Add a committed proof artifact at `.planning/phases/06-mmap-toctou-safety/06-BENCHMARK-PROOF.md` following the Phase 5 format.
- [ ] Consider factoring the mmap constructor choice behind a tiny private helper so the benchmark and any future test can target the three strategies without duplicating decode logic.

## Sources

### Primary (HIGH confidence)
- `/websites/rs_memmap2` - `MmapOptions`, `map`, `map_copy`, `map_copy_read_only`, safety notes
- https://docs.rs/memmap2/latest/memmap2/struct.MmapOptions.html - exact API signatures and safety text
- https://crates.io/api/v1/crates/memmap2/0.9.10 - current published version metadata
- `/bheisler/criterion.rs` - benchmark groups, throughput, baselines
- https://github.com/bheisler/criterion.rs/blob/master/book/src/user_guide/benchmarking_with_inputs.md - `BenchmarkId`/`Throughput` pattern
- https://github.com/bheisler/criterion.rs/blob/master/book/src/user_guide/command_line_options.md - `--save-baseline` / `--baseline`
- https://bheisler.github.io/criterion.rs/book/faq.html - benchmark CLI and `black_box` guidance
- https://learn.microsoft.com/windows/win32/api/memoryapi/nf-memoryapi-mapviewoffile#parameters - `FILE_MAP_COPY` commit-charge behavior on Windows
- Repo sources: `ClassicLib-rs/business-logic/classic-file-io-core/src/core.rs`, `.../benches/file_io_benchmarks.rs`, `docs/api/classic-file-io-core.md`, `.planning/ROADMAP.md`, `.planning/phases/06-mmap-toctou-safety/06-CONTEXT.md`

### Secondary (MEDIUM confidence)
- `.planning/research/SUMMARY.md` - prior repo research rationale for `map_copy_read_only()`
- `.planning/research/PITFALLS.md` - repo-specific Windows pitfall framing and benchmark expectations
- `performance_baselines/README.md` - local-only raw baseline policy and repo proof threshold

### Tertiary (LOW confidence)
- None used for recommendations.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - core APIs and versions verified from docs.rs/crates.io and repo manifests
- Architecture: HIGH - implementation site, benchmark site, and doc-update obligations verified in repo source/docs
- Pitfalls: MEDIUM - Windows commit-charge behavior is verified, but upstream `memmap2` safety wording remains broader than the repo phase goal

**Research date:** 2026-04-06
**Valid until:** 2026-05-06
