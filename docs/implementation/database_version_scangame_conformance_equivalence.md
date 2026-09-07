# Database, Version Registry, and Scan Game conformance equivalence

Issue #210 migrates deterministic operations into the executable umbrella from
#185. Expectations are authored in the versioned packs; adapters receive only
fixture references and input actions. No existing evidence is retired.

| Pack | Canonical Rust owner | Executed facts |
| --- | --- | --- |
| `database-operations` | `classic-database-core` | Pool construction and initialization; game table; availability; single and batch lookup hits, empty values, misses, duplicates and ordering; clear/close lifecycle; missing database without creation; invalid SQLite open error; unchanged exact database bytes |
| `version-registry` | `classic-version-registry-core` | Fixture-seeded metadata lookup and miss; full returned metadata projection; standard and VR version selection; exact/unknown matches; malformed version rejection; unchanged YAML bytes |
| `scan-game` | `classic-scangame-core` | INI validation reports and structured particle findings; corrected settings; Fallout4 versus Fallout4VR selection; ENB absent/partial/present and valid/missing/unreadable config; unchanged files and directories |

All three packs execute through Rust, Node, Python, and CXX. CXX runs on both MSVC
and clang-cl. Database CXX observes both legacy string and typed optional lookup
APIs; Version Registry observes both public CXX namespaces. Scan Game's CXX
root-scoped issue wrapper now fills the Rust validator cache before detection,
matching the maintained Rust/Node/Python sequence. A bridge regression proves the
previous empty result and verifies that loading leaves source bytes unchanged.

## Fixtures and observations

Fixtures live under `tests/fixtures/database_operations_conformance`,
`version_registry_conformance`, and `scan_game_conformance`. Packs live under
`tests/conformance/packs/{database_operations,version_registry,scan_game}/v1.json`.
SQLite bytes are supplied by a checked-in fixture, not by an installed game.
Version Registry's process-wide singleton is seeded from identical owned YAML
before the first public call in its dedicated participant process. Each scenario
uses a disposable root. No live Windows registry, network, user configuration,
or installed game is consulted.

Database files use exact hexadecimal bytes; YAML/INI text inventories preserve
content. Path normalization removes only owned temporary roots and native path
separators. INI reports preserve their domain wording and ordering. Domain errors
are attributed from actual public error carriers. Empty lookup values remain
distinct from successful misses, and skipped execution cannot count as either.

## Retained evidence and migration limits

The existing database pool tests, Version Registry fixture/unit tests, Tier-1
auxiliary binding tests, and Scan Game INI/ENB diagnostics remain in the same
checkout's full Rust, Bun/Node, Python, and CLI wrapper suites. Source parity,
declaration freshness, type negatives, stub validation, and ownership audits
remain blocking. The new native steps follow their retained suite in each CI job
and upload family-specific receipts, reports, and bounded attempt diagnostics.

Database tuning, statistics, maintenance and default-value helpers retain their
existing checks. Version Registry's unexercised enumeration, compatibility,
crashgen, hash and convenience helpers also retain their existing checks, as does
ENB message formatting. Exact existing selectors are frozen in
`tools/binding_compliance/conformance/families/operation_scope.py`; they grant no
new coverage. Unknown new methods or aliases cannot borrow a migrated class's
receipt. Scan Game orchestration, executable integrity, BA2, XSE, crashgen, log,
Wrye and discovery behavior remain outside this deterministic slice.

No maintained frontend seam changes, so this migration creates no CLI/GUI/TUI
consumer obligations. Each domain keeps its own observation contract rather
than using the Crash Log Scan Run shape.

## Execution and failure enforcement

After building the adapter, run
`python tools/binding_compliance/run_semantic_conformance.py --family <family> --participant <rust|node|python>`.
For CXX use
`tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Family <family> -Compiler <msvc|clang-cl>`.
The latter invokes the approved CLI wrapper and binds JUnit to the same execution
instance. CI reserves 360 minutes for the retained CLI suite and bounded family
launches. Missing, stale, malformed, skipped, mismatching, or incomplete receipts
fail the applicable scope. Neither the diagnostic migration ledger nor an old
runtime registry claim can satisfy the new receipt requirement.

## Local validation

All 15 family/participant executions passed, counting CXX MSVC and clang-cl
separately. The full Rust workspace passed 3,081 tests with 39 existing ignored
tests; Python passed 529, Bun 1,035, and Node 17. The retained CLI wrapper passed
84 unit tests and 24 integration scenarios. Compliance tooling passed 551 tests
with two preexisting inapplicable CXX combinations skipped. All three parity
gates, declaration freshness, TypeScript contracts, Python stubs (zero warnings),
Rust formatting/Clippy, and Python lint checks passed. Independent standards and
specification reviews found no blocking findings; consolidating repeated test
setup remains an optional maintenance suggestion. These local results do not
claim a run of GitHub Actions for the unpublished commit.
