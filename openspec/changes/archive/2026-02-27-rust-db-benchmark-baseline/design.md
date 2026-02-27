## Context

The Rust database path in CLASSIC already has several performance-oriented implementations (`sqlx` async pool, batch lookups, cache stats), but optimization work is currently measured ad hoc. This makes it hard to validate net wins, compare competing approaches, or detect regressions when multiple DB-focused changes land over time.

The baseline must cover both:
- Core database operations in `classic-database-core`
- Scan-time FormID resolution behavior in `classic-scanlog-core`

## Goals / Non-Goals

**Goals:**
- Define a repeatable benchmark matrix for Rust DB-critical paths.
- Produce stable baseline artifacts that future optimization changes can compare against.
- Standardize scenario names, dataset classes, and reported metrics for apples-to-apples comparisons.
- Keep benchmark setup practical for local developer execution.

**Non-Goals:**
- Changing production lookup/query behavior in this change.
- Exhaustive system-wide performance profiling beyond DB/FormID hot paths.
- Introducing hard CI blocking by default for all benchmark drift.

## Decisions

1. **Rust-native benchmarking is the source of truth for this baseline**
   - Use Rust benchmark harnesses for Rust path measurement (crate-local benchmarks and fixtures).
   - Keep existing Python benchmark coverage as supplementary context, not primary pass/fail source.
   - Rationale: This change is Rust-focused and should remove cross-language measurement noise.

2. **Scenario matrix is explicit and versioned**
   - Define canonical scenarios: single lookup (cold/warm), batch lookup (small/medium/large), multi-db fallback behavior, scan-path FormID resolution.
   - Fix dataset size classes and fixture generation strategy (seeded generation where synthetic data is used).
   - Rationale: Stable scenario naming and input classes are required for meaningful historical deltas.

3. **Baseline artifacts are persisted as comparable snapshots**
   - Store benchmark outputs in a documented machine-readable format with metadata (commit, OS, runtime/toolchain summary, scenario metrics).
   - Rationale: Follow-up changes need a concrete reference, not terminal-only output.

4. **Regression comparison workflow is report-first**
   - Add a documented comparison step that computes per-scenario absolute/relative delta and flags threshold breaches.
   - Keep gating optional/toggleable for now.
   - Rationale: Enables disciplined optimization without forcing hard CI policy in the first baseline change.

## Risks / Trade-offs

- **[Risk] Benchmark variance across machines obscures signal** → **Mitigation:** define warmup/measurement settings and emphasize same-host comparisons for acceptance decisions.
- **[Risk] Overly broad scenario set increases maintenance burden** → **Mitigation:** limit baseline to DB/FormID hot paths and defer peripheral scenarios.
- **[Risk] Baseline becomes stale after major architecture shifts** → **Mitigation:** document baseline refresh workflow with explicit versioning and changelog notes.
- **[Risk] Optional gating may miss regressions if ignored** → **Mitigation:** require comparison report in follow-up optimization changes even when hard-fail is disabled.

## Migration Plan

1. Add benchmark fixtures/scenarios and baseline runner.
2. Run and capture initial baseline snapshot.
3. Publish run instructions and comparison workflow.
4. Require subsequent DB optimization changes to include baseline delta reports.

## Open Questions

- Should baseline artifacts live in-repo or be generated/referenced externally for long-term history?
- What default regression threshold should be used for warning vs fail classifications?
