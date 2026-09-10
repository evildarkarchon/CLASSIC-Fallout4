# Registry, settings, and version owner conformance

Issue #213 extends the existing owner packs with independent expectations and
input-only fixtures. The compliance command validates fresh receipts, exact
observations, source-derived applicability, and operation-scoped coverage.
Each required CXX participant has both MSVC and clang-cl execution instances.

| Pack | Executed public behavior | Required adapters |
|---|---|---|
| `registry-operations` | Typed storage, replacement, removal, clear, game-version lookup | Rust, CXX, Node, Python |
| `registry-game` | Explicit game selection, replacement, absence after clear, game key | Rust, CXX, Node, Python |
| `registry-gui` | Default, enabled, disabled and reset GUI flag; GUI key | Rust, CXX, Python |
| `registry-context` | Optional cached references, version/preferences, local-directory override and reset | Rust, Python |
| `registry-paths` | Application-directory absence, replacement, reset and forbidden filesystem writes | Rust, Node, Python |
| `registry-keys` | Every shared public Python/Rust key constant | Rust, Python |
| `settings-load` | Sync/async single/batch loaders, errors, cache lifecycle, statistics/reset, unchanged files | Rust, CXX, Node, Python |
| `settings-yaml` | Parse/read/update/save/reload, typed defaults, cache and exact saved bytes | Rust, CXX, Node, Python |
| `settings-yaml-batch` | Batch reads/updates, ordered mappings and vector mappings | Rust, Node |
| `settings-cached-docs` | Full cached documents, cached empty stream versus absence, invalidation | Rust, Node, Python |
| `settings-validation` | Typed validation/coercion, rejected values and structured error carriers | Rust, CXX, Python |
| `version-extraction` | Filename/log/all-version extraction and controlled known-game lookup | Rust, Node, Python |
| `version-f4se` | Known and unknown F4SE versions from controlled YAML | Rust, Python |
| `version-pe` | Synthetic PE version resources and missing/malformed inputs | Rust, CXX, Node, Python |
| `version-pe-path` | Executable path validity over test-owned files | Rust, Node, Python |
| `version-registry` | Metadata/matching, enumeration, XSE and Crashgen configuration | Rust, CXX, Node, Python |
| `version-registry-details` | Filters, addresses, hashes, compatibility and unknown-version policy | Rust, Node, Python |
| `version-registry-values` | Compatibility ranges and model queries | Rust, Python |
| `game-version-parse` | Valid, invalid and overflowing game versions | Rust, CXX, Node, Python |
| `game-version-distance` | Semantic distance | Rust, Node, Python |
| `game-version-order` | Same-major comparison with retained binding comparisons | Rust, Python |
| `fallout4-identity` | Ordered variant identity, executable and Steam metadata | Rust, CXX, Node, Python |
| `fallout4-paths` | Variant tokens, document names, standard/VR and registry identifiers | Rust, CXX, Python |
| `fallout4-metadata` | Controlled YAML-derived version metadata | Rust, Python |

Registry here means the Rust process-global registry. Its receipt runners own
their processes and clear state before and after observations, including failure
cleanup. They never inspect or mutate a contributor's Windows registry.
Filesystem scenarios use disposable directories, controlled YAML, and synthetic
PE bytes. They do not discover installed games or read user settings.

## Transport contracts and retained evidence

Optional values remain distinct from empty values. Registry object references
use strings to exercise value transport; these facts do not claim cross-language
object identity. Game selection uses explicit nonempty values because Python's
existing empty-string fallback differs from Node/Rust. Empty reference and typed
sentinel scenarios remain independently exercised. Application-directory paths
are checked for containment before projection to relative paths.

CXX PE extraction exposes a string and collapses domain failures to an empty
string. The PE pack compares that public result without inventing structured
errors the bridge cannot expose. Existing typed PE error tests remain retained.
Settings floating-point values use an explicitly tagged, lossless scientific
string carrier; JSON floating-point numbers remain prohibited in common receipts.

Ordered YAML entries are compared as arrays. The Node ordered-map accessor now
inserts properties directly into the JS object, preserving the Rust mapping's
order for ordinary string keys instead of passing through a sorted JSON map.
JavaScript's integer-index property enumeration rules still apply.

Parity corrections identify actual Rust owners of retained Node operations.
Three fictitious Python `@rust` mappings that pointed non-exported functions at
unrelated classes were removed; no callable Python export was removed. Rust
inventories and the real classes' structural evidence remain. Retained runtime
selector counts/hashes were refreshed without changing their tests or evidence
classification.

The source/signature gates, Node declaration freshness and compile-only type
negatives, Python stub validation, forbidden exports, ownership audits and prior
runtime suites remain required. Broad owner or class enrollment cannot grant a
new operation coverage. The operation policies admit only observed methods and
the explicit fields they transport. Old registry evidence is not retired here.

Value packs use granular source-backed methods where shared class carriers would
otherwise enroll an adapter lacking the operation. Binding-only equality, hash,
representation and comparison behavior retains its existing local runtime tests;
additional observations do not assign those methods invented Rust capability credit.

## Validation

Run `python tools/binding_compliance/run_semantic_conformance.py --family <pack>
--participant <rust|node|python>` for a fresh scoped result. Prepare and rebuild
the managed Python environment first. For CXX, use
`tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Family
<pack> -Compiler <msvc|clang-cl>`; this invokes the approved CLI wrapper.

The full tooling suite is `python -m pytest tools/binding_compliance/tests -q`.
Mutation checks reject missing/changed/extra observations, stale invocations,
missing participants and toolchains, and new unexecuted aliases. Passing
receipts and build logs remain untracked invocation artifacts.
