# Config, file, path, and message conformance equivalence

Issue #209 promotes five operation packs to blocking receipt enforcement. Each
pack invokes existing public APIs and compares independently authored domain
observations. Shared path normalization has its own pack because its Rust owner
is different from game-path validation. No production API is added.

| Pack | Rust owner | Required bindings | Executed facts |
| --- | --- | --- | --- |
| `config-operations` | `classic-config-core` | Rust, CXX (MSVC and clang-cl), Node, Python | Explicit Main/Game/Ignore loading; stable version, XSE, Crashgen, game version, ordered ignore values; parse and missing-input errors with role/path; unchanged input bytes |
| `file-operations` | `classic-file-io-core` | Rust, CXX (both compilers), Node, Python | UTF-8 and empty reads; read aliases; create and overwrite; missing read and missing-parent write failures; exact before/after file contents and forbidden effects |
| `path-operations` | `classic-path-core` | Rust, CXX (both compilers), Node, Python | Existence predicate and required-file validation; successful empty requirements; missing paths, wrong kind, missing required files; root-relative domain errors |
| `path-normalization` | `classic-shared-core` | Rust, Node, Python | Join and normalize; ordered batch existence hits and successful misses; temporary-root and Windows separator normalization |
| `message-operations` | `classic-message-core` | Rust, Node, Python | All seven message severities, routing targets, null/empty/nonempty details, Unicode and multiline content, exact public formatter output |

CXX has no shared-path normalization or message construction/formatting export.
Its logging-only message bridge is not an observable substitute. The permanent
source mappings determine this applicability; no policy exception is added.
No maintained frontend seam is changed, so no consumer obligations are invented.

## Existing facts and fixture ownership

The config inputs preserve the deterministic Tier-1 Main/Game/Ignore facts in
`node-bindings/classic-node/__test__/fixtures/tier1_parity.fixtures.ts` and
`python-bindings/tests/fixtures/tier1_parity_fixtures.py`. The explicit strict
loader requires ordered `Mods_CORE` sequences, so the new fixture uses that
current contract instead of the historical Python fixture's mapping carrier.
The old fixture remains available to its original tests.

File, path, and message packs exercise the same public operation families as the
retained Tier-1 auxiliary and infrastructure smoke tests. Their input fixtures
are under `tests/fixtures/file_operations`, `path_operations_conformance`,
`path_normalization_conformance`, and `message_operations_conformance`.
Expected observations live only in `tests/conformance/packs/*/v1.json`.
Adapters receive input-only run plans and never read those expected values.

Every filesystem scenario owns a disposable temporary directory. No registry,
installed game, network service, or user document is consulted. File inventories
compare exact UTF-8 text without newline conversion. Path observations remove
only the owned temporary root, extended Windows path prefix where applicable,
and native separators; array ordering remains significant. Message content is
never normalized.

## Blocking execution and retained evidence

Use `python tools/binding_compliance/run_semantic_conformance.py --family <pack>
--participant <rust|node|python>` after the participant build. Native CXX uses
`tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Family
<pack> -Compiler <msvc|clang-cl>`, which runs only the approved CLI wrapper and
requires both a normalized receipt and associated JUnit/attempt evidence.

CI runs each applicable pack after the retained runtime suites at the same
checkout, preserves failures, and uploads each family's diagnostics. The CLI
job reserves 315 minutes for its retained suite and bounded native launches.
Missing, skipped, stale, malformed, changed, or incomplete receipts fail the
applicable scope. A passing local receipt proves only its recorded source
identity and participant, never repository-wide success.

Existing runtime registries, positive evidence, source/signature inventories,
declaration freshness, stub validation, type negatives, ownership audits, and
focused lower-level tests remain. Exact existing exports with incomplete owner
metadata now have precise Node/Python parity mappings. Registry selector counts
and hashes are refreshed for those mappings while their historical test evidence
is preserved. Migrated summary rows require receipts and cannot borrow a legacy
registry claim.

Partial class migrations retain known unrelated methods under the frozen
`operation_scope.py` dispositions. These exclusions grant no evidence and leave
those methods with their original checks. Unknown new methods have no such
disposition and fail the migrated class's executable coverage check. Binary I/O,
DDS, caching, streaming, message mutation/title helpers, and other unexercised
operations retain their focused tests. No legacy evidence is retired by #209.

## Validation recorded for this change

All 21 applicable participant/family executions passed locally, including each
native CXX family on MSVC and clang-cl. The retained Python suite passed 529
tests, Bun passed 1,035 tests, and Node passed 17 tests. Full Rust suites for the
conformance host and five domain owners passed, including their documentation
tests with the preexisting ignored examples. The complete binding-compliance
tooling suite passed 519 tests; two parameter combinations are intentionally
inapplicable because CXX has no message-formatting or shared-path export.

The three parity gates, Node declaration freshness and type contracts, Python
stub validation (zero warnings), Rust formatting/Clippy, and Python lint checks
passed. Standards and specification reviews found no actionable findings.
These local results accompany the required CI jobs; they do not claim CI has
run for an unpublished commit.
