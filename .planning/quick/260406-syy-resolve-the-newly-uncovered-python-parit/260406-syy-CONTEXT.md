# Quick Task 260406-syy: Resolve the newly uncovered Python parity surface for FcxResetError so the Python parity gate no longer reports uncovered runtime metadata. - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Task Boundary

Resolve the newly uncovered Python parity surface for `FcxResetError` so the Python parity gate no longer reports uncovered runtime metadata.

</domain>

<decisions>
## Implementation Decisions

### Resolution strategy
- Keep `FcxResetError` as a Rust-only Tier-2 deferred surface for Python. Align the Python parity governance/runtime metadata so the surface is classified as deferred instead of newly uncovered. Do not expand the Python binding contract for this quick task.

### the agent's Discretion
- Choose the smallest set of Python parity registry, governance, and generated artifact updates needed to clear the newly uncovered status while matching existing repo policy and prior Phase 3 intent.
- Use repo-standard Python parity validation depth appropriate for the touched files.

</decisions>

<specifics>
## Specific Ideas

- The newly uncovered surface is `binding:rust:FcxResetError` under `scanlog` Tier-2 runtime coverage.
- Existing project state already records the intended policy: "Track `FcxResetError` as deferred Tier-2 parity while runtime-verifying the new Node-only FCX exports."

</specifics>

<canonical_refs>
## Canonical References

- `.planning/STATE.md`
- `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json`
- `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json`
- `docs/api/classic-scanlog-core.md`

</canonical_refs>
