# Auxiliary, performance, and shared owner conformance

Issue #212 adds domain packs behind the existing input-only plan, authenticated
receipt, exact comparison, coverage, and reporting lifecycle. Expectations are
authored independently of Rust execution. The old runtime registries, smoke
suites, and shared registry loaders remain available and blocking alongside the
new CI steps; this change does not retire their evidence.

| Pack | Core owner | Executed domain observations | Semantic adapters |
|---|---|---|---|
| `file-fingerprint` | file-io | SHA-256 vectors, batch success filtering, encoding, missing file, cache counters/reset/clear, unchanged bytes | Rust, Node, Python |
| `performance` | perf | Supplied timing samples, complete summaries, clear and reuse | Rust, CXX, Node, Python |
| `update-decisions` | update | Valid version upgrade/equality/downgrade/prerelease decisions | Rust, CXX, Node, Python |
| `web-operations` | web | URL validation, domain extraction, joining, query parameters, errors, user agents and all ModSite names/base URLs | Rust, CXX, Node, Python |
| `resource-operations` | resource | Type catalog, constructors, enumeration, counts, validation errors, unchanged files | Rust, Node, Python |
| `version-operations` | version | Parsing, optional parsing, comparison, formatting, invalid text | Rust, Node, Python |
| `xse-operations` | xse | F4SE metadata, absent/loader-only/version-DLL detection, unchanged files | Rust, CXX, Node, Python |
| `string-operations` | shared | Interned content and ordered scalar/batch normalization | Rust, Node, Python |
| `registry-operations` | registry | Typed values, absence, overwrite, removal, clearing | Rust, CXX, Node, Python |
| `game-identity` | shared | Canonical ordered game tokens | Rust, CXX, Node, Python |
| `runtime-access` | shared | Initial/repeated availability of the shared runtime | Rust, CXX, Node |
| `settings-load` | settings | Local YAML document counts, batch failures, cache effects and unchanged files | Rust, CXX, Node, Python |

Each applicable CXX pack runs through the approved CLI wrapper on both MSVC and
clang-cl. It traverses native bridge return values and emits its own observations;
it does not serialize a Rust-generated oracle. The resource classification and
version parsing capabilities have no corresponding CXX entry point. Python's
runtime diagnostics belong to the separately inventoried `classic-shared-py`
owner and are not credited as a core runtime operation.

## Determinism and transport limits

Issue #214 extends web metadata and adds configured notification service coverage;
see the [update/web evidence map](update_web_conformance_equivalence.md) for its
controlled listener, cache observations and retained operation boundaries.

All files live beneath disposable invocation-owned directories. No scenario
contacts GitHub, searches the user's registry, discovers an installed game, or
reads mutable user files. File inventory observations include exact bytes and
therefore detect unexpected writes. Registry and metric scenarios clear their
process-global state between cases. No wall-clock duration, pointer identity,
host-dependent worker count, or concurrent event ordering is an expectation.

Performance uses supplied whole-millisecond samples and checks numeric
integrality rather than rounding. CXX's formatted summary is checked against
its public numeric accessors. The scope does not claim elapsed timer behavior.
Update decisions use valid versions because the current CXX boolean API
collapses malformed-version errors to `false`; existing typed-error tests remain
responsible for those errors. XSE absence uses the public optional/sentinel
contract, not an invented typed detection error. Generic CXX settings loaders
expose document counts, so this pack does not claim full YAML value transport.

## Coverage and retained evidence

Coverage starts from canonical Rust capabilities and current parity rows. Legacy
Node aux metadata receives source-backed owner/symbol corrections without new
registry acknowledgements or changed mapping IDs. Operation identities are
preserved for aggregate carriers, so an added function or method cannot borrow
another operation's receipt. Tooling mutation tests exercise missing/changed
observations, replay, and actual appended contract aliases through the public
materialization, receipt-validation, and row-derivation boundaries.

The narrow retained-operation selectors in
`tools/binding_compliance/conformance/families/operation_scope.py` preserve
existing runtime tests for unexecuted language-specific methods. They never
grant receipt coverage or relabel runtime behavior as structural. In particular,
network release methods, alternate XSE constructors, representation/equality
helpers, and the other GameId carriers keep their original evidence. See also
the [shared/registry scope map](shared_registry_conformance_equivalence.md).

Irreducibly structural evidence stays with named permanent analyzers:
`cxx-source-parity`, `node-source-and-declaration-parity`, and
`python-source-and-stub-parity`. Runtime receipts do not replace declaration
freshness, Python stub validation, compile-only TypeScript checks, forbidden
exports, Vocabulary ownership, or the shared-runtime ownership audit.

## Validation commands

Use `python tools/binding_compliance/run_semantic_conformance.py --family <pack>
--participant <rust|node|python>` for a fresh scoped run. Rebuild the managed
Python environment before Python execution. For CXX use
`tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Family
<pack> -Compiler <msvc|clang-cl>`. CI retains separate attempts, receipts, JUnit
and diagnostic uploads on failure. A participant run proves only its own scope.

The full tooling suite is `python -m pytest tools/binding_compliance/tests -q`.
The diagnostic migration ledger is not execution evidence; passing receipts
remain untracked artifacts.
