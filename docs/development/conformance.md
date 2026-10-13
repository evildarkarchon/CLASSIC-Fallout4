# Conformance

Conformance proves that every implementation of a CLASSIC capability observes
the same behaviour. Each scenario is written once, as data, with an expected
result authored independently of any implementation. Every participant that the
catalogs require runs it and reports what it actually observed. One central
engine compares those observations with the expectations. A participant never
sees an expectation and never decides whether it passed.

The engine is `cargo xtask conformance` (`xtask/src/conformance.rs` and
`xtask/src/conformance/`). It has three commands:

- `check` validates the inputs statically;
- `run` executes one participant;
- `verdict` decides repository completeness from run artifacts.

This page covers the protocol, the catalogs, pack authoring and the commands.
`cargo xtask conformance <command> --help` and the module docs carry the exact
flags and rules.

## Terms

- **Family**: one area of behaviour with one versioned scenario pack, for
  example `user-settings` or `crash-log-scan-run`. There are 86.
- **Scenario pack**: `tests/conformance/packs/<family>/v1.json`. It declares
  the family's capabilities, fixtures and scenarios.
- **Capability**: a stable ID for one Rust-owned operation, such as
  `user-settings.update`. A scenario's `action` names the capability it
  exercises.
- **Participant**: an implementation that runs scenarios and writes a
  receipt. There are two kinds:
  - **Semantic adapters** report domain observations for scenarios:
    - `rust`: the Rust core crates, through `cargo test` runners. It runs
      every scenario of every pack.
    - `cxx`: the native C++ adapter over the CXX bridge, through CTest in
      `classic-cli`. It runs only the families that `participants.json`
      enrols.
  - **Consumers** report how a frontend presents Rust-owned results, through
    named obligations: `cli`, `gui` and `tui`.
- **Execution instance**: one build of a participant. The native participants
  have two, `windows-msvc` and `windows-clang-cl`. Every other participant has
  one, named after itself (`rust`, `tui`).
- **Run plan**: the input-only document the engine hands one invocation.
- **Receipt**: the participant's observations for one run plan.

A conformance runner is not a production caller, so it cannot keep a CXX bridge
export alive ([`cxx-bridge-policy.md`](../api/cxx-bridge-policy.md)).
Conformance decides which scenarios CXX runs. It never decides what the bridge
exports.

## Catalogs

Packs never choose their own participants. Two catalogs do.

### `tests/conformance/participants.json`

This catalog decides which families the semantic participants run:

- Rust is implicit and runs every scenario of every pack.
- A family is Rust-only unless the catalog enrols `cxx` for it, with the
  capability IDs CXX must cover. CXX then runs exactly the scenarios whose
  `action` is one of those capabilities. Other `capabilityIds` on a scenario
  do not exclude it.
- Families and capability IDs are sorted and unique. Every capability must
  exist in the pack, and every enrolment must select at least one scenario.
- Unknown fields, duplicate keys and families without a pack fail `check`.

### `tests/conformance/consumer-obligations.json`

This catalog registers the consumers. For each family, each consumer lists:

- its execution instances;
- its `sourcePaths`, the files whose bytes bind its receipts;
- the pack obligations it owns, each with the exact expected observation.

The CLI and GUI declare both native instances. The TUI declares one.

`check` derives every required (family, participant, execution instance) from
the packs and both catalogs. That set, 123 executions today, is the
denominator for the verdict and for the CI workflow policy.

## Authoring a pack

A pack is closed JSON. It is parsed strictly: duplicate keys, floating-point
numbers, `NaN`, a BOM and unknown members all fail. Its top level holds:

- `schemaVersion`, `familyId` and `familyVersion`;
- `domainOwner.rustCrate`;
- `fixtureRoot`, and the `fixtures` alias map beneath it;
- `capabilities`: each has an `id`, `rustSymbols` and `observationFamilies`;
- `scenarios`;
- `consumerObligations`.

Each scenario has an `id`, an `action`, `capabilityIds`, `fixtureRefs`, an
`input`, an `expected` observation and a `normalization` block.

The rules `check` enforces:

- **Stable IDs.** Family, capability, scenario, action and obligation IDs are
  stable machine identifiers. Bump `familyVersion` when the contract changes.
- **Fixtures.** Fixtures stay beneath `fixtureRoot`, as canonical relative
  paths, and must exist. A `.json` fixture must be valid JSON.
- **Inputs carry no results.** By default a scenario's input is exactly
  `{"fixtureRef": "<alias>"}`, with `fixtureRefs` equal to `[<alias>]`. The
  fixture references named in an input always equal `fixtureRefs`. Neither an
  input nor a JSON fixture may carry `expected` or `observation` data, or the
  scenario's expectation.
- **Richer inputs need a hook.** A family with richer inputs (for example
  user-settings or crash-log-scan-run) checks them in its own `validate_inputs`
  hook in `xtask/src/conformance/families.rs`.
- **Independent expectations.** `expected` is written from the contract, not
  copied from an adapter's output. If an expectation refers to an independent
  oracle, `compile_expectations` compiles it against that oracle. The oracles
  are user-settings' compatibility corpus, autoscan-report's Markdown goldens
  and the vocabulary families' Rust tokens. If the input or expectation
  disagrees with the oracle, `check` fails.
- **Exact normalization paths.** Paths are `$` followed by dotted field names
  or numeric indices. Wildcards, filters and the bare root are invalid.
  - `unorderedPaths` lists arrays that may be compared in any order.
  - Each `excludedPaths` entry is `{path, rationale}`.
  - Each `optionalEmptyFiles` entry is `{path, relativePath, rationale}` and
    permits one absent or empty file at that tree position.
  - `rootRelativePaths` makes fixture-root paths relative.

To add a family:

1. Write the pack and its fixtures.
2. Give the Rust runner its case: the shared semantic runner is
   `business-logic/classic-scanlog-core/tests/semantic_conformance`, and some
   families have dedicated runners.
3. If the family runs anywhere other than the shared semantic runner, register
   its command in the command table (`xtask/src/conformance/launch.rs`).
4. Add family hooks only if the generic input rule cannot express the inputs.
5. To bring CXX in, enrol the family in `participants.json` and dispatch it in
   the native runner under `classic-cli/tests/conformance`.

Run `cargo xtask conformance check` after every step.

## Protocol

### Run plans

`run` builds one input-only plan per (family, participant, execution instance)
and writes it as canonical JSON to
`<artifact-root>/<participant>/<instance>/<invocation id>/run_plan.json`. The
plan holds:

- the family identity, `fixtureRoot` and `fixtures`;
- for a semantic adapter, the applicable scenarios, with their inputs and
  normalization but never `expected`;
- for a consumer, its obligation and scenario IDs;
- `expectationDigest`: a framed SHA-256 over the canonical pack, its oracles
  and its fixtures;
- `sourcePaths`, and `invocation`: a fresh UUID, the
  `sourceIdentity` (`git:<HEAD>:sha256:<digest>` over the pack, fixtures,
  oracles and source paths, with directories expanded) and the
  `runPlanDigest`.

The participant receives the plan and the receipt path in environment
variables:

- semantic adapters: `CLASSIC_CONFORMANCE_RUN_PLAN` and
  `CLASSIC_CONFORMANCE_OUTPUT`;
- consumers: `CLASSIC_CONSUMER_CONFORMANCE_RUN_PLAN` and
  `CLASSIC_CONSUMER_CONFORMANCE_OUTPUT`.

Runners skip when these variables are absent. The CTest runners exit 125, so
ordinary `-Test` builds skip them.

### Receipts

A receipt echoes the plan's identity and lists each planned scenario exactly
once:

- its `executionStatus`, which is `completed` or `failed`;
- its `capabilityIds`;
- the actual `observation`;
- a `failure` (`{kind, message}`) when the status is `failed`, else `null`.

There is no `not_applicable` or `unsupported` status. A required scenario
cannot be skipped.

Central validation runs in this order, and stops at the first stage that
fails:

1. The receipt exists.
2. It is strict JSON.
3. No scenario is skipped or unsupported.
4. It has the closed receipt shape.
5. Its identity matches the current invocation: digests, source identity and
   participant.
6. It holds no unplanned, duplicate or missing evidence.
7. Each scenario is compared.

The comparison for each scenario:

1. The family's `normalize_observation` hook runs before the declared
   normalization.
2. The declared normalization runs.
3. The hook runs again after it.
4. The Display Content carriers are checked.
5. The normalized observation is compared exactly with the expectation.
   Types are compared first. Extra, missing or reordered values are
   mismatches.

Consumers are compared obligation by obligation, against the catalog's
expected observations.

### Failure kinds

| Kind | Meaning |
| --- | --- |
| `local_environment_failure` | A wrapper failed for want of a local toolchain or environment prerequisite |
| `adapter_command_failure` | The participant command failed, timed out, could not start, or reported a failed scenario |
| `missing_execution_receipt` | A required execution, receipt or scenario produced no evidence |
| `malformed_execution_receipt` | The receipt is not strict JSON or not the closed shape, or holds duplicate or unknown entries |
| `stale_execution_receipt` | The digest, invocation, run plan or source identity no longer matches the tree |
| `applicability_violation` | A required scenario was skipped or marked unsupported |
| `coverage_mapping_gap` | A consumer obligation has no passing, executed evidence |
| `normalization_failure` | An observation cannot be normalized without inventing or discarding data |
| `semantic_conformance_mismatch` | A valid normalized observation differs from the expectation |

## Commands

### `cargo xtask conformance check`

`check` is static, and runs no participant. It validates:

- every pack;
- both catalogs;
- the CI workflow policy, described below.

It runs in the ci-rust `lint` job.

### `cargo xtask conformance run --participant <p>`

`run` runs every family that requires the participant's instance, one
invocation per family. Its flags:

- `--compiler <msvc|clang-cl>`: required for cxx, cli and gui, and rejected
  for rust and tui;
- `--preset <name>`: the GUI wrapper's `-Preset`;
- `--family <id>`: restrict the run to one family (repeatable);
- `--artifact-root <dir>`: where the artifacts go. The default is
  `target/conformance`.

`run` keeps going past failed families. Its summary names each family that
failed. For each family it writes four files:

- `run_plan.json`;
- `receipt.json`, written by the participant;
- `attempt.json`: the command, exit code, timeout and captured output;
- `conformance_report.json`.

The command table in `xtask/src/conformance/launch.rs` decides what each
participant runs:

- **rust and tui** run their `cargo test` runners. The time limit is
  1200 s per family. The two `classic-cpp-bridge --lib` runners
  (markdown-rendering and report-discovery) go through
  `tools/enter_vs_dev_shell.ps1`.
- **cxx, cli and gui** call the build wrappers with
  `-Test -TestOnly -CTestName <test> -Compiler <c>`, so a wrapper build of
  the same commit must already exist (AGENTS.md rule 9). The time limit is
  15 minutes per family.

`update-services` and `yaml-update-operations` run against an in-process
controlled update service. Its address is passed in
`CLASSIC_CONFORMANCE_SERVICE`. It serves exactly the responses the fixtures
script, and fails the run on any unplanned, unused or authenticated request.
Only the Rust participant runs these two families.

Use a fresh artifact root for each run. Two runs of one execution instance
under one directory are duplicate evidence to the verdict.

### `cargo xtask conformance verdict --receipts <dir> [--output <file>]`

`verdict` finds every `run_plan.json` beneath `<dir>`. It authenticates each
plan against the current tree, and validates the receipt beside it. It passes
only when every pack's family passes on every required execution. Each
problem is a finding:

- a missing, stale or mismatched execution;
- an untracked family;
- a plan that no longer authenticates.

`--output` writes the verdict document as JSON.

## CI

There is one `conformance run` step per participant job, and one artifact per
(participant, execution instance):

| Workflow and job | Run steps | Artifacts |
| --- | --- | --- |
| `ci-rust.yml` `test` | `--participant rust`, `--participant tui` | `rust-conformance`, `tui-conformance` |
| `ci-cpp.yml` `cli-tests` (`compiler: [msvc, clang-cl]`) | `--participant cxx`, `--participant cli` | `cxx-conformance-<compiler>`, `cli-conformance-<compiler>` |
| `ci-cpp.yml` `gui-tests` (`compiler: [msvc, clang-cl]`) | `--participant gui --preset ci-system-qt` | `gui-conformance-<compiler>` |

Run steps use `if: ${{ !cancelled() }}`, so they still report after an earlier
failure. Uploads use `if: always()`. The artifact root is under
`runner.temp`, not under the cached `target/`.

The `full` job in `ci-binding-compliance.yml` has `needs: [rust, native]`. It
works in three steps:

1. It downloads every `*conformance*` artifact of the current run, unmerged.
2. A guard step requires both reusable workflows to have succeeded.
3. It runs `cargo xtask conformance verdict` and uploads the verdict document.

### Workflow policy

`check` parses the three CI workflows with `yaml-rust2` and walks
`jobs → steps`. It pins these jobs:

- in `ci-rust.yml`: `lint`, `test` and `xtask-linux`;
- in `ci-cpp.yml`: `cxx-bridge-gate`, `cli-tests` and `gui-tests`;
- in `ci-binding-compliance.yml`: `full`.

For each pinned job it checks:

- its runner, its exact `timeout-minutes` and its `needs`;
- `if: ${{ !cancelled() }}` exactly when the job has `needs`;
- no `continue-on-error`;
- one default `actions/checkout@v6`;
- for the native jobs, the `compiler: [msvc, clang-cl]` matrix with
  `fail-fast: false`.

Each pinned step must appear once, in order, with its exact `run` or `uses`,
`if`, `with`, `env` and step timeout, and no other keys. The pinned steps are:

- the surviving gates: `cxx-bridge-gate`, `user-settings-ownership`,
  `scan-run-contract`, `conformance check`, clippy, the cargo-test steps, and
  the `xtask-linux` steps;
- the native build-and-test steps;
- every conformance run and upload;
- the `full` job's download, guard, verdict and upload.

The policy also checks these:

- Every required participant instance has a run step, and every run step runs
  a required participant.
- The `rust` and `native` reusable jobs cannot be skipped.
- The pinned Corrosion source is archived once and verified before each
  native build.

The pins live in `JOBS` in `xtask/src/conformance/workflow_policy.rs`. To
change a pinned step, edit the workflow and the pin in the same change.
`xtask/tests/conformance_workflow_policy.rs` checks that deleting or weakening
any pinned step or job fails.
[`repository-gates.md`](repository-gates.md) lists the other gates.
