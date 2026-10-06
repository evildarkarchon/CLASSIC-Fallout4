# Final 23-crate workspace

This is the outcome inventory for [issue #260](https://github.com/evildarkarchon/CLASSIC-Fallout4/issues/260), the last batch of the [23-crate layout work](https://github.com/evildarkarchon/CLASSIC-Fallout4/issues/234). It compares the finished workspace with the [validated 43-crate baseline](../baseline/validated-36127742320/README.md) captured by #237 before the first owner move.

[`graph.json`](graph.json) was derived at branch revision `f8e46aa4dc89e3bfb8b04e93ceb52268caa3f2f9` (Git tree `e99bb99d4b821f7c3493b76fbbe8e7fe635f5d41`) with the same command and rules as the [baseline graph](../baseline/README.md#physical-workspace-graph): `cargo metadata --locked --offline --format-version 1 --no-deps`, `workspace_members` as the crate set, internal means a workspace package name with a null `source`, a null `kind` counts as `normal`, an entry keeps its kind even when the same pair also appears under another kind, and groups are the first directory of each manifest path. The commit that adds this directory changes documentation only, so the graph is the same at that commit.

## Physical crates

| Manifest group | Baseline | Final | Change |
| --- | ---: | ---: | --- |
| `foundation` | 4 | 3 | `classic-shared-py` folded into the Python adapter |
| `business-logic` | 19 | 16 | `classic-perf-core` (#256), `classic-settings-core` (#257), `classic-version-core` (#258) retired |
| `python-bindings` | 17 | 1 | 17 `classic-*-py` crates replaced by `classic-python-bindings` (#259) |
| `node-bindings` | 1 | 1 | `classic-node` |
| `ui-applications` | 1 | 1 | `classic-tui` |
| `cpp-bindings` | 1 | 1 | `classic-cpp-bridge` |
| **Total** | **43** | **23** | 21 retired, 1 added |

The three foundation crates are `classic-operation-context`, `classic-vocabulary`, and `classic-shared-core`. The 16 business-logic crates are `classic-config-core`, `classic-database-core`, `classic-durable-publication`, `classic-file-io-core`, `classic-message-core`, `classic-path-core`, `classic-registry-core`, `classic-resource-core`, `classic-scan-presentation`, `classic-scangame-core`, `classic-scanlog-core`, `classic-update-core`, `classic-user-settings-core`, `classic-version-registry-core`, `classic-web-core`, and `classic-xse-core`. The one Python adapter, `classic-python-bindings`, builds one native extension (`_classic_native._native`) and one wheel behind the 18 `classic_*` direct-import facades.

No retired crate remains as a workspace member, a manifest dependency, or a forwarding re-export. Their Rust import paths ended without shims; the migration notes live in the owner pages under [`docs/api/`](../../../api/README.md).

## Internal dependency entries

| Kind | Baseline | Final |
| --- | ---: | ---: |
| `normal` | 161 | 104 |
| `dev` | 14 | 10 |
| `build` | 0 | 0 |
| Distinct source/target pairs | 173 | 113 |

One pair occurs in both kinds (`classic-update-core` to `classic-file-io-core`), so 114 entries form 113 distinct pairs.

The normal graph (including build edges) is acyclic, and it points inward: no foundation crate depends on a business-logic crate or an adapter, and no business-logic crate depends on an adapter. The foundation crates have no internal dependencies at all.

Where the 57 normal and 4 dev entries went, by source group:

| Source | Baseline normal / dev | Final normal / dev |
| --- | ---: | ---: |
| Foundation and business logic (baseline excludes `classic-shared-py`) | 55 / 13 | 44 / 9 |
| Python adapters (baseline: 17 crates plus `classic-shared-py`) | 58 / 0 | 17 / 0 |
| `classic-cpp-bridge` | 19 / 0 | 17 / 0 |
| `classic-node` | 20 / 0 | 17 / 0 |
| `classic-tui` | 9 / 1 | 9 / 1 |

Seventy-eight baseline entries named a retired crate (75 normal, 3 dev); 58 of them belonged to the Python adapters. Among the 22 crates that exist in both graphs, the moves removed these entries:

- `classic-config-core` to `classic-path-core` (config owns the YAML cache location, #246)
- `classic-file-io-core` to `classic-durable-publication` (YAML install, rollback, and self-heal moved to config, #248)
- `classic-file-io-core` to `classic-operation-context` and `classic-xse-core` (Crash Log collection moved to scanlog, #254)
- `classic-resource-core` to `classic-path-core` (neutral path primitives moved to shared core, #245)
- `classic-tui` to `classic-file-io-core` (game-file operations moved to resource, #250)
- `classic-scanlog-core` to `classic-path-core` as `dev` (now a normal edge, below)

and added these:

- `classic-path-core` and `classic-resource-core` to `classic-shared-core` (#245)
- `classic-resource-core` to `classic-file-io-core` (#250: resource applies game-target rules over file I/O's neutral primitives)
- `classic-scangame-core`, `classic-tui`, and `classic-cpp-bridge` to `classic-resource-core` (game-target DDS rules #249, game-file operations and backups #250/#251)
- `classic-scanlog-core` to `classic-path-core` as `normal` (custom-scan folder policy validates setup paths, #254)
- `classic-python-bindings` to its 17 owners: every business-logic crate except `classic-durable-publication`, plus `classic-shared-core` and `classic-vocabulary`

Graph guards: `classic-file-io-core/tests/dependency_boundary.rs` and `classic-xse-core/tests/dependency_boundary.rs` fail if file I/O or XSE regains a removed edge.

## Remaining cross-crate handoffs

These are the workflows that still cross a crate boundary. Each crosses in one direction and hands over typed facts or a scope, not a second copy of the policy.

| Handoff | Producer | Consumer | What crosses |
| --- | --- | --- | --- |
| Game Local facts to XSE Folder | `classic-config-core` (`read_game_local_facts`) | `classic-xse-core` (`resolve_xse_folder_from_game_local_facts*`), composed by `classic-scangame-core` (`resolve_xse_folder_for_scan*`) | `XseGameLocalFacts`; XSE never reads YAML or depends on config |
| XSE Folder for Crash Log collection | `classic-scangame-core` | `classic-scanlog-core` (Standard collection and the Crash Log Scan Run) | a resolved folder, in the run's Version Registry scope |
| Setup path validation | `classic-path-core` | `classic-scanlog-core`, `classic-scangame-core`, `classic-xse-core` | documents/game discovery and validation results |
| Installed YAML Data, Local Ignore, and crashgen rules | `classic-config-core` | `classic-scanlog-core` (run inputs, Local Ignore reset), `classic-scangame-core` (crashgen rule model, game layout), `classic-scan-presentation` (YAML Data provenance and role tokens) | selected YAML Data snapshots, typed outcomes, and config-owned tokens |
| FormID Value Lookup | `classic-database-core` | `classic-scanlog-core` | hit, miss, disabled, or failure per lookup; an unopenable database fails the run, other lookup failures retry with lookup disabled ([ADR 0005](../../../adr/0005-semantic-autoscan-report-contributions.md)) |
| Crash Log Scan Run Display Content | `classic-scanlog-core` | `classic-scan-presentation` | run outcomes; presentation renders Display Content, frontends own Display Layout |
| Game Setup Intake proposals | `classic-scangame-core` | callers (GUI, CLI, TUI, bindings) | typed Game Setup Checks and optional Game Setup Path Updates; intake reads an already-opened `classic-user-settings-core` group and never persists |
| Game-target files | `classic-file-io-core` | `classic-resource-core` | neutral DDS headers, hashes, and file primitives under resource's game-target rules and backups |
| Durable Publication | `classic-durable-publication` | `classic-config-core`, `classic-user-settings-core` | atomic publish; YAML and User Settings policy stay with their owners |
| YAML Data install and rollback | `classic-config-core` | `classic-update-core` | `install_atomic`/`rollback` and the YAML cache location for the YAML Data channel |
| Notification cache location | `classic-path-core` | `classic-update-core` | the app-notification cache directory |
| Application-directory registry | `classic-registry-core` | `classic-config-core` | the registered application directory, through an explicit `RegistryScope` |
| Version Registry metadata | `classic-version-registry-core` | config, XSE, scangame, scanlog | `VersionRegistryScope`; unscoped Rust/CXX/Node paths use the default scope |
| File hashes | `classic-file-io-core` | `classic-scangame-core`, `classic-update-core` | `FileHashScope`-selected hash cache and statistics |
| Cancellation | `classic-operation-context` | `classic-scanlog-core` | operation-local cancellation |

The one XSE folder-name rule (`F4SEVR` uses `F4SE`) is now owned only by `classic_xse_core::xse_folder_name`; Game Setup Intake's private copy was removed in #260.

## Coordination in adapters and tooling

Some coordination moved out of the core graph rather than disappearing:

- **Python scopes.** The one adapter selects opaque core-owned scopes (registry and application directory, both YAML cache scopes, file-hash cache, and Version Registry snapshot) at facade entry or object construction, so 18 facades in one native library keep their former isolation. `classic_perf` and `classic_shared` deliberately share the library's one default timing store. See [`python-bindings-adapter.md`](../../../api/python-bindings-adapter.md).
- **Rust conformance participant.** The Rust semantic participant for every family is hosted in `classic-scanlog-core/tests/semantic_conformance.rs`, which is why scanlog carries seven of the ten `dev` entries (message, registry, resource, update, user-settings, web, XSE).
- **Parity and coverage routing.** Parity rows keep their stable IDs and name the actual owner crate and symbol. `tools/binding_compliance/conformance/coverage.py` preserves exported-operation identity for symbols that moved into shared core, config, resource, and Version Registry, and maps renamed Python facade owners (`_RENAMED_PYTHON_FACADE_OWNERS`). Each conformance pack's `domainOwner` (or capability `rustCrate`) must name the same crate as the rows it covers, or a participant silently becomes "not applicable". Facade-only Node `@rust` proxy rows were dropped or remapped to `classic-shared-core` when their facade crate retired.
- **Source identity.** Scan-run, autoscan, and consumer conformance plans hash the whole `src` trees of scanlog, config, database, scangame, and scan presentation; the Python participant hashes the whole adapter (`src` and `python`); the CXX plan preparer fingerprints the resource and file-I/O sources.

## Evidence

- Final graph: [`graph.json`](graph.json).
- Parity artifacts: [`cxx_api_parity/baseline/`](../../cxx_api_parity/baseline/), [`node_api_parity/baseline/`](../../node_api_parity/baseline/), [`python_api_parity/baseline/`](../../python_api_parity/baseline/), Node [`index.d.ts`](../../../../node-bindings/classic-node/index.d.ts), and the Python facade stubs under [`python-bindings/classic-python-bindings/python/`](../../../../python-bindings/classic-python-bindings/python/).
- Contract documentation: the owner pages indexed by [`docs/api/README.md`](../../../api/README.md), [`binding-parity-overview.md`](../../../api/binding-parity-overview.md), and [`python-bindings-adapter.md`](../../../api/python-bindings-adapter.md).

### Local gates at the graph revision

Run on Windows on 2026-10-05 (Pacific time) at the graph revision, after `uv sync --project python-bindings --inexact` and with `PYO3_PYTHON` pointing at `python-bindings/.venv/Scripts/python.exe`. The C++ wrappers ran from a `subst` drive mapped to the checkout to stay under the Windows path limit.

| Gate | Command | Result |
| --- | --- | --- |
| Rust format | `cargo fmt --all -- --check` | pass |
| Rust lint | `cargo clippy --workspace --all-targets --all-features -- -D warnings` | pass |
| Rust build | `cargo build --workspace` | pass |
| Rust tests | `cargo test --workspace --all-features` | pass (3,221 passed, 0 failed, 39 ignored) |
| Source profile | `python tools/binding_compliance/check_compliance.py --repo-root . --profile ci` | pass (16/16) |
| Static coverage diagnostic | `retirement_readiness.py --fail-on-unmatched` | pass (0 runtime rows without a predicate) |
| Binding Compliance tooling | `pytest tools/binding_compliance/tests` | pass (966 passed, 2 skipped) |
| CXX parity | `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` | pass |
| CLI, MSVC | `classic-cli/build_cli.ps1 -Test` | pass (84/84 CTest, 24/24 integration) |
| CLI, clang-cl | `classic-cli/build_cli.ps1 -Test -Compiler clang-cl` | pass (84/84 CTest, 24/24 integration) |
| GUI, MSVC | `classic-gui/build_gui.ps1 -Test` | pass (23/23 CTest) |
| GUI, clang-cl | `classic-gui/build_gui.ps1 -Test -Compiler clang-cl` | pass (23/23 CTest) |
| Node build | `bun run build` (VS dev shell) | pass |
| Node parity and declarations | `bun run parity:gate:ci` | pass (Tier-1 gate, `index.d.ts` freshness) |
| Node runtime and types | `bun run test:bun`, `test:node`, `test:types` | pass (1,080 Bun, 19 Node, types clean) |
| Python parity | `tools/python_api_parity/check_parity_gate.py` | pass |
| Python stubs | `validate_stubs.py ... --fail-on-warnings` | pass (18/18 modules) |
| Python wheel | `rebuild_rust.ps1 -Target python` | pass (obsolete wheels removed; 18/18 imports and versions verified in the upgraded venv and a clean install) |
| Python tests | `pytest python-bindings/tests` | pass (605 passed) |
| Touched conformance families | `run_semantic_conformance.py` and `run_cxx_conformance.ps1` | pass: `fallout4-metadata` (Rust, Python), `game-setup-intake` (Rust, Node, Python, CXX MSVC and clang-cl), `xse-folder` (Rust, CXX MSVC and clang-cl) |

The Python `fallout4-metadata` receipt, aggregated with `check_compliance.py --profile conformance --participant python`, credits `parity:python:version_registry.lib.Fallout4Version.version` as executable evidence.

### Same-revision CI receipts

Local gates are scoped observations; they do not certify the repository. The certifying evidence is the blocking [Binding Compliance workflow](../../../../.github/workflows/ci-binding-compliance.yml) on the merged revision: fresh Rust, Node, Python, MSVC CXX, and clang-cl CXX receipts beside their immutable `run_plan.json` files, CXX `attempt.json` and `ctest.junit.xml` evidence, and a `full` aggregation reporting `repositoryComplete: true`. Only that `full` job may claim completion.

Before #260 the `full` job failed on exactly one uncovered row, `parity:python:version_registry.lib.Fallout4Version.version` ([run 37413929087](https://github.com/evildarkarchon/CLASSIC-Fallout4/actions/runs/37413929087) at `4715606f`, after #259: every participant job passed, all 85 families reported complete, and no family was missing). Since #244 the Python method reads its facade's Version Registry scope through `game_version_in`, and the row maps to that symbol, but the `fallout4-metadata` capability and predicate named only `game_version`. #260 declares `game_version_in` on that capability, so the executed Python `version()` observation now credits the row. The receipt-free diagnostic `python tools/binding_compliance/retirement_readiness.py --repo-root . --output <file> --fail-on-unmatched` reports zero runtime rows without a predicate.
