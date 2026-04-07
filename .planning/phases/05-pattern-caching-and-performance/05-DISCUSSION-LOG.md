# Phase 5: Pattern Caching and Performance - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 05-pattern-caching-and-performance
**Areas discussed:** Important-mod matcher, Shared pattern cache, Benchmark proof, Optimization breadth

---

## Important-mod matcher

### Matching engine

| Option | Description | Selected |
|--------|-------------|----------|
| Aho-Corasick | Best fit for many reusable literal patterns. Gives one compiled automaton per pattern set instead of per-entry regex builds. | ✓ |
| Literal contains | Smallest code change. Keeps behavior easy to reason about, but does repeated per-entry scans and may leave less headroom on large lists. | |
| Adaptive hybrid | Use simple contains for small lists and Aho-Corasick for larger ones. Best-case performance flexibility, but more branching and more test surface. | |

**User's choice:** Aho-Corasick

### Overlap semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Leftmost-longest | Safest default for overlapping literals because the most specific/longest hit wins when matches start at the same place. | ✓ |
| Leftmost-first | Priority comes from input order. Useful if YAML order should explicitly decide ties. | |
| You decide | Lock Aho-Corasick, but let planner/research choose the exact match-kind after parity investigation. | |

**User's choice:** Leftmost-longest

### Search surface

| Option | Description | Selected |
|--------|-------------|----------|
| One combined text | Keep today's behavior: lowercase plugin names and XSE module names, join them, and search one combined haystack. Lowest parity risk versus the current implementation. | ✓ |
| Separate plugin/module scans | Search plugin names and XSE modules separately, then merge hits. Cleaner internally, but it changes how matching is structured. | |
| Planner decides | Lock Aho-Corasick usage, but let implementation choose the exact haystack layout. | |

**User's choice:** One combined text

### Rollout safety

| Option | Description | Selected |
|--------|-------------|----------|
| Fixture parity first | Require explicit parity coverage against current fixtures and existing tests before removing the old path. | ✓ |
| Unit tests are enough | Once unit tests pass, remove the old path without extra parity-focused coverage. | |
| Keep a temporary fallback | Ship Aho-Corasick but keep the old regex path around briefly as a backup. | |

**User's choice:** Fixture parity first
**Notes:** This follows the blocker already recorded in `.planning/STATE.md`.

---

## Shared pattern cache

### Sharing depth

| Option | Description | Selected |
|--------|-------------|----------|
| Shared helper + focused caches | Share the normalization/compile helper where shapes align, but keep cache keys scoped to each hotspot's data shape. | ✓ |
| Separate caches per function | Smallest patch in each function, but leaves repeated compilation logic scattered across the file. | |
| One universal cache | Normalize all three hot paths into one generic cache abstraction. Most consolidated, but highest refactor cost. | |

**User's choice:** Shared helper + focused caches

### Cache lifetime

| Option | Description | Selected |
|--------|-------------|----------|
| Process-wide bounded caches | Best fit for standalone hot functions and consistent with Phase 4's bounded-cache direction. | ✓ |
| Per-run / per-parser caches | Shorter-lived state, but weaker reuse for repeated standalone calls across a long-running process. | |
| Planner decides | Lock caching as required, but leave the exact ownership model open. | |

**User's choice:** Process-wide bounded caches

### Invalidation model

| Option | Description | Selected |
|--------|-------------|----------|
| Hash-keyed + eviction only | Use normalized-content hashes as keys and let bounded eviction retire old entries. No explicit reset API unless testing proves it is needed. | ✓ |
| Add manual clear hook | Expose explicit cache-reset helpers for these pattern caches. | |
| Time-based expiry | Add TTL-style cache aging on top of bounded storage. | |

**User's choice:** Hash-keyed + eviction only

### Cache backend

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse quick_cache pattern | Matches the established repo pattern from Phase 4: bounded global cache with `LazyLock` initialization. | ✓ |
| Custom map + lock | Hand-roll the cache ownership and locking for these pattern sets. | |
| Use lru crate | Use the existing `lru` dependency instead of `quick_cache` for these new caches. | |

**User's choice:** Reuse quick_cache pattern

---

## Benchmark proof

### Benchmark home

| Option | Description | Selected |
|--------|-------------|----------|
| Extend scanlog benches | Reuse the existing `classic-scanlog-core/benches/scanlog_benchmarks.rs` setup and measure the bridge hotspot via parser-construction/header-parse equivalents. | ✓ |
| Add bridge Criterion benches | Measure `classic-cpp-bridge` more literally, but this adds new Criterion setup to a crate that does not use it today. | |
| Both | Use the existing core benches and also add bridge-local benchmark coverage for the parser reuse change. | |

**User's choice:** Extend scanlog benches

### Benchmark inputs

| Option | Description | Selected |
|--------|-------------|----------|
| Real + synthetic | Use existing real crash-log fixtures for realism, plus generated mod/plugin sets to isolate the regex and Aho-Corasick hot paths at different sizes. | ✓ |
| Real fixtures only | Stay entirely on sample crash logs and existing fixture data. | |
| Synthetic only | Use generated plugin/mod datasets for tighter control of hotspot sizes and comparisons. | |

**User's choice:** Real + synthetic

### Baseline handling

| Option | Description | Selected |
|--------|-------------|----------|
| Local Criterion baselines | Use Criterion baseline save/compare locally and keep raw baseline captures out of git, matching current repo policy. | ✓ |
| Commit a shareable summary | Generate a small markdown or JSON summary artifact and commit it with the phase. | |
| No saved baseline | Just run benchmarks and compare the numbers manually in the session output. | |

**User's choice:** Local Criterion baselines

### Success bar

| Option | Description | Selected |
|--------|-------------|----------|
| Each hotspot improves | Require measurable improvement for the locked hotspots: important matcher, shared regex cache paths, and parser-allocation path. Flat results need explanation before they pass. | ✓ |
| Overall phase improves | Accept a mixed result as long as the overall benchmark story trends faster. | |
| Report only | Capture numbers, but do not treat any threshold or per-hotspot improvement as a pass/fail expectation. | |

**User's choice:** Each hotspot improves

---

## Optimization breadth

### Refactor style

| Option | Description | Selected |
|--------|-------------|----------|
| Shared helpers where justified | Prefer the smallest change set, but extract internal helpers when it directly removes duplicate hot-path setup across the touched functions. | |
| Strictly localized edits | Keep every hotspot change inline, even if some setup logic stays duplicated. | |
| Broader cleanup pass | Use Phase 5 to do a wider internal cleanup around these hotspots while the file is open. | ✓ |

**User's choice:** Broader cleanup pass

### Cleanup boundary

| Option | Description | Selected |
|--------|-------------|----------|
| All touched-file regex setup in scope | Include the roadmap-required hotspots plus adjacent regex/static-init cleanup in the same touched files, as long as it stays inside `mod_detector` and the C++ bridge paths already named for Phase 5. | ✓ |
| Only roadmap-required call sites | Broader style, but still limit edits to the exact functions named in the roadmap. | |
| Also expand to nearby bindings | Pull adjacent binding-side parser/pattern hotspots into the same phase if they are discovered while implementing. | |

**User's choice:** All touched-file regex setup in scope

### Supporting cleanup rule

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, if it supports the locked hotspot work | Keep supporting structural cleanup when it directly enables the Phase 5 performance changes or reduces duplicate pattern setup in the touched files. | ✓ |
| Only if benchmark-visible | Defer any cleanup that is not independently measurable in benchmarks. | |
| Defer to Phase 7 | Leave non-benchmark-visible cleanup for the later consistency sweep. | |

**User's choice:** Yes, if it supports the locked hotspot work

### Out-of-scope hotspots

| Option | Description | Selected |
|--------|-------------|----------|
| Note and defer | Capture them as deferred ideas or backlog notes unless they are required to complete the locked Phase 5 goals. | ✓ |
| Pause and ask | Stop and revisit scope before continuing if adjacent hotspots look worthwhile. | |
| Fold them in | Treat similar nearby hotspots as part of this phase automatically. | |

**User's choice:** Note and defer

---

## the agent's Discretion

- Exact cache capacities and helper names.
- Exact benchmark group names and synthetic fixture sizes.
- Exact internal factoring for touched-file cleanup inside `mod_detector` and `scanner.rs`.

## Deferred Ideas

- Node synchronous parser utilities in `ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs` also instantiate `LogParser::new(None)` per call and should be considered later, not folded into Phase 5 automatically.
