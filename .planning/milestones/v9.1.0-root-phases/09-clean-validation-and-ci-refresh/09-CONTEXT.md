# Phase 9: Clean Validation and CI Refresh - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Clean-state verification and CI must prove the repo-root workspace works without stale caches, stale outputs, or legacy `ClassicLib-rs` artifacts. This phase is about fresh proof, workflow refresh, and CI-owned path-bearing artifacts, not the broader docs/guidance cleanup that remains in Phase 10.

</domain>

<decisions>
## Implementation Decisions

### Clean-State Proof
- **D-01:** Phase 9 uses a targeted clean-state reset, not a minimal rerun and not a full repository or machine scrub.
- **D-02:** The targeted reset must quarantine or remove the highest-risk generated outputs before proof: legacy `ClassicLib-rs/target`, repo-root `target`, binding `.venv`, Node build outputs, and binding/parity working artifacts touched by the validated flows.
- **D-03:** Phase 9 proof must include at least one deliberate fresh-state execution path, not only incremental reruns on top of existing outputs.

### CI Closure Surface
- **D-04:** Phase 9 closure must refresh and validate all active PR CI workflows: `.github/workflows/ci-rust.yml`, `.github/workflows/ci-python-bindings.yml`, `.github/workflows/ci-typescript.yml`, and `.github/workflows/ci-cpp.yml`.
- **D-05:** `.github/workflows/benchmarks.yml` is also part of the required Phase 9 closure surface.
- **D-06:** Phase 9 must include one required native package-sensitive proof surface in addition to the CI workflows.
- **D-07:** The required native package-sensitive proof is the GUI package flow via `classic-gui/build_gui.ps1`.

### Artifact Refresh
- **D-08:** Phase 9 regenerates only CI-owned, path-bearing artifacts that are directly used by the required CI and package proof surfaces.
- **D-09:** Phase 9 should avoid unrelated artifact churn; path-bearing outputs outside the required proof surface stay out unless the proof shows they are stale.

### Legacy Residue Policy
- **D-10:** Any new generated output under `ClassicLib-rs/` is a Phase 9 failure.
- **D-11:** This failure rule covers recreated `target`, `.venv`, parity-artifact directories, build outputs, packaging outputs, and similar generated residue under the legacy tree.
- **D-12:** Historical docs or planning references to `ClassicLib-rs` are explicitly deferred to Phase 10 unless they break an active Phase 9 proof surface.

### the agent's Discretion
- Exact targeted-clean implementation mechanics, as long as the required high-risk outputs are quarantined or removed before proof.
- Exact mapping from required proof surfaces to the CI-owned artifacts that must be regenerated.
- Exact orchestration between planning audits, workflow updates, and live package-proof execution.

</decisions>

<specifics>
## Specific Ideas

- "Targeted clean" means stronger than the Phase 6 legacy-target quarantine, but it should stop short of a full machine scrub.
- Benchmark CI is part of the closure story for this phase, not a later optional follow-up.
- The GUI package flow is the required native package-sensitive proof because it is the heavier path surface.
- Historical `ClassicLib-rs` references in docs and planning are not Phase 9 work unless they interfere with live validation.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope And Acceptance Criteria
- `.planning/ROADMAP.md` - Phase 9 goal, dependency chain, and success criteria for clean-state validation and CI refresh.
- `.planning/REQUIREMENTS.md` - `INTG-03` and `INTG-04`, plus milestone out-of-scope rules that forbid redesign work or permanent dual-layout support.
- `.planning/PROJECT.md` - milestone goal, active requirements, and relocation-only framing for `v9.1.0-root`.
- `.planning/STATE.md` - current milestone position and the carry-forward sequencing into Phase 9.

### Prior Locked Decisions
- `.planning/phases/06-repo-root-workspace-cutover/06-CONTEXT.md` - repo-root Cargo canon and the original clean-proof expectations from Phase 6.
- `.planning/phases/07-crate-relocation-and-path-rewire/07-CONTEXT.md` - preserved-layer layout, minimal path-rewrite policy, and the non-authoritative legacy-tree boundary from Phase 7.
- `.planning/phases/08-wrapper-and-parity-rewire/08-CONTEXT.md` - root-only wrapper and parity policy plus fail-fast legacy-path behavior that Phase 9 must preserve.
- `.planning/phases/08-wrapper-and-parity-rewire/08-VALIDATION.md` - the existing wrapper/parity validation contract that Phase 9 should extend rather than replace.

### Research And Codebase Maps
- `.planning/research/SUMMARY.md` - recommended clean-validation, CI-refresh, and artifact-regeneration strategy after the path rewires.
- `.planning/research/PITFALLS.md` - false-green cache and artifact shadowing risks, benchmark gotchas, and legacy-residue failure modes.
- `.planning/research/ARCHITECTURE.md` - expected repo-root validation flow, CI/cache integration points, and high-value proof surfaces.
- `.planning/research/STACK.md` - workflow-specific CI, cache, and benchmark path assumptions that Phase 9 must refresh.
- `.planning/codebase/TESTING.md` - available validation surfaces and repo-level test entrypoints reusable in Phase 9.
- `.planning/codebase/STACK.md` - current CI, benchmark, and package-manager stack assumptions relevant to workflow refresh.
- `.planning/codebase/STRUCTURE.md` - current repo layout and path-sensitive directories after the workspace move.
- `.planning/codebase/INTEGRATIONS.md` - GitHub Actions and artifact-handling context for the repo's external automation surface.
- `AGENTS.md` - repo workflow rules and native test invocation constraints that still apply during Phase 9.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/planning/phase06_clean_run.ps1`: prior clean-run harness that already quarantines legacy `ClassicLib-rs/target` and runs repo-root Cargo proof steps.
- `tests/planning/test_phase08_validation.py`: established `unittest` plus subprocess-smoke pattern for repo-root wrapper, parity, and path validation.
- `tests/powershell/rebuild_rust.general_target.test.ps1`, `tests/powershell/rebuild_node.wrapper_contract.test.ps1`, and `tests/powershell/cpp_build_scripts.test.ps1`: existing path-contract tripwires that can stay in the Phase 9 proof story.
- `.github/workflows/ci-rust.yml`, `ci-python-bindings.yml`, `ci-typescript.yml`, `ci-cpp.yml`, and `benchmarks.yml`: live workflow surfaces that already encode cache, working-directory, and artifact-upload assumptions.

### Established Patterns
- Planning validation is file-backed and executable: committed audits plus subprocess proof, not prose-only checklists.
- Repo-root paths are canonical after Phase 8; legacy `ClassicLib-rs/...` runtime and workflow paths are explicit regressions.
- Phase 8 already refreshed parity and d.ts path-bearing artifacts; Phase 9 should build on those surfaces instead of inventing new entrypoints.
- Cache paths, cache keys, and artifact upload locations need to move together; partial rewires are treated as false-green risk.

### Integration Points
- `.github/workflows/ci-rust.yml`, `.github/workflows/ci-python-bindings.yml`, `.github/workflows/ci-typescript.yml`, `.github/workflows/ci-cpp.yml`, and `.github/workflows/benchmarks.yml`.
- `classic-gui/build_gui.ps1` for the required package-sensitive proof surface.
- `validate_stubs.py`, `tools/python_api_parity/`, `tools/node_api_parity/`, `tools/cxx_api_parity/`, and `node-bindings/classic-node/package.json` for CI-owned artifact regeneration and root-path proof.
- `tests/planning/phase06_clean_run.ps1` and `tests/planning/test_phase08_validation.py` for the executable audit harness.

</code_context>

<deferred>
## Deferred Ideas

None - discussion stayed within Phase 9 scope.

</deferred>

---

*Phase: 09-clean-validation-and-ci-refresh*
*Context gathered: 2026-04-12*
