## Context

The repository already has solid contract-based parity gates for maintained binding APIs, but runtime verification breadth is uneven across bindings. The current baselines show zero Tier-1 drift, yet they also show substantial remaining uncovered surface: `docs/implementation/node_api_parity/baseline/parity_diff_report.md` reports 99 total gaps and `docs/implementation/python_api_parity/baseline/parity_diff_report.md` reports 292 total gaps, with the largest concentration in `scanlog`.

Today, Node relies on a broad but hand-curated runtime suite, and Python relies on smoke tests plus tooling checks. Those suites prove important workflows, but they do not yet provide a systematic answer to "which binding-facing APIs are runtime-verified against the Rust core and which are still deferred?"

Constraints:
- Reuse the existing parity manifests, contracts, and local developer commands instead of replacing them.
- Keep Tier-1 release gates strict while allowing intentional Tier-2 deferral with published rationale.
- Avoid flaky coverage checks that depend on network access, mutable machine state, or full app packaging.
- Limit scope to maintained Node and Python bindings; C++ bridge parity can evolve separately.

## Goals / Non-Goals

**Goals:**
- Make binding parity coverage measurable for both Node and Python.
- Require direct runtime verification for all Tier-1 binding surfaces and newly promoted APIs.
- Keep deferred surface area visible, attributable, and reducible in planned waves.
- Extend parity tooling and CI so coverage cannot silently regress when Rust or binding surfaces change.

**Non-Goals:**
- Promoting every existing Tier-2 API to Tier-1 in a single implementation wave.
- Replacing current parity contract formats with a new contract system.
- Adding network-dependent end-to-end tests for external services.
- Defining new requirements for C++ application frontends in this change.

## Decisions

1. **Separate API contract metadata from runtime coverage metadata**
   - Decision: Keep `parity_contract.json` focused on Rust-to-binding API mapping, and add a separate coverage registry/report layer keyed by stable contract or export identifiers.
   - Rationale: API parity and runtime verification are related but different concerns; separating them keeps contract files stable while making test ownership explicit.
   - Alternatives considered:
     - Store runtime test metadata directly in parity contracts: rejected because it couples release-gated API mapping to test implementation churn.
     - Infer coverage by parsing test files only: rejected because it is brittle and hard to audit.

2. **Use table-driven runtime suites keyed by exported surface identifiers**
   - Decision: Expand Node and Python runtime tests through parameterized case tables that reference binding export identifiers or contract IDs, rather than adding one-off tests without traceability.
   - Rationale: Table-driven coverage scales better across large surfaces and gives tooling a deterministic way to verify that each Tier-1 export has runtime evidence.
   - Alternatives considered:
     - Continue hand-curated freeform tests only: rejected because it does not provide coverage accounting.
     - Auto-generate all runtime tests from signatures alone: rejected because many APIs still need curated fixtures and assertions.

3. **Make Tier-1 runtime verification mandatory, and manage Tier-2 through explicit waves**
   - Decision: Every Tier-1 callable export must have direct runtime execution coverage, while non-callable Tier-1 data types must be verified through construction, return values, or field inspection. Remaining Tier-2 surface stays allowed only when published with owner, rationale, and planned revisit metadata.
   - Rationale: This gives strong guarantees for shipped surfaces without forcing an unrealistic all-at-once promotion of hundreds of deferred APIs.
   - Alternatives considered:
     - Keep Tier-1 as contract-only and rely on a few smoke tests: rejected because it leaves runtime drift undetected.
     - Fail on every uncovered Tier-2 API immediately: rejected because current backlog size would block practical rollout.

4. **Extend parity tooling to emit coverage summaries and enforce non-regression**
   - Decision: Node and Python parity tooling should produce human-readable and machine-readable coverage summaries, and CI should fail when Tier-1 runtime mappings disappear, new exports are unclassified, or refreshed artifacts are missing after tracked surface changes.
   - Rationale: Coverage expansion only sticks if contributors can see it and if regressions are mechanically blocked.
   - Alternatives considered:
     - Rely on reviewer judgment and docs updates: rejected because drift will be missed over time.
     - Enforce coverage only in release branches: rejected because fixes would arrive too late.

5. **Prioritize the backlog by owner module and workflow value**
   - Decision: Start coverage expansion with the largest and most user-facing modules (`scanlog`, then `config`), then continue through `version_registry` and `aux`, using the existing parity diff reports as the planning source.
   - Rationale: This captures the most important workflow surface first and matches where the baseline reports show the biggest remaining gaps.
   - Alternatives considered:
     - Alphabetical or random API ordering: rejected because it does not align effort with user impact.

## Risks / Trade-offs

- **[Risk] Coverage metadata becomes stale even while tests still pass** -> **Mitigation:** Generate summaries from test registries plus parity manifests, and fail checks when tracked exports lack refreshed artifacts.
- **[Risk] CI runtime suites grow too slow as coverage expands** -> **Mitigation:** Prefer shared fixtures, parameterized cases, and a split between fast mandatory Tier-1 checks and broader wave-oriented suites where needed.
- **[Risk] Backlog waves encourage indefinite deferral** -> **Mitigation:** Require owner, reason, and revisit metadata for every deferred surface and publish reduction counts per wave.
- **[Risk] Some APIs are difficult to exercise deterministically in local CI** -> **Mitigation:** Allow representative construction/inspection coverage for data types and define stable offline fixtures for callable workflows.

## Migration Plan

1. Refresh Node and Python parity manifests to establish the starting uncovered surface for this effort.
2. Introduce binding-specific runtime coverage registries keyed to existing contract/export identifiers.
3. Convert current smoke/runtime suites to consume those registries and ensure every Tier-1 surface has explicit runtime evidence.
4. Extend parity tooling to emit coverage summaries and validate registry completeness against discovered exports.
5. Wire the new coverage checks into existing local workflows and CI jobs for Node and Python.
6. Reduce remaining Tier-2 backlog in waves, starting with `scanlog` and `config` high-value surfaces.

Rollback strategy:
- Keep the new coverage gate isolated from existing parity contract checks so it can be temporarily downgraded or bypassed in CI without discarding new registries or runtime tests.
- Preserve generated summaries and wave metadata so rollout can resume without rebuilding the inventory from scratch.

## Open Questions

- Should the first implementation wave require full Tier-1 direct runtime coverage in both bindings before enabling a hard CI gate, or should one binding land first with the other gated shortly after?
- Do we want one shared cross-binding coverage report schema for Node and Python, or binding-specific schemas with the same headline fields?
- For APIs that intentionally surface filesystem or environment behavior, what is the minimum fixture standard we want before calling them runtime-verified?
