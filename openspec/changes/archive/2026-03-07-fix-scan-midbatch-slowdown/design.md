## Context

The current GUI batch scan path reports progress when a log completes, not while a log is actively being processed. In practice, this makes a batch appear to slow down in the middle whenever the in-flight worker set is dominated by a few heavier logs, then appear to speed up again once those logs clear and shorter queued logs complete in rapid succession.

At the same time, the Rust scan pipeline appears to rebuild equivalent intermediate views of the same crash log for multiple analyzers. `OrchestratorCore::process_log()` performs several analysis phases over overlapping callstack and plugin data, and some analyzers convert or rescan data in ways that amplify the cost of already-heavy logs. This makes the user-visible progress artifact worse because the longest logs become even longer.

The change spans Rust scanlog orchestration, the C++ bridge batch callback surface, and GUI progress presentation. The design must preserve current scan correctness, report content, and fail-soft behavior while making progress reporting more truthful and reducing repeated per-log work. The GUI status text should remain simple and log-focused rather than exposing detailed internal lifecycle categories.

## Goals / Non-Goals

**Goals:**
- Make GUI batch progress reflect active work instead of only completed logs.
- Expose enough coarse-grained internal batch state to drive smoother, more truthful progress during long scans.
- Reduce repeated crash-data materialization and redundant analyzer passes within `process_log()`.
- Preserve existing scan outputs, report ordering, and error-handling semantics.
- Add lightweight instrumentation points that make future regressions diagnosable without requiring ad hoc profiling.

**Non-Goals:**
- Redesigning the entire scan pipeline or changing analyzer feature scope.
- Replacing the shared Tokio runtime, batch scheduling model, or database architecture.
- Changing user-facing report text or altering how successful scans are written to disk.
- Expanding the status bar into a detailed operational dashboard of internal batch states.
- Introducing fine-grained per-line or per-record progress that would materially increase hot-path overhead.

## Decisions

1. **Adopt coarse phase-aware progress instead of completion-only progress**
   - The bridge batch callback will expose progress events for major lifecycle transitions such as queued, started, phase changes, and completed, rather than only completed results.
   - The GUI will derive user-visible progress from a weighted model of per-log state so long-running logs continue to advance the batch even before completion.
   - The richer state model remains primarily internal; the status bar keeps its current simple, log-focused presentation.
   - Rationale: this directly addresses the misleading mid-batch stall without requiring expensive fine-grained instrumentation.
   - Alternatives considered:
     - Keep completion-only progress and only improve status text: rejected because the percent bar would remain misleading.
     - Emit extremely granular progress from inner analyzers: rejected because it increases coupling and risks measurable overhead in the hot path.

2. **Represent batch work using stable coarse scan phases**
   - The Rust/C++ boundary will treat per-log progress as a small fixed set of phases such as read/setup, parse, analyze, and finalize.
   - Phase reporting will be monotonic and best-effort; failures still emit terminal events with the last known phase.
   - Rationale: a fixed phase model is cheap to compute, stable enough for tests, and useful for internal progress weighting without forcing detailed UX changes.
   - Alternatives considered:
     - Expose analyzer-specific internal states directly: rejected because it leaks implementation details into the UI contract and becomes brittle during refactors.

3. **Create a shared per-log analysis view inside the orchestrator**
   - `process_log()` will conceptually prepare a reusable per-log context once, holding the derived views needed across analyzers: parsed sections, normalized callstack data, joined/combined crash data where necessary, and plugin-derived structures.
   - Downstream analyzer calls should consume references to that shared context instead of independently rebuilding equivalent `Vec<String>`, lowercase variants, or joined strings.
   - Rationale: this reduces repeated allocation and repeated scans on the heaviest logs while keeping analyzer behavior intact.
   - Alternatives considered:
     - Leave analyzers independent and only micro-optimize individual functions: rejected because the largest waste appears at the orchestration boundary where shared derived data is recreated.
     - Fully merge analyzers into one monolithic pass: rejected because it would increase change risk and make behavioral parity harder to preserve.

4. **Target the worst analyzer hot spots first without changing semantics**
   - The first efficiency-focused work will concentrate on paths that scale poorly with large logs, especially plugin suspect matching and repeated whole-callstack string processing.
   - Any algorithmic simplification must preserve current matching behavior, case-handling, report ordering, and fail-soft semantics.
   - Rationale: these paths are the best candidates for real throughput improvement beyond the progress-reporting illusion.
   - Alternatives considered:
     - Focus only on DB paths: rejected because earlier DB work did not materially change the observed symptom and the current evidence points to non-DB hot spots as well.

5. **Add structured performance instrumentation at orchestration boundaries**
   - Instrumentation will capture per-log phase timings and selected batch-level counters around orchestrator phases and bridge progress events.
   - Instrumentation must be lightweight, optional or low-noise in normal operation, and aligned with existing logging/diagnostic patterns.
   - Rationale: this change is performance-motivated; the design should leave behind durable observability rather than one-off debugging code.
   - Alternatives considered:
     - Rely only on external profilers: rejected because the user-visible issue combines perception and throughput, and internal phase timing is the fastest way to distinguish them.

## Risks / Trade-offs

- **[Risk] Weighted phase progress may feel inaccurate for unusual logs** -> **Mitigation:** keep phase weights coarse, monotonic, and easy to tune; validate against mixed-size log batches rather than pretending to provide exact work percentages.
- **[Risk] Internal lifecycle richness leaks into noisy UI text** -> **Mitigation:** constrain user-visible presentation to the existing simple status style and use richer state only for progress computation and diagnostics.
- **[Risk] New progress events may increase bridge/UI churn** -> **Mitigation:** limit updates to major phase transitions and terminal states rather than emitting high-frequency callbacks.
- **[Risk] Shared per-log context could increase memory residency for very large logs** -> **Mitigation:** reuse owned structures already created by the pipeline and avoid duplicating large buffers when building shared views.
- **[Risk] Analyzer refactors could accidentally change report behavior** -> **Mitigation:** preserve analyzer contracts, add parity-focused tests, and compare output ordering/content on representative heavy logs.
- **[Risk] Instrumentation itself becomes a hot-path tax** -> **Mitigation:** keep measurements at coarse boundaries, avoid per-line logging, and use lightweight timing/counter collection.

## Migration Plan

1. Define the batch progress contract and bridge event model for coarse per-log phases.
2. Update GUI progress handling to consume the richer event model while preserving the existing simple status-bar messaging style.
3. Introduce a shared per-log analysis context in the orchestrator and route existing analyzer calls through reused derived data.
4. Simplify the highest-cost analyzer paths while verifying behavioral parity on representative logs.
5. Add timing/instrumentation hooks and run mixed-batch validation to confirm both improved progress behavior and reduced heavy-log cost.

Rollback strategy:
- The progress model and orchestrator reuse changes can be reverted independently if either introduces regressions.
- If the weighted progress UI proves confusing, the richer events can still be retained for diagnostics while the presentation layer is adjusted.

## Open Questions

- Should the progress contract be shared with the CLI as well, or should this change keep CLI presentation untouched and focus on the GUI path first?
- Do we want the phase model to be exposed as explicit enum-like states across the bridge, or as numeric milestones plus status text?
- Which heavy-log fixture set should become the reference workload for validating both progress smoothness and orchestrator throughput?
