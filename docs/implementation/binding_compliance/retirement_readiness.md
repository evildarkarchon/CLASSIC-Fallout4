# Evidence retirement readiness

Issue #216 retires the remaining registry claims, their production loaders,
claim-only summaries, and the diagnostic migration ledger. The permanent source
inventory and executable conformance engine now own the obligations directly.

The retirement audit on 2026-09-08 accounts for every live parity occurrence:

| Disposition | Occurrences |
| --- | ---: |
| Named source-derived structural or negative evidence | 1,360 |
| Runtime obligation with an executable predicate | 1,479 |
| Runtime obligation without an executable predicate | 0 |
| Total | 2,839 |

These are diagnostic counts, not an activation list or a checked coverage
baseline. A matching predicate alone is not runtime proof. Only the `full`
profile can certify repository-wide conformance after authenticating all
required executions from the current source tree.

## Permanent evidence

- `retained_analyzers.py` names the blocking structural and negative owners.
  Source, bridge, declaration, stub, type, forbidden-export, Vocabulary, and
  ownership checks remain required.
- `conformance/coverage.py` loads the live parity inventories and derives
  runtime facts from trusted predicates applied to executed observations.
  No registry flag or test pointer can grant coverage.
- `conformance/source_declarations.py` corroborates Python declarations with
  live PyO3 source. Constructors remain runtime obligations, including ones in
  separately named source files. Standard exception macros require verified
  provenance and registration; a stub-only phantom class earns no proof.
- `node-package-metadata` validates the exact compile-time Cargo-version
  getter. `cxx-opaque-map-reachability` proves that the existing opaque-map
  accessors have no exposed producer. Neither analyzer grants unrelated
  functions runtime coverage.
- Operation-scoped capabilities and exact binding selectors distinguish public
  wrappers that share a Rust owner. For example, database lookup entries and
  scanlog finding entries execute through their respective Python extensions.
  Unsupported siblings remain visible in the full repository denominator.

The inventory also retains honest Rust-only rows. The nonexistent Python
`PapyrusError` stub and incorrect Node error-type export anchors were removed;
real runtime error translations remain covered by their executable scenarios.
Previously omitted Node scan-run exports and declarations are now represented.

## Execute and verify

The canonical CI entrypoint is
[ci-binding-compliance.yml](../../../.github/workflows/ci-binding-compliance.yml).
It requires the Rust, Node, Python, and CXX producers from the same workflow run
and revision. CXX requires both MSVC and clang-cl; required consumer receipts
remain part of the full denominator. Downloaded artifact directories and their
immutable plans are preserved without rewriting receipt identities.

Run the static diagnostic from the repository root:

```powershell
python tools/binding_compliance/retirement_readiness.py --repo-root . --output tools/binding_compliance/artifacts/retirement_readiness.json --fail-on-unmatched
```

After executing the applicable producers, aggregate their artifact directories:

```powershell
python tools/binding_compliance/check_compliance.py --profile full --receipt-directory tools/binding_compliance/artifacts/current-run --output-dir tools/binding_compliance/artifacts/full
```

The full command executes the retained lower-level gates as well as receipt
validation. Missing instances, skipped or failed scenarios, changed observations,
stale source identities, modified plans, and unresolved parity rows fail the
result. A scoped participant pass cannot claim repository completion. Source
changes require fresh affected producer evidence before aggregation.

See the [binding compliance suite contract](../../api/binding-compliance-suite.md)
and the [project command reference](../../../.agents/skills/classic-project-guide/references/repo-guide.md)
for build prerequisites and producer commands.

## Deliberate evidence boundaries

Negative update scenarios prove rejection before external transport; controlled
service scenarios separately prove successful responses and durable cache
behavior. CXX hash-cache controls prove the empty state accessible through their
public surface. Python's config-cache clear probe proves its callable boundary
and unchanged owned configuration bytes, not another extension DLL's cache
state. Windows platform probes compare against independent read-only native
results without persisting machine-specific paths.

These bounds describe what the observations establish. They are not exemptions
from the live source inventory or substitutes for the full executable gate.
