# Fixture-backed evidence retirement

Issue #211 retires redundant positive metadata after the blocking migrations in
#205–210. The family packs, authored expectations, canonical owner goldens,
source parity contracts, declarations, stubs, type negatives, forbidden exports,
ownership audits, and focused diagnostics remain authoritative.

## Retirement boundary

The Node and Python registries retain explicit contract IDs for the unmigrated
part of each mixed selector. Migrated rows lose selector counts/hashes and their
copied test pointers, fixture references, and runtime-verification claims.
Unrelated owners keep their existing selectors. The shared registry and fixture
loaders remain because unmigrated suites still consume them.

This narrows 14 mixed selectors, removes 154 migrated identifier claims, and
deletes four now-empty registry entries (Named Record and Plugin Evidence in
each binding). Their focused test files remain independently collected. The
diagnostic ledger consequently contains 63 registry entries and 3,273 total
obligations; these counts describe inventory, not execution coverage.

The metadata report now also delegates the five focused semantic analyzers,
FormID lookup, Autoscan Report, and Vocabulary rows to their existing conformance
families. An old or optimistic registry cannot restore execution credit to those
rows. `receipt_required` records an obligation; it never means a test passed.
Erased Node declarations and Rust-only source mappings remain structural evidence.
Actual execution coverage is derived by the conformance report from authenticated
receipts. The residual registry totals are explicitly labeled legacy claims.

| Retired duplicate positive assertions | Blocking replacement |
| --- | --- |
| Node Tier-1 normalize/join shape assertions | `path-normalization`: `existing-path` and `missing-cleaned-path` compare actual normalized and joined paths |
| Node Tier-1 Info/All message smoke | `message-operations`: `info` uses the same `Tier1 message [ok]` content and compares its exact public fields and formatter output |
| Node metadata assertion that the registry claims `loadInstalledYamlData` | `installed-yaml-data` executes the public loader and compares snapshot/recovery/error observations |

Identifier-only retirement also removes 22 Python Installed YAML outcome,
snapshot, and recovery metadata getter claims and 58 Python semantic
result/enum getter claims. Their values are explicitly projected by the
Installed YAML and semantic receipt runners. Three Node Installed YAML
request/outcome/discriminator DTO claims are removed after their complete
transport projections execute. Constructor, opaque-handle, rule-field,
immutability, reset-action, and internal-error claims remain when they represent
additional guarantees. Remaining fields are selected individually, never by
deleting every member of a class.

FormID Finding Analyzer remains separate from FormID lookup and retains its
registry claims and focused tests. Rule construction, frozen carriers,
concurrency, cache/tuning behavior, Version Registry enumeration/compatibility,
binary/streaming I/O, message mutation, and reset/internal-error diagnostics are
not replaced by these deletions. The frozen operation dispositions in
`tools/binding_compliance/conformance/families/operation_scope.py` remain unchanged.
Node-runtime execution probes also remain because Bun conformance cannot replace
the separate Node runtime.

## Evidence before deletion

All 18 affected packs were already blocking before this change. The workflow
policy requires Rust, Node, Python, and both MSVC and clang-cl CXX instances;
path normalization and message operations have no applicable CXX export.
The retained equivalence maps document the original dual runs. Local historical
artifacts contain 86 passing real receipts across all applicable instances.
Those historical revisions are not represented as current execution evidence.

Before retirement, 260 focused tooling tests passed (two deliberately
inapplicable CXX combinations skipped), including missing/stale/malformed
receipt, skipped scenario, changed observation, new operation, and weakened CI
topology rejection. The removed Node positives passed alongside their fresh
replacement receipts before deletion.

Fresh receipt artifacts for this change live under the ignored
`tools/binding_compliance/artifacts/issue211-before-{rust,node,python,cxx}/` roots.
Each report retains its exact invocation and source identity. These local runs
do not claim GitHub Actions execution for an unpublished commit.

All 86 fresh required executions passed: 18 each for Rust, Node, and rebuilt
Python, plus 16 each for CXX MSVC and clang-cl. Native runs use the approved
wrapper with authenticated attempt and JUnit evidence. A local CMake cache
generator mismatch was resolved by selecting the existing Ninja generator in
the process environment; no build cache or source was deleted.

Final validation passed 553 compliance tooling tests (two expected inapplicable
CXX combinations skipped), 59 Node parity tooling tests, 41 Python parity
tooling tests, and 43 CXX parity tooling tests. The rebuilt Python suite passed
529 tests; Bun passed 1,034 and Node passed 17. All three parity gates,
declaration freshness, TypeScript contracts, and Python stub validation (zero
warnings) passed. Standards and specification reviews found no remaining
findings. Graphify was refreshed; its existing parser limitations still omit
Cargo.toml and partially extract two unchanged C++ headers.
