---
phase: 08
reviewers:
  - gemini
  - claude
  - codex
reviewed_at: 2026-04-12T15:48:18.3315704-07:00
plans_reviewed:
  - 08-01-PLAN.md
  - 08-02-PLAN.md
  - 08-03-PLAN.md
  - 08-04-PLAN.md
  - 08-05-PLAN.md
  - 08-06-PLAN.md
---

# Cross-AI Plan Review - Phase 08

## Gemini Review

### Summary

Gemini judged the plan set highly disciplined and well sequenced. It called out the wave split as strong, praised the strict adherence to the Phase 8 boundary, and viewed the overall migration as low risk because the work is mostly deterministic path rewiring rather than semantic redesign.

### Strengths

- Wave 1 and Wave 2 are ordered correctly for generator rewires before artifact refresh.
- The plans avoid scope creep and preserve the locked Phase 8 decisions.
- The regression-first approach is strong, especially around rejecting `ClassicLib-rs/...` references.
- The fail-fast legacy-path policy is consistently reflected in the plan set.

### Concerns

- HIGH: Plans 08-03 and 08-04 may under-specify the need to update hardcoded path inventories inside `generate_baseline.py`, such as `RUST_TARGET_CRATES` and `PYTHON_TARGET_MODULES`, rather than only argparse defaults.
- LOW: Plan 08-02 should avoid accidental dependency creep if the TUI smoke flag is implemented with a heavy CLI parsing crate.

### Suggestions

- Explicitly call out internal target-inventory dictionary rewires in Plans 08-03 and 08-04.
- Constrain the TUI smoke flag in 08-02 to `std::env::args()` and forbid a new CLI dependency.
- Extend 08-01 verification to cover a normal `rebuild_node.ps1` alias path in addition to a debug run.

### Risk Assessment

Overall risk: LOW.

## Claude Review

### Summary

Claude assessed the six plans as well structured for a brownfield path-rewrite phase, with correct wave ordering and good adherence to the locked context. Its main warning was that the most load-bearing path changes are in the internal inventory dictionaries of the parity baseline generators, and those edits should be made explicit in the plan text.

### Strengths

- Parallelism across 08-01 through 08-05 is correct, and 08-06 is correctly dependent on all five.
- The plans consistently use a test-first pattern before rewiring each surface.
- The plan set directly addresses the major Phase 8 pitfalls identified in research.
- The plans avoid new packages, wrappers, or parity workflows.
- Legacy-path rejection is handled consistently across wrappers and parity tooling.
- Verification largely uses real contributor-facing entrypoints.

### Concerns

- HIGH: Plans 08-03 and 08-04 do not explicitly name the hardcoded target-inventory dictionaries in `generate_baseline.py` as primary rewire targets.
- MEDIUM: Plan 08-01 does not explicitly guard stale internal Python paths inside `rebuild_rust.ps1`; current verification appears stronger for Node than Python.
- MEDIUM: Plan 08-06 may list baseline files that need validation against what actually exists on disk before execution.
- MEDIUM: Plan 08-05 should explicitly cover synthetic CXX test-tree paths that still assume `ClassicLib-rs/...`.
- LOW: Plan 08-04 should explicitly mention package scripts such as `parity:gate:local:vsdev` that may still have stale depth assumptions.
- LOW: Plan 08-01 should explicitly catch stale legacy-path help text in user-facing messages.

### Suggestions

- Add explicit language to Plans 08-03 and 08-04 covering target-inventory dictionary rebasing.
- Add a `ClassicLib-rs` body-text assertion for `rebuild_rust.ps1` so internal stale paths cannot survive.
- Explicitly require CXX synthetic test trees to move to `cpp-bindings/classic-cpp-bridge/`.
- Validate the 08-06 `files_modified` list against the real baseline directory contents before execution.
- Constrain the TUI smoke flag in 08-02 to a minimal `std::env::args()` implementation.

### Risk Assessment

Overall risk: LOW-MEDIUM.

## Codex Review

### Summary

Codex considered the plan set strong, tightly scoped, and aligned to `INTG-01` and `INTG-02`. Its main concern was proof quality rather than scope: some verification steps are narrower than the preserved entrypoints they claim to prove, and some artifact-refresh plans could become self-validating unless semantic no-drift checks are made explicit.

### Strengths

- The plans stay inside the stated Phase 8 boundary.
- Wave ordering is sound, with rewires first and consolidation second.
- The repo-root-only contract is enforced consistently.
- Native proof uses the correct wrapper entrypoints rather than raw `ctest`.
- The split across wrapper, native/TUI, Python, Node, CXX, and final audit is easy to execute and review.
- The plans correctly separate path-bearing metadata refresh from semantic parity-contract stability.

### Concerns

- HIGH: Plans 08-05 and 08-06 may be self-validating if regenerated artifacts are only checked with the same updated tooling.
- HIGH: Plan 08-04 does not explicitly prove that `bun run build` still works from `node-bindings/classic-node`.
- MEDIUM: Plan 08-03 lacks an explicit automated test for `validate_stubs.py` legacy-path rejection and migration messaging.
- MEDIUM: Plan 08-01 does not explicitly prove the Python rebuild path after rewiring `rebuild_rust.ps1`.
- MEDIUM: Plan 08-06 omits `bun run dts:freshness:check` and does not re-run repo rebuild wrappers in its final gate.
- MEDIUM: Plan 08-02 should prefer behavior-based TUI smoke proof over text-shape auditing alone.
- LOW: Plan 08-01 over-specifies alias mechanics with an exact text pattern instead of a more general single-canonical-path requirement.
- LOW: The phase should acknowledge where GUI proof is expected to run if Qt is unavailable in a local environment.

### Suggestions

- Add explicit semantic no-drift invariants around artifact refresh plans.
- Add a direct `validate_stubs.py` regression test.
- Add `bun run build` to 08-04 verification.
- Add explicit Python wrapper smoke coverage somewhere in Phase 8.
- Expand the 08-06 final gate to include d.ts freshness and at least one repo rebuild-wrapper smoke command.
- Make 08-02 prove exit-before-terminal-setup behavior instead of relying mainly on text contracts.
- Relax 08-01 alias verification from exact text shape to single canonical execution-path proof.

### Risk Assessment

Overall risk: MEDIUM.

## Consensus Summary

All three reviewers considered the Phase 8 plan set strong and appropriately scoped. The common theme across feedback is not that the phase is overplanned, but that a few of the most important path rewires and proof surfaces should be made more explicit before execution. The two strongest overlaps were around under-specified parity-generator path inventories and verification that is slightly narrower than the preserved workflows the phase claims to prove.

### Agreed Strengths

- The wave structure is sound: 08-01 through 08-05 prepare the rewires, and 08-06 is the right consolidation point.
- The plans stay within the Phase 8 boundary and avoid drifting into CI, packaging, or broader redesign.
- The plan set consistently preserves existing entrypoints while enforcing repo-root-only path policy and legacy-path rejection.
- The regression-first approach is a strong fit for this migration.

### Agreed Concerns

- Plans 08-03 and 08-04 should explicitly name internal `generate_baseline.py` target-inventory dictionaries as required rewire points, not only CLI defaults.
- Verification is narrower than the full preserved workflow story in a few places: Python wrapper proof, standard package-local Node build proof, and final-gate coverage of wrapper or freshness flows should be strengthened.
- Plan 08-02 should constrain TUI smoke proof to minimal behavior-based handling and avoid accidental CLI dependency creep.

### Divergent Views

- Codex was most concerned about artifact-refresh plans becoming self-validating and recommended explicit semantic no-drift invariants in 08-05 and 08-06.
- Claude focused more on plan accuracy details such as synthetic CXX test-tree paths and validating the 08-06 file list against actual baseline files on disk.
- Gemini was the most positive overall and rated the phase low risk if the internal parity-generator path dictionaries are made explicit.
