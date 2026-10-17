# Repository gates

This page lists the repository checks that CI runs as direct, blocking steps
outside the conformance families. It replaces the deleted static compliance
catalog and its `cxx-ci` profile, which retired with the Python and Node
bindings (ADR-0010, in [`docs/adr/`](../adr/)). Every gate is a Rust
command: a `cargo xtask` subcommand, a crate-local cargo test or clippy. The
conformance protocol, its catalogs and its CI steps are described in
[`conformance.md`](conformance.md).

## Other direct gates

| Check | Command (repo root) | CI step |
| --- | --- | --- |
| CXX bridge has no orphan exports | `cargo xtask cxx-bridge-gate` | `ci-cpp.yml`, job `cxx-bridge-gate` (`windows-latest`), step "Check for orphan CXX bridge exports" |
| User Settings exclusive ownership | `cargo xtask user-settings-ownership` | `ci-rust.yml`, job `lint`, step "Check User Settings exclusive ownership" |
| Crash Log Scan Run contract variants | `cargo xtask scan-run-contract` | `ci-rust.yml`, job `test`, step "Validate Crash Log Scan Run variant coverage" |
| Conformance packs, catalogs and workflow policy | `cargo xtask conformance check` | `ci-rust.yml`, job `lint`, step "Check conformance packs, catalogs and workflow policy" |
| Opaque CXX map reachability | `cargo test -p classic-cpp-bridge --test opaque_map_read_only` | `ci-rust.yml`, job `test`, through `cargo test --workspace --release` |
| Bundled YAML Data schema version | `cargo test -p classic-config-core --lib client_schemas` | `ci-rust.yml`, job `test`, through `cargo test --workspace --release` |
| Single Tokio runtime | `cargo clippy --workspace --all-targets --all-features -- -D warnings` | `ci-rust.yml`, job `lint`, step "Run clippy" |
| YAML Data publishes cleanly | `cargo xtask yaml-data validate --databases-dir "CLASSIC Data/databases" --schema-ranges "CLASSIC Data/databases/client-schema-ranges.yaml"` | `ci-rust.yml`, job `xtask-linux` (`ubuntu-latest`), step "Validate YAML Data" |
| App-notification source publishes cleanly | `cargo xtask app-notification validate --source "CLASSIC Data/app-notification.yaml"`, then `cargo xtask app-notification dry-run --workflow-tag app-notification-v0.0.0` | `ci-rust.yml`, job `xtask-linux` (`ubuntu-latest`), steps "Validate app-notification source" and "Dry-run app-notification publish" |
| A valid cached Documents path wins over platform discovery | `cargo test -p classic-path-core --lib docs_path` | `ci-rust.yml`, job `test`, through `cargo test --workspace --release` (the two tests are Windows-only; the job runs on `windows-latest`) |
| Frontends write no core-owned scan-run phrase or Display Label table (TUI) | `cargo test -p classic-tui --test shared_runtime_audit` | `ci-rust.yml`, job `test`, through `cargo test --workspace --release` |
| Frontends write no core-owned scan-run phrase or Display Label table (CLI) | `classic-cli/build_cli.ps1 -Test` (the `[display-label][audit]` cases in `classic-cli-tests`) | `ci-cpp.yml`, job `cli-tests` (both compilers), step "Build and test CLI" |
| Frontends write no core-owned scan-run phrase or Display Label table (GUI) | `classic-gui/build_gui.ps1 -Test -CTestName classic-gui-test-display-label-audit` | `ci-cpp.yml`, job `gui-tests` (both compilers), step "Build and test GUI" |

The CXX bridge gate enforces the consumer-driven bridge: every bridge function
has a production caller in `classic-cli/src` or `classic-gui/src`, and every
exported type is reached by a surviving function. A finding names the orphan
export, for example `orphan-export: function classic::<module>::<name> has no
caller in classic-cli/src or classic-gui/src`. It is source-only, so its job has
no `needs:` and runs in parallel with `cli-tests` and `gui-tests`; the build
wrappers do not call it. Missing exports are caught by the CLI and GUI
production builds instead. Rules and matcher details:
[`cxx-bridge-policy.md`](../api/cxx-bridge-policy.md#gate).

The User Settings ownership gate keeps User Settings with one Rust owner,
`classic-user-settings-core`. It audits production `.rs`, `.cpp`, `.h` and
`.hpp` files under `foundation`, `business-logic`, `cpp-bindings`,
`classic-cli`, `classic-gui` and `ui-applications`, skipping test, build and
dependency directories and `*_tests.rs` files. It fails on a raw
`CLASSIC_Settings` key outside the owner, on a returning `ClassicConfig`,
`PathConfig` or generic YAML `Settings` variant, and on runtime reads of the
`default_settings` compatibility mirror outside its generator. Comments are
ignored and string literals are audited. `cargo xtask user-settings-ownership
--help` lists the rules.

The scan-run contract gate reads
`tests/fixtures/crash_log_scan_run/manifest.json` and reports every finding in
one run. The manifest's `contractVariants` must match the Rust enums it names
(found with `syn`). Every variant needs a row in the variant evidence policy
(`xtask/src/scan_run_contract/variant_policy.rs`) whose scenario is a
`scenarios[].id` in `tests/conformance/packs/crash_log_scan_run/v1.json`, or a
retained label when no scenario can reach it. The Reset To Default and failure
fixtures must be complete, and no `forbiddenExports` symbol may appear in its
source file. The conformance workflow policy pins this step: it must stay
blocking, keep `if: ${{ !cancelled() }}`, and run before the Rust receipt step.

The conformance check validates, statically and without running any
participant, every scenario pack under `tests/conformance/packs/`,
`tests/conformance/participants.json`,
`tests/conformance/consumer-obligations.json` and the CI workflow policy.
Packs and catalogs are read as strict JSON (duplicate keys and floating-point
numbers fail) into closed shapes, so an unknown member fails. Pack inputs name
fixtures only (`{"fixtureRef": ...}`), fixtures stay beneath the pack's
`fixtureRoot`, and neither inputs nor fixtures may carry result data; families
with richer inputs check them in their own input hook. Families whose
expectations reference an independent oracle (user-settings' compatibility
corpus, autoscan-report's Markdown goldens, the vocabulary families' Rust
tokens) are compiled against it, so an input or expectation that disagrees
with its oracle fails too. The workflow policy
walks each workflow's `jobs` and `steps` with a YAML parser and pins every
gate in the table above: each gate's step must keep its exact `run` (or
`uses`), `if`, `with` and position, and its job must keep its runner,
timeout, `needs` and blocking status. It pins every `conformance run` step and
upload as well, the `compiler: [msvc, clang-cl]` matrix on `cli-tests` and
`gui-tests`, the `full` aggregation and the pinned Corrosion source. Deleting
or editing any of them fails the check. `cargo xtask conformance check --help`
lists the input rule; [`conformance.md`](conformance.md#workflow-policy) lists
the pins.

The cached Documents path test pins the installation-discovery source boundary
(#297): `DocsPathFinder::find_docs_path` returns a valid cached path before it
runs the non-injectable platform discovery, and falls back to discovery when
the cached path is invalid.
`valid_cached_docs_path_wins_over_a_discoverable_platform_path` and
`invalid_cached_docs_path_falls_back_to_platform_discovery` in
`business-logic/classic-path-core/src/docs_path_tests.rs` are Windows-only,
because the registry Documents folder is the one discovery result every host
is guaranteed to have.

The core-owned phrase audits keep Crash Log Scan Run prose and Display Labels
with the Rust crates that own them. Each frontend has one source audit:
`ui-applications/classic-tui/tests/shared_runtime_audit.rs`,
`classic-cli/tests/test_display_label_audit.cpp` and
`classic-gui/tests/test_display_label_audit.cpp`. All three read the one shared
deny-list, `business-logic/classic-scan-presentation/core-owned-phrases.txt`,
and fail when a frontend source string literal contains a listed phrase, when a
frontend turns an audited enum into its own naming table, or when the audit's
declared source list falls behind the directory it covers. The TUI audit also
pins the single shared Tokio runtime for TUI workflows.

## Tools that are not gates

| Tool | Command (repo root) | CI step |
| --- | --- | --- |
| Criterion post-processing (tail percentiles, old baseline cleanup) | `cargo xtask bench percentiles`, `cargo xtask bench cleanup [--keep <n>] [--execute]` | None. It is a local benchmarking aid with no CI home; no workflow runs it |

`cargo xtask bench` post-processes local Criterion output and never fails a
build on a performance result. Usage is in
[`profiling_workflow.md`](profiling_workflow.md).

## Conformance applicability

Which semantic participants run which scenarios is declared in one central
catalog, `tests/conformance/participants.json`. Every family is Rust-only by
default; a family that enrols `cxx` lists the capability IDs CXX must cover,
and CXX then runs exactly the scenarios whose `action` is one of them. Packs
never choose their own participants, and the CLI, GUI and TUI consumers stay in
`tests/conformance/consumer-obligations.json`. The workflow policy derives the
required CI executions from both catalogs. One `conformance run` step covers
every family of its participant, so a newly enrolled family needs no new step,
but a participant or execution instance without a run step fails
`cargo xtask conformance check`.

## Repository conformance verdict

The `full` job in `ci-binding-compliance.yml` waits for the `rust` and `native`
participant workflows, requires both to succeed, and then runs the verdict over
every conformance artifact the run uploaded:

```powershell
cargo xtask conformance verdict --receipts <downloaded artifacts> --output <verdict.json>
```

Each participant job produces those artifacts with one
`cargo xtask conformance run --participant <rust|cxx|cli|gui|tui>` step
(`--compiler ${{ matrix.compiler }}` for cxx, cli and gui), which runs every
family that requires the participant and keeps going past failures. The CXX,
CLI and GUI runs call the build wrappers with `-Test -TestOnly`, reusing the
job's earlier build. See [`conformance.md`](conformance.md) for the commands
and artifacts.

Only the verdict, given every family's artifacts, can certify repository-wide
conformance. It fails on any missing family, and each family report requires
every applicable participant and execution instance declared by
`tests/conformance/participants.json` and the consumer obligation catalog.
Registry metadata never supplies that proof.

Crash Log Scan Run and User Settings have blocking executable conformance
obligations. Rust, every CXX execution instance (MSVC and clang-cl) of a family
that `participants.json` enrols in `cxx` (User Settings does; Crash Log Scan Run
left CXX with the bridge trim), and every CLI, GUI, and TUI consumer obligation
in `tests/conformance/consumer-obligations.json` must emit current
same-revision receipts for their exact applicable scopes. Central validation requires the full scenario and
observation-family denominator plus every source-owned consumer obligation.
Missing, skipped, stale, malformed, duplicate, or semantically mismatched
evidence fails the applicable workflow. These receipts run conjunctively with
the runtime, Rust-variant, and native wrapper gates; promotion does not weaken
or retire those checks.

Autoscan Report output has a blocking semantic family. It runs on Rust only
since CXX left the family with the bridge trim (the exports it exercised had no
production caller). Fresh same-revision receipts compare actual persisted bytes
with the original immutable goldens, typed Display Content, and durable
filesystem effects. Existing owner goldens and focused assembly diagnostics
remain required. This family adds no public assembly API or frontend layout
contract; see the
[Autoscan Report evidence map](../implementation/autoscan_report_conformance_equivalence.md).

Conformance decides which scenarios CXX runs; it never decides what the bridge
exports. A conformance runner is not a production caller, so it cannot keep an
export alive ([`cxx-bridge-policy.md`](../api/cxx-bridge-policy.md)).
