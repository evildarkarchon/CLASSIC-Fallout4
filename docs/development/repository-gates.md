# Repository gates

This page lists the repository checks that CI runs as direct, blocking steps
outside the conformance families. It replaces the deleted static compliance
catalog and its `cxx-ci` profile, which retired with the Python and Node
bindings (ADR-0010, in [`docs/adr/`](../adr/)).

Every Python command runs from the tools-only uv project at `tools/pyproject.toml`
(`uv sync --project tools`, then `uv run --project tools python ...`). CI
installs the same dependencies with `setup-python` and `pip`.

## Interim gates

Each of these steps stays in place until its replacement lands; the replacing
PR deletes the step and its row here.

| Check | Command (repo root) | CI step | Removed by |
| --- | --- | --- | --- |
| User Settings exclusive ownership | `python tools/user_settings_ownership/check.py --repo-root .` | `ci-rust.yml`, job `lint`, step "Check User Settings exclusive ownership" | the `user-settings-ownership` xtask port |
| Scan-run workflow policy | `python tools/binding_compliance/scan_run_workflow_policy.py --repo-root .` | `ci-rust.yml`, job `lint`, step "Check scan-run workflow policy" | engine PR A (`conformance check`) |

The scan-run workflow policy loads the conformance packs, whose User Settings
family needs `ruamel.yaml`, so the `lint` job installs it first. It also
loads `tests/conformance/participants.json` and fails when that catalog enrols
a family that has no pack. The ownership gate uses only the standard library.

## Other direct gates

| Check | Command (repo root) | CI step |
| --- | --- | --- |
| CXX bridge has no orphan exports | `cargo xtask cxx-bridge-gate` | `ci-cpp.yml`, job `cxx-bridge-gate` (`windows-latest`), step "Check for orphan CXX bridge exports" |
| Crash Log Scan Run contract variants | `python tools/binding_compliance/scan_run_contract.py --repo-root .` | `ci-rust.yml`, job `test`, step "Validate Crash Log Scan Run variant coverage" |
| Opaque CXX map reachability | `cargo test -p classic-cpp-bridge --test opaque_map_read_only` | `ci-rust.yml`, job `test`, through `cargo test --workspace --release` |
| Bundled YAML Data schema version | `cargo test -p classic-config-core --lib client_schemas` | `ci-rust.yml`, job `test`, through `cargo test --workspace --release` |
| Single Tokio runtime | `cargo clippy --workspace --all-targets --all-features -- -D warnings` | `ci-rust.yml`, job `lint`, step "Run clippy" |
| YAML Data publishes cleanly | `cargo xtask yaml-data validate --databases-dir "CLASSIC Data/databases" --schema-ranges "CLASSIC Data/databases/client-schema-ranges.yaml"` | `ci-rust.yml`, job `xtask-linux` (`ubuntu-latest`), step "Validate YAML Data" |

The CXX bridge gate enforces the consumer-driven bridge: every bridge function
has a production caller in `classic-cli/src` or `classic-gui/src`, and every
exported type is reached by a surviving function. A finding names the orphan
export, for example `orphan-export: function classic::<module>::<name> has no
caller in classic-cli/src or classic-gui/src`. It is source-only, so its job has
no `needs:` and runs in parallel with `cli-tests` and `gui-tests`; the build
wrappers do not call it. Missing exports are caught by the CLI and GUI
production builds instead. Rules and matcher details:
[`cxx-bridge-policy.md`](../api/cxx-bridge-policy.md#gate).

## Conformance applicability

Which semantic participants run which scenarios is declared in one central
catalog, `tests/conformance/participants.json`. Every family is Rust-only by
default; a family that enrols `cxx` lists the capability IDs CXX must cover,
and CXX then runs exactly the scenarios whose `action` is one of them. Packs
never choose their own participants, and the CLI, GUI and TUI consumers stay in
`tests/conformance/consumer-obligations.json`. The workflow policy derives the
required CI executions from both catalogs, so enrolling a family without a CI
step fails the scan-run workflow policy gate.

## Repository conformance verdict

The `full` job in `ci-binding-compliance.yml` waits for the `rust` and `native`
participant workflows, requires both to succeed, and then runs the
conformance-only verdict over every downloaded receipt:

```powershell
python tools/binding_compliance/check_compliance.py --repo-root . --profile full --receipt-directory tools/binding_compliance/artifacts/downloaded --output-dir tools/binding_compliance/artifacts/full
```

`check_compliance.py` keeps only the `conformance` and `full` profiles until the
Rust conformance engine replaces it (engine PR B).

Only `--profile full` with all family receipts can certify repository-wide
conformance. Full aggregation fails on any missing family, and each family
report requires every applicable participant and execution instance declared by
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
