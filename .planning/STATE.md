# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-04)

**Core value:** Python is the UI, Rust is the engine — every piece of business logic lives in Rust `-core` crates, Python only handles presentation and user interaction.
**Current focus:** v8.3.0 Performance & Polish — Phase 17 in progress (CI Regression Detection)

## Current Position

Phase: 17 of 17 (CI Regression Detection)
Plan: 2 of 3 in current phase
Status: In progress
Last activity: 2026-02-05 — Completed 17-02-PLAN.md (Benchmark Comparison and Threshold Analysis)

Progress: [v1.0: 14/14] [v8.2.0-part2: 14/14] [v8.3.0: 13/14]
[##############################] 98% (41/42 plans)

## Performance Metrics

**v1.0 Velocity:**
- Total plans completed: 14
- Average duration: 12m
- Total execution time: ~2.8 hours

**v8.2.0-part2 Velocity:**
- Total plans completed: 14
- Average duration: ~12m
- Total execution time: ~2.7 hours

**v8.3.0 Velocity:**
- Plans completed: 12
- Phase 12-01: ~45m
- Phase 13-01: ~5m
- Phase 13-02: ~12m
- Phase 13-03: ~5m
- Phase 14-01: ~4m
- Phase 14-02: ~8m
- Phase 14-03: ~4m (gap closure)
- Phase 15-01: ~6m
- Phase 15-02: ~8m
- Phase 16-01: ~25m
- Phase 16-02: ~35m
- Phase 17-01: ~2m
- Phase 17-02: ~4m

**By Phase (v8.2.0-part2):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 06-foundation-settings | 2/2 | ~15m | ~7.5m |
| 07-game-detection | 2/2 | ~27m | ~13.5m |
| 08-report-generation | 2/2 | ~15m | ~7.5m |
| 09-orchestration-migration | 4/4 | ~76m | ~19m |
| 10-parity-validation | 2/2 | ~17m | ~8.5m |
| 11-integration-cleanup | 2/2 | ~54m | ~27m |

## Accumulated Context

### Decisions

All milestone decisions logged in PROJECT.md Key Decisions table.

**Highlighted decisions:**
- Rust-only, hard fail: no Python fallback for any migrated component
- Delete Python orchestrators entirely (not deprecate-first)
- GIL release audit must happen before baselines (research finding)
- Split GIL and Benchmark work into separate phases for cleaner deliverables
- 1ms threshold guideline for GIL release decisions
- YAML operations have architectural limitation - Python<->Rust dict conversion requires GIL
- Quick/thorough benchmark modes via BENCH_MODE env var (quick: 50 samples, thorough: 200 samples)
- Shared benchmark config via #[path] attribute (not crate dependency)
- Real crash logs embedded via include_str! for scanlog benchmarks
- Native frames enabled by default in py-spy for combined Python+Rust stacks
- AtomicU64 with Ordering::Relaxed for cache hit/miss counters (lock-free statistics)
- PyO3 cache_stats() returns dict for simpler Python consumption (not exposing Rust struct)
- serial_test crate for serializing Rust tests that touch global state (BUG-01 fix)
- ResourceLoader.get_data_directory().parent as project root anchor (BUG-02 fix)
- cProfile used instead of py-spy due to Python 3.14 incompatibility (16-01)
- Threading overhead identified as dominant factor (86%) for optimization (16-01)
- Rust FFI overhead confirmed minimal (0.3%) - previous optimizations successful (16-01)
- Python algorithmic improvements (O(n) to O(1)) more impactful than Rust micro-optimizations (16-02)
- mimalloc added as optional feature flag for future testing (16-02)
- Set-backed lists pattern for O(1) membership with list API compatibility (16-02)
- ready_for_review trigger for benchmark CI (reduces noise vs all PR events) (17-01)
- Separate cache restore/save pattern for baseline management (17-01)
- 5% warning / 10% failure thresholds as CI defaults (17-01)
- Windows-compatible yq installation via PowerShell for benchmark CI (17-02)
- Per-benchmark threshold overrides via yq YAML lookup (17-02)
- Label bypass (perf-regression-accepted) for intentional regressions (17-02)

### Pending Todos

None.

### Blockers/Concerns

- py-spy 0.4.1 incompatible with Python 3.14 (limits native frame profiling)

## Session Continuity

Last session: 2026-02-05
Stopped at: Completed 17-02-PLAN.md
Resume file: None
Next action: Execute 17-03-PLAN.md (PR Comment and Failure Enforcement)
