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

Orphan CXX bridge exports are checked by `cargo xtask cxx-bridge-gate`, which
exists but is wired into CI only by T2.

## Other direct gates

| Check | Command (repo root) | CI step |
| --- | --- | --- |
| Crash Log Scan Run contract variants | `python tools/binding_compliance/scan_run_contract.py --repo-root .` | `ci-rust.yml`, job `test`, step "Validate Crash Log Scan Run variant coverage" |
| Opaque CXX map reachability | `cargo test -p classic-cpp-bridge --test opaque_map_read_only` | `ci-rust.yml`, job `test`, through `cargo test --workspace --release` |
| Bundled YAML Data schema version | `cargo test -p classic-config-core --lib client_schemas` | `ci-rust.yml`, job `test`, through `cargo test --workspace --release` |
| Single Tokio runtime | `cargo clippy --workspace --all-targets --all-features -- -D warnings` | `ci-rust.yml`, job `lint`, step "Run clippy" |

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
