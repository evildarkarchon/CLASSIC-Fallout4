# Executable Cross-Adapter Conformance Specification

> **Status: accepted design; implementation in progress.** [ADR-0008](../adr/0008-executable-cross-adapter-conformance.md) records the decision. Phase 0's diagnostic ledger and generic engine are implemented, together with the first input-only Crash Log Scan Run pack, its centrally derived family predicates, and public-seam Rust, Node, Python, and bridge-only CXX receipt runners in shadow. Existing, generated, malformed, Proceed Without Ignore, Reset To Default, successful reset, intervening conflict, portable backup failure, pre-discovery, post-discovery queued, admitted/durable, pre-reset, and post-critical cancellation, observer delivery failure, public request-validation/discovery/intake/report-write/Unsolved Logs finalization failures, replay, and abandonment scenarios execute through all adapters; the CXX scenarios run through the approved CLI wrapper on both MSVC and clang-cl and publish bounded attempt, JUnit, log, receipt, and instance-report artifacts. Replacement-publication and durability-unknown mappings remain under the reset blocking internal-fault analyzer. Injected analysis, FormID database access, initialization, and internal-invariant failure projections remain under the separate structured-failure retained analyzer; neither analyzer grants semantic-adapter coverage. Consumer receipts, equivalence review, blocking promotion, and legacy-evidence retirement remain later migration slices. Until a phase reaches its blocking exit gate, the commands and evidence documented in `docs/api/binding-compliance-suite.md` remain authoritative.

## Target

Turn binding parity evidence into executable conformance across every maintained binding domain. One deep module under `tools/binding_compliance/` must materialize deterministic scenarios, validate adapter and consumer receipts, compare actual normalized observations with an independent oracle, derive coverage from the public Rust capability through every binding mapping, preserve irreducibly static checks, and report one honest result.

The first vertical slice is Crash Log Scan Run and includes real CXX execution. Migration is not follow-up work: this specification defines the phases and deletion gates required to retire the current acknowledgement and runtime-registry layer safely.

## Accepted decisions

1. The target covers all binding parity surfaces, not only Crash Log Scan Run.
2. Expectations are scenario-owned. Rust is an adapter, never the oracle.
3. Observable semantics are common; language transport, declaration syntax, and frontend layout remain surface-specific.
4. CXX runtime conformance ships in the first executable slice.
5. Equivalent acknowledgement lists and positive source markers are removed after executable replacement; irreducible static and negative checks remain.
6. The implementation is a generic engine with versioned domain-specific scenario packs.
7. Runtime coverage is attached to meaningful operations and scenarios, then mapped transitively to contract rows.
8. Native workflows execute their own adapters and emit a common receipt. The compliance suite validates and aggregates receipts.
9. Migration is incremental: Crash Log Scan Run, User Settings, fixture-backed domains, remaining owner modules, then evidence cleanup.
10. Every adapter exposing a capability is required. `not_applicable` is valid only for a documented parity-policy exception.
11. Runtime, structural, type/declaration, and negative ownership evidence are separate evidence kinds in the same compliance report.
12. Scenario packs are JSON, comparison is exact after declared normalization, and passing receipts are ephemeral.
13. Each pack moves through shadow, equivalent, blocking, and retired states.
14. The CXX adapter is a bridge-only CTest target hosted by the CLI build; the production CLI interface does not change.
15. CLI, GUI, and TUI are consumer participants rather than additional semantic adapters.
16. Blocking scenarios are hermetic and stale receipts fail. A new runtime-verifiable parity row requires executable coverage or a policy exception in the same change; an irreducibly static row requires a named retained analyzer.

## Scope and non-goals

In scope:

- Rust, CXX, Node, and Python public binding semantics.
- CLI, GUI, and TUI consumption of binding-owned facts and Rust-owned Display Content.
- Shared fixtures, deterministic durable effects, structured failures, and observer events.
- Source-derived parity inventories and row-to-capability coverage.
- Declaration, stub, forbidden-export, type-level, Vocabulary, and Display Content ownership evidence in the combined report.
- CI receipt production, validation, failure classification, and migration accounting.

Out of scope:

- Moving business logic or validation out of Rust.
- Making binding transport shapes byte-identical.
- Making CLI, GUI, and TUI Display Layout identical.
- Adding a production CLI conformance command or test-only public binding API.
- Using live network services, user registry state, installed-game state, or mutable user files in blocking conformance.
- Treating implementation phases as parity tiers or permitting a deferred parity backlog.
- Deleting focused lower-level diagnostics merely because the umbrella can invoke them.

## Evidence model

| Role | Participants | Proves | Does not prove |
| --- | --- | --- | --- |
| Semantic adapter | Rust, CXX, Node, Python | Public operations produce the expected normalized domain facts and effects | Declaration completeness, erased types, absence of unused exports |
| Consumer | CLI, GUI, TUI | Facts and Display Content cross the frontend seam with required routing, ordering, interaction, and layout behavior | Binding parity or identical presentation |
| Structural analyzer | Rust/CXX/Node/Python surface parsers, declaration/stub validators | Public items, signatures, variants, declarations, and stubs have the required shape | Runtime behavior |
| Negative analyzer | Forbidden-export and ownership audits | Removed APIs and adapter-local duplicated policy/content remain absent | Positive runtime semantics |

There is no manual-evidence role. A test name, file path, marker string, selector hash, owner-module label, or `runtime_verified` claim can help locate diagnostics but cannot grant coverage.

## Proposed repository shape

The exact private file split may change during implementation, but the ownership boundaries must remain:

```text
tools/binding_compliance/
  check_compliance.py              existing public umbrella command
  catalog.py                       evidence requirements and profiles
  suite.py                         combined result and reporting
  conformance/
    schema.py                      scenario, run-plan, receipt validation
    packs.py                       discovery, digests, materialization
    applicability.py               participant and policy-exception rules
    coverage.py                    capability-to-parity-row expansion
    compare.py                     exact normalized comparison
    receipts.py                    receipt loading and execution proof
    failures.py                    common failure taxonomy
    adapters/                      native command/receipt integration only
    families/                      domain-specific input and observation rules
  tests/                           Python tooling tests

tests/conformance/
  schemas/                         tracked JSON Schemas
  policy_exceptions.json           narrow documented applicability exceptions
  packs/
    crash_log_scan_run/
    user_settings/
    <later domain families>/

tools/binding_compliance/artifacts/
  <participant>/<execution-instance>/<invocation-id>/
                                    ephemeral receipts, attempts, and JUnit where required
  binding_compliance_report.json   combined ephemeral report
  binding_compliance_report.md
```

`tools/binding_compliance/` owns the generic lifecycle. A family module may understand a Crash Log Scan Run Result or a User Settings snapshot, but no family-specific DTO becomes the engine's public interface. Existing modules such as `parity_rust_surface.py`, `parity_artifact_io.py`, `tools/cxx_api_parity/`, `tools/node_api_parity/`, `tools/python_api_parity/`, `validate_stubs.py`, and focused source audits remain specialized implementations behind the umbrella.

## Scenario-pack contract

### Tracked pack

Each pack is validated before any adapter runs. Its normative shape is:

```json
{
  "schemaVersion": 1,
  "familyId": "crash-log-scan-run",
  "familyVersion": 1,
  "domainOwner": {
    "rustCrate": "classic-scanlog-core"
  },
  "fixtureRoot": "tests/fixtures/crash_log_scan_run",
  "fixtures": {
    "validCrashLog": "valid-crash.log"
  },
  "capabilities": [
    {
      "id": "scan-run.execute.standard",
      "rustSymbols": ["Request", "execute"],
      "observationFamilies": [
        "run-status",
        "discovery",
        "setup",
        "installed-yaml-data",
        "log-results",
        "events",
        "display-content"
      ]
    }
  ],
  "scenarios": [
    {
      "id": "standard-end-to-end",
      "action": "scan-run.execute.standard",
      "capabilityIds": ["scan-run.execute.standard"],
      "fixtureRefs": ["validCrashLog"],
      "input": {},
      "expected": {},
      "normalization": {
        "rootRelativePaths": true,
        "unorderedPaths": [],
        "excludedPaths": []
      }
    }
  ],
  "consumerObligations": []
}
```

The example omits domain payloads for readability. Implemented schemas must enforce these rules:

- `schemaVersion`, `familyId`, `familyVersion`, capability IDs, scenario IDs, action IDs, observation-family IDs, and consumer-obligation IDs are stable machine identifiers.
- Fixture references resolve beneath the declared repository-owned fixture root. Absolute paths, parent traversal, and undeclared files fail validation.
- `expected` contains complete normalized values, expected durable effects, and forbidden effects where relevant. It is authored independently of adapter output.
- A scenario names canonical Rust capabilities, not binding export names, test files, or test-case strings.
- Applicability is derived from the canonical parity policy and source mappings. A pack cannot exempt one adapter with a free-form note.
- A scenario required for a participant cannot be skipped or marked unsupported. `not_applicable` must carry an ID present in `policy_exceptions.json` and the exception must name the capability, participant, rationale, and owning policy page.
- Common semantic expectations cannot be weakened in participant-specific sections. Legitimate consumer differences use named consumer-obligation profiles rather than language-specific semantic snapshots.
- Normalization declarations name exact observation paths. Wildcard removal of arbitrary fields is invalid.
- Every exclusion has a rationale. Timing and unconstrained concurrent interleaving are excluded by default; stable serialized ordering remains contractual.

Version 1 normalization paths use a deliberately small exact JSONPath grammar: `$` followed by one or more dotted field names or numeric array indices. Wildcards, recursive descent, filters, slices, and the root by itself are invalid. `unorderedPaths` is an array of those exact path strings. Each `excludedPaths` entry is an object containing exactly `path` and a non-empty `rationale`; a path cannot be both unordered and excluded.

### Input-only run plan

The engine validates a pack and materializes a temporary run plan containing only:

- schema and family identity;
- scenario IDs, actions, capabilities, and fixture references;
- deterministic input values;
- normalization instructions needed to construct observations;
- an opaque expectation digest;
- a unique invocation ID, current source identity, and run-plan digest;
- canonical repository-relative participant/runner source paths so receipt-only validation can recompute source identity;
- the required participant identity and role.

The run plan omits `expected`. Adapter runners must not load expectations or compare themselves with Rust output. Existing native tests may keep focused local assertions, but conformance passes only when the central comparator receives actual observations.

The expectation digest is SHA-256 over the engine's validated canonical JSON representation of the pack plus the relative path and raw bytes of every declared fixture, ordered by relative path and framed unambiguously by the engine. Canonical JSON uses UTF-8, recursively sorted object keys, no insignificant whitespace, and no ASCII escaping. Floating-point JSON numbers are forbidden in the common schema; normalized quantities use integers or an explicitly formatted string. The version 1 digest preimage uses type-tagged, unsigned 64-bit big-endian length frames for the contract marker, canonical pack, and each ordered fixture path/byte pair. Native runners receive the digest as opaque launch data, and the compliance engine recomputes it from the current tracked pack and fixtures when validating a receipt.

Every launch uses a new UUID invocation ID and unique artifact directory. The run-plan digest covers the canonical materialized plan before the self-referential `runPlanDigest` member is inserted; every other plan field, including the invocation ID, is covered. Source identity has the form `git:<current-revision>:sha256:<source-input-digest>` and covers the declared path identities and current bytes of the pack, declared fixtures, and caller-declared participant/runner source paths. It is recomputed during materialization and again when a later receipt-only process authenticates the plan, but remains stable when those source inputs are unchanged. Aggregation compares the embedded Git revision after authenticating each plan independently; participant-specific source digests need not be equal because their declared runner roots differ. The reserved receipt path must be absent before execution, preventing a prior receipt from being reused when source changes but the pack does not.

## Receipt contract

Each participant writes one receipt per pack invocation. The normative envelope is:

```json
{
  "schemaVersion": 1,
  "familyId": "crash-log-scan-run",
  "familyVersion": 1,
  "expectationDigest": "sha256:<hex>",
  "invocation": {
    "id": "<unique-run-id>",
    "runPlanDigest": "sha256:<hex>",
    "sourceIdentity": "<commit-and-worktree-digest>"
  },
  "participant": {
    "id": "cxx",
    "role": "semantic-adapter",
    "executionInstanceId": "windows-msvc"
  },
  "runner": {
    "id": "classic-cxx-conformance",
    "version": 1,
    "platform": "windows",
    "toolchain": "msvc"
  },
  "scenarios": [
    {
      "id": "standard-end-to-end",
      "executionStatus": "completed",
      "capabilityIds": ["scan-run.execute.standard"],
      "observation": {},
      "failure": null
    }
  ]
}
```

Receipt rules:

- `executionStatus` is `completed`, `failed`, or `not_applicable`. Semantic pass/fail is computed centrally after comparison.
- Invocation ID, run-plan digest, and source identity must match the current launch. A receipt from an earlier invocation fails even when the scenario pack is unchanged.
- `not_applicable` requires a valid `policyExceptionId`; `unsupported` is not a valid status.
- Actual observations are present even when they later mismatch. A pass/fail boolean without the values is insufficient.
- Every required scenario appears exactly once. Missing, duplicate, unexpected, or skipped scenarios fail closed.
- Fact and assertion coverage is derived centrally from the validated action plus predicates over the normalized observation. A runner-authored fact ID cannot grant coverage.
- Multiple required execution instances may share a participant ID. Receipts are unique by `participant.id` plus `executionInstanceId`; scenario IDs remain unique within each receipt. CXX requires both `windows-msvc` and `windows-clang-cl` globally, while an instance-scoped native job validates only its named instance.
- Paths are fixture-root-relative with `/` separators. Receipts contain no machine-specific temporary roots, credentials, user paths, or volatile timestamps.
- Domain errors are normalized as stable kind/token plus structured fields. Language exception classes, CXX envelope mechanics, and Python/Node naming conventions stay in adapter diagnostics rather than the common observation.
- Display Content records line severity and ordered segments using the frozen binding carrier: every segment contains `kind`, `text`, `path`, and `count`; unused fields remain present with their specified empty/zero values, and Label/Name payloads travel through `text`. Frontend styling is not part of the semantic adapter receipt.
- JUnit may accompany a receipt as command-execution evidence and cannot replace normalized observations. A participant profile may require it; CXX does, and its validator receives the absolute JUnit path through `--junit`.

Receipts are written atomically beneath `tools/binding_compliance/artifacts/<participant>/<execution-instance>/<invocation-id>/`. They are uploaded by CI with `if: always()` for diagnosis and remain untracked.

## Normalization and exact comparison

The family normalizer converts public adapter values into the schema-owned observation without reinterpreting business rules. It may:

- convert enum representations to their stable Vocabulary Token;
- make declared fixture paths root-relative and normalize separators;
- project language-native option/result/envelope mechanics into the declared structured field;
- sort only collections named by `unorderedPaths` using a schema-defined stable key;
- omit only paths named by `excludedPaths`;
- record durable files by relative path, byte length, and SHA-256 where byte identity is contractual;
- record ordered events after the public observer serialization point.

It may not:

- derive a missing fact from another field;
- translate adapter-local prose back into a domain state;
- accept aliases not declared by the contract;
- drop unknown fields or variants;
- substitute Rust output for an expected value;
- coerce consumer layout into semantic equality.

After normalization, object keys and values compare exactly. Arrays compare in order unless their exact JSON path is declared unordered. Extra fields, missing fields, type differences, unexpected variants, and additional durable side effects are mismatches.

## Applicability and coverage derivation

### Capability mapping

The coverage engine starts from each scenario's canonical Rust capability and expands it through current source-derived parity artifacts:

1. Resolve the canonical Rust crate and symbol set.
2. Select the CXX, Node, and Python parity rows mapped to those symbols.
3. Include returned/input DTOs, fields, enum variants, and accessors that the public operation exposes through the declared observation families.
4. Require a completed, matching receipt for every applicable semantic adapter.
5. Derive observed fact IDs by evaluating family-owned predicates over the validated action and normalized observation, then credit only rows associated with predicates that passed. The receipt cannot self-attest coverage.

Node and Python baselines already carry Rust crate/symbol metadata. The CXX parity artifact must be enriched with canonical `ownerModule`, `rustCrate`, and `coreRustSymbol` metadata rather than claiming that a bridge declaration alone is the core mapping. Mechanically derived counts, identifiers, and hashes are generated diagnostics, never hand-maintained evidence.

Every tracked row must end in exactly one honest evidence classification:

- runtime-verifiable through one or more executed capability scenarios;
- irreducibly structural or negative through a named retained analyzer; or
- excluded by a documented parity-policy exception.

There is no `mapped_only`, unclassified, or manual-acknowledgement success bucket. Existing Node binding-only and Python binding-only rows remain explicitly classified; they are not silently relabeled as matched Rust capabilities.

### New-row rule

A new source-derived parity row fails the compliance gate until the same change does one of the following:

- maps it to a scenario that executes on every applicable adapter;
- adds a new scenario and receipts for every applicable adapter; or
- classifies a genuinely declaration-only, erased-type, or negative row under a named retained analyzer that proves the relevant property; or
- adds a reviewed policy exception because the public capability is intentionally inapplicable.

The structural option is not a fallback for behavior that can be observed through a public operation, and a policy exception is not a substitute for valid structural evidence.

Migration status cannot waive this rule for new API work. The one-tier parity policy remains in force throughout the migration.

## CXX and CLI test-host design

### Target boundary

Add a test-only executable target named `classic-cxx-conformance` in `classic-cli/CMakeLists.txt` and register one stable CTest test with the same name.

The target must:

- link `classic_cxx_bridge` and only test serialization/support dependencies;
- use the generated CXX declarations and traverse returned CXX DTOs and observer events in C++;
- consume the input-only run plan;
- emit actual CXX observations rather than ask Rust to serialize them;
- remain uninstalled and unpackaged;
- avoid `classic-cli`, `src/scan_run_cli.cpp`, `src/scanner.cpp`, Qt, and other frontend sources;
- leave the production CLI command surface and behavior unchanged.

The registered test must also remain safe under the ordinary full `build_cli.ps1 -Test` suite. When either required conformance environment variable is absent, it returns the code configured through CTest's `SKIP_RETURN_CODE`, writes no receipt, and reports a visible skip. Only an exact-name run with a current run plan may grant conformance evidence; the receipt validator treats a missing receipt as failure whenever that execution was required.

Use test-only environment variables with absolute paths:

- `CLASSIC_CONFORMANCE_RUN_PLAN` — materialized input-only JSON;
- `CLASSIC_CONFORMANCE_OUTPUT` — receipt destination.

Add a private adapter launcher at `tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1`. It accepts `-Compiler msvc|clang-cl`, asks the engine to prepare a fresh invocation, and creates this layout:

```text
tools/binding_compliance/artifacts/cxx/
  windows-<compiler>/
    <invocation-id>/
      run_plan.json
      receipt.json
      ctest.junit.xml
      attempt.json
      stdout.log
      stderr.log
      binding_compliance_report.json
      binding_compliance_report.md
```

`attempt.json` records the invocation/source identity, exact approved wrapper command, compiler, exit code, timeout flag, whether a receipt and JUnit file were produced, and the absolute paths and SHA-256 hashes of captured `stdout.log` and `stderr.log`. It is execution diagnostics, not semantic evidence. The validator uses the captured output to distinguish local toolchain/environment failures from adapter command failures.

The launcher owns a 15-minute timeout for this incremental exact-name invocation. Raise the CLI matrix job timeout from 90 to 120 minutes while keeping setup plus the existing full-suite step within their current 90-minute envelope; this reserves 30 minutes for conformance launch, validation, and artifact finalization. The launcher starts the wrapper as a child process with redirected output, waits only for its bound, and terminates the entire child process tree on expiry before finalizing `attempt.json`. It must invoke receipt validation in a `finally` path after success, nonzero exit, or launcher timeout, passing `--attempt` and `--junit` so the report can distinguish command, timeout, toolchain, missing-JUnit, and missing-receipt failures. A job-level or runner-level cancellation outside the launcher's control remains a missing CI job rather than a fabricated conformance report.

Inside that launcher, the only permitted native test invocation has this argument order (`-CTestArgs` must be last for correct `pwsh -File` array binding):

```powershell
$env:CLASSIC_CONFORMANCE_RUN_PLAN = $runPlanPath
$env:CLASSIC_CONFORMANCE_OUTPUT = $receiptPath
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 `
    -Test `
    -CTestName classic-cxx-conformance `
    -Compiler $compiler `
    -CTestArgs @("--output-junit", $junitPath)
```

The launcher's always-run validation step has this contract:

```powershell
python tools/binding_compliance/check_compliance.py `
    --repo-root . `
    --profile conformance `
    --participant cxx `
    --execution-instance "windows-$compiler" `
    --receipt $receiptPath `
    --junit $junitPath `
    --attempt $attemptPath `
    --output-dir $invocationDir
```

The conformance engine materializes the run plan and binds all paths before the wrapper starts. Every path is absolute because the wrapper changes its working directory before invoking CTest, and every invocation directory is new so stale outputs cannot satisfy the gate. No specification or implementation instruction may invoke raw `ctest` or the test executable. The wrapper's discovery guard must find exactly the dedicated test. Selective mode intentionally skips the CLI integration script.

### First-pack CXX observations

Crash Log Scan Run CXX v1 must record:

- Run Status;
- discovery source, accepted/rejected paths and reasons, and stable discovery order;
- setup results;
- effective concurrency;
- Installed YAML Data identities, provenance, diagnostics, Local Ignore state, recovery data, and reset receipt;
- per-log disposition and every structured failure's stage, message, and path, plus artifact paths;
- serialized events and observer-delivery failure;
- Display Content severity and ordered frozen `kind + text + path + count` segments, including empty unused fields;
- durable report and backup identity where the scenario contracts bytes.

The pack includes Standard, Targeted, existing/generated/malformed/repaired Local Ignore, both recovery decisions, replay, abandonment, the pre-discovery, post-discovery queued, and admitted/durable cancellation seams, the pre-reset and post-critical reset cancellation boundaries, reset conflict/operational/durability outcomes, observer failure, and five deterministic public structured-failure scenarios. Request validation, discovery, and intake produce typed infrastructure observations; report persistence and Unsolved Logs finalization preserve ordered per-log failures, failed disposition, movement outcome, and observed artifact types. A failure mapping that cannot safely be triggered through the public CXX seam is classified under `scan-run-structured-failure-internal-faults` rather than as a CXX semantic receipt. It cannot grant CXX runtime coverage, and its existing focused test cannot be deleted or relabeled unless a deterministic public scenario later replaces it.

### CXX CI placement

Keep the current Python-only `cxx-parity-gate` job source-only. Raise the existing `cli-tests` matrix job timeout to 120 minutes, preserving its current setup/full-suite 90-minute envelope. In each matrix leg, run the full CLI wrapper suite first, then invoke `run_cxx_conformance.ps1 -Compiler ${{ matrix.compiler }}`. The launcher performs the exact selected wrapper run and its instance-scoped validation after success, nonzero exit, or its own timeout. The second wrapper invocation reconfigures and invokes the build command but must reuse the existing build directory and caches, so it is incremental rather than a second cold native build. Do not create another native job and do not add Qt.

Upload one GitHub artifact bundle named `cxx-conformance-${{ matrix.compiler }}` with `if: always()`. Matrix jobs have isolated workspaces, so the on-disk paths remain stable:

- `tools/binding_compliance/artifacts/cxx/windows-${{ matrix.compiler }}/**/receipt.json`;
- `tools/binding_compliance/artifacts/cxx/windows-${{ matrix.compiler }}/**/ctest.junit.xml`;
- `tools/binding_compliance/artifacts/cxx/windows-${{ matrix.compiler }}/**/attempt.json`;
- `tools/binding_compliance/artifacts/cxx/windows-${{ matrix.compiler }}/**/stdout.log` and `stderr.log`;
- `tools/binding_compliance/artifacts/cxx/windows-${{ matrix.compiler }}/**/binding_compliance_report.json` and `.md` execution-instance-slice reports;
- `classic-cli/build*/Testing/` diagnostics.

The report must distinguish missing or malformed receipt, nonzero wrapper exit, timeout, missing JUnit, toolchain/environment failure, and semantic mismatch.

## Consumer participants

CLI, GUI, and TUI use the same scenario identities but declare consumer obligations rather than semantic adapter coverage. Examples include:

- every Rust-owned Display Content line reaches the intended presentation path in order;
- typed path and count segments remain typed until the frontend applies layout;
- CLI stream and exit-code routing matches the declared obligation;
- GUI links, worker-to-GUI dispatch, recovery interaction, and model updates remain correct;
- TUI ordering, styling categories, recovery interaction, and cancellation behavior remain correct;
- no consumer recomposes Rust-owned wording.

Consumer expectations are keyed by stable obligation profile, not by copied adapter output. Legitimate layout differences are explicit obligations. A consumer receipt cannot grant semantic binding coverage, and a CXX bridge receipt cannot grant CLI presentation coverage.

The CLI consumer continues through `classic-cli/build_cli.ps1 -Test`, GUI through `classic-gui/build_gui.ps1 -Test`, and TUI through its Cargo test surface. Production frontends gain no conformance-only public interface.

## Failure taxonomy

The combined report uses stable failure kinds:

| Failure kind | Meaning |
| --- | --- |
| `local_environment_failure` | Required executable, SDK, venv, toolchain, or test dependency is unavailable |
| `adapter_command_failure` | Native command ran and failed or timed out before producing a valid receipt |
| `missing_execution_receipt` | A required participant, execution instance, or scenario did not produce evidence |
| `malformed_execution_receipt` | Receipt schema, duplicate IDs, unknown IDs, or value types are invalid |
| `stale_execution_receipt` | Schema, family version, expectation digest, invocation, run plan, or source identity differs from the current launch |
| `applicability_violation` | Required execution was skipped/unsupported or a policy exception is invalid |
| `coverage_mapping_gap` | A parity row has no executable, structural, negative, or exception classification |
| `normalization_failure` | Adapter output cannot be projected without inventing or discarding semantics |
| `semantic_conformance_mismatch` | Valid normalized actual observation differs from the independent expectation |
| `structural_contract_drift` | Source, declaration, stub, or parity inventory differs from its contract |
| `negative_contract_violation` | Forbidden export or duplicated ownership/presentation logic is present |

Reports preserve adapter stdout/stderr and concrete test/JUnit artifact locations as diagnostics, but messages and paths do not become coverage.

## Migration ledger and ratchet

During migration, generate a ledger that maps each current evidence item to its intended replacement. The ledger is diagnostic and cannot satisfy a gate. Each row records:

- stable obligation ID;
- current artifact/check and participant;
- replacement family, scenario, observation/assertion, and evidence role;
- retained structural or negative companion check, if any;
- state: `shadow`, `equivalent`, `blocking`, or `retired`;
- objective evidence for the state transition.

A row can enter `equivalent` only when old and new evidence run in the same CI period and the new path proves equal or stronger facts. It can enter `blocking` only when a missing, stale, malformed, or mismatching receipt fails the applicable workflow. It can enter `retired` only in the change that deletes the redundant old evidence. A ledger label alone never proves a transition.

### Phase 0 — Freeze and classify current evidence

Deliverables:

- Generate the initial migration ledger from CXX, Node, and Python parity rows; Node/Python runtime registries; the Crash Log Scan Run manifest; and consumer/source audits.
- Classify every obligation as runtime-verifiable, structural/negative, or policy-excepted.
- Record the existing Node binding-only, Python binding-only, and `classic-resource-core` CXX exception honestly.
- Add mutation tests proving that a new row, missing participant or execution instance, stale receipt, changed observation, and a Rust-only behavior change fail without altering the independent expectation.

Exit gate:

- Every current evidence item has one target disposition, but no existing gate has been weakened or removed.

### Phase 1 — Build the generic engine in shadow mode

Deliverables:

- Add JSON Schemas, pack discovery, input-only materialization, canonical digesting, receipt validation, exact comparison, applicability, coverage mapping, failure taxonomy, and combined reporting.
- Add Python tooling tests under `tools/binding_compliance/tests/`. Any new Rust unit tests use the repository-required sibling test files.
- Add `--profile conformance` with required `--participant`, optional single-instance `--execution-instance`, repeatable `--receipt`, and companion `--attempt`/`--junit` arguments for native-job validation. Extend `full` to orchestrate or aggregate all available participants without making absent shadow receipts blocking.
- Enrich CXX parity metadata with canonical Rust owner/core-symbol mapping.

Exit gate:

- Tooling tests cover malformed/stale/missing/duplicate receipts, exact comparison, normalization declarations, applicability exceptions, row mapping, and deterministic reports.
- The current canonical compliance command remains green and reports shadow results separately from blocking requirements.

### Phase 2 — Crash Log Scan Run vertical slice

Deliverables:

- Add a versioned scenario pack alongside the current manifest's copied acknowledgements and source markers, retaining its fixture inputs and explicit expected outcomes until the later blocking/deletion gate.
- Make Rust, CXX, Node, and Python emit the same normalized observation families for every publicly executable scenario. Keep unreachable internal fault-mapping rows explicitly classified under retained analyzers rather than misreporting them as CXX runtime coverage.
- Add the dedicated CXX target and run it through the CLI wrapper on MSVC and clang-cl.
- Add CLI, GUI, and TUI consumer receipts for their presentation obligations.
- Dual-run all existing scan-run evidence and the new receipts.

Equivalence gate:

- Every publicly executable required scenario produces Rust, Node, Python, MSVC CXX, and clang-cl CXX execution receipts plus the applicable consumer receipts. These roll up to four semantic participants; retained internal-only fault mappings appear separately and grant no semantic-adapter coverage.
- Observed variant sets equal the source-derived inventory.
- Run Status, discovery, setup, Installed YAML Data, per-log outcomes, ordered events, Display Content, durable artifacts, recovery, reset, all five named cancellation boundaries, replay, abandonment, observer failure, and publicly reachable structured failures have equal or stronger executable coverage.
- Fault injection that remains internal is explicitly retained and cannot be counted as public CXX execution.

Blocking and deletion gate:

- Missing/skipped adapter execution, a changed adapter value, a new Rust variant, a stale digest, or an invalid exception fails CI.
- Only then delete `adapters.*.acknowledgedVariants`, `adapters.*.evidence[].contains`, scenario/presentation `requiredOwners` and `evidence`, and corresponding positive marker-validation code.
- Retain fixture inputs/expectations, Rust enum inventory derivation, reset/failure fixture validation, and forbidden-export audits.

### Phase 3 — User Settings

Deliverables:

- Convert `tests/fixtures/user_settings_compatibility/` into the second pack without duplicating its expected values.
- Exercise read-only open, typed settings/frontends, bootstrap preview/commit, update preview/commit, migration planning/reversal/application, invalid values, stale revisions, byte preservation, and ownership boundaries across applicable adapters.
- Add consumer obligations only where a maintained frontend consumes the capability.

Exit gate:

- The shared corpus drives all applicable adapters through input-only run plans.
- Source ownership remains exclusively enforced by `tools/user_settings_ownership/check.py` or its retained analyzer wrapper.
- Registry rows for migrated User Settings capabilities can no longer grant coverage without executed receipts.

### Phase 4 — Existing fixture-backed domains

Migrate domains that already have strong deterministic inputs and focused tests before inventing new fixture infrastructure:

- focused semantic analyzers and FormID lookup;
- Installed YAML Data operations not already covered by the scan-run pack;
- Autoscan Report byte goldens;
- Vocabulary and positive Display Content transport cases;
- deterministic config, file, path, message, database, version-registry, and scan-game operations with existing fixtures.

Exit gate for each pack:

- It independently reaches blocking status before its registry entries or positive duplicate assertions are deleted.
- Canonical owner goldens and negative ownership audits remain.

### Phase 5 — Remaining owner modules

Add hermetic packs for the remaining runtime-verifiable parity surface, including aux, perf, registry, settings, shared, update, web, XSE, version, and any other current owner-module rows not covered earlier. Live network, registry, or installed-game state must be replaced with controlled local servers, temporary/test-owned registry locations, injected deterministic inputs, or retained structural evidence where runtime behavior is not honestly observable through the public seam.

Exit gate:

- Every current parity row is runtime-proven, irreducibly structural/negative, or policy-excepted.
- Every applicable participant is required; no owner-module smoke enrollment or `mapped_only` success remains.

### Phase 6 — Registry and migration cleanup

Deliverables:

- Remove Node and Python runtime-registry entries, selector counts/hashes, test names, and `runtime_verified` claims surface by surface. Shared registry loaders remain until every loader-backed surface is blocking on receipts, then are deleted with their final consumers.
- Remove generated runtime-coverage summaries whose only input was those claims, or regenerate equivalent summaries exclusively from executed receipts.
- Remove the temporary migration ledger after every row is `retired` or represented by a permanent retained analyzer/policy exception.
- Make the deep module's report and commands canonical in CI and contributor/API documentation.
- Retain focused lower-level parser and native test commands as diagnostics where they add leverage.

Final exit gate:

- Repository search finds no `acknowledgedVariants`, scenario/presentation positive evidence markers, registry-driven test activation, or human-authored `runtime_verified` claim for migrated surfaces.
- Adding a shared scenario changes its pack once and automatically obligates every applicable adapter without editing per-adapter evidence lists.

## Deletion and retention matrix

| Current evidence | Final disposition | Required replacement before deletion |
| --- | --- | --- |
| Crash Log Scan Run `acknowledgedVariants` copies | Delete | Source-derived variants plus passing observed-variant receipts from all four adapters |
| Adapter/scenario/presentation `evidence.contains` markers | Delete | Receipts from actually executed semantic/consumer tests, missing receipt fails closed |
| Shared scan-run fixtures and explicit expected outcomes | Retain and reshape as pack | Remain the independent oracle; never generated from Rust |
| Node/Python runtime registry claims and test pointers | Delete surface by surface | Every selected parity row tied to an executed matching receipt |
| Selector counts and hashes | Generate only | Derived from current source mappings and receipts |
| CXX source parity gate/baseline | Retain | Continues to catch source/ABI/export drift alongside runtime receipts |
| Node/Python source parity contracts | Retain | Continue to catch public surface/signature drift |
| Node declarations and TypeScript negative type tests | Retain | Runtime cannot prove erased types |
| Python stubs/type validation | Retain | Runtime cannot prove annotation/type surface |
| Forbidden-export audit and runtime namespace probes | Retain narrowly | Source/declaration scans prove unused or hidden API absence; loadable bindings also prove removed names are not generated or re-exported at runtime |
| Rust Vocabulary owner conformance | Retain | Canonical token/label ownership invariant |
| Positive per-adapter label/segment mapping copies | Delete when covered | Predicate-derived receipt coverage exercises every source-derived token, segment kind, severity, unknown behavior, and the exact `kind + text + path + count` carrier including empty unused fields |
| Negative Vocabulary/Display Content ownership audits | Retain narrowly | Runtime equality cannot detect newly copied policy/prose |
| Core presentation wording goldens | Retain once | Rust owner pins Display Content; adapters prove lossless transport |
| Internal Rust fault-injection tests | Retain where public execution is unsafe | Cannot be relabeled as public adapter execution |

## CI topology

The adapter-native workflow produces the receipt before the compliance command validates it:

```text
tracked scenario pack
        |
        v
input-only run plan ---> native adapter/consumer test ---> actual receipt + JUnit/log
        |                                                   |
        +---------------- expected oracle ------------------+
                                                            v
                                      binding compliance validation/report
```

Required workflow placement:

- Rust receipts: the existing Rust workspace test workflow.
- CXX receipts: the existing `ci-cpp.yml` CLI test matrix for MSVC and clang-cl, through `build_cli.ps1` only.
- Node receipts: the existing Bun/Node runtime workflow after the native package is built.
- Python receipts: the existing Python binding workflow after `uv sync --inexact` and `rebuild_rust.ps1 -Target python`.
- CLI consumer receipts: the CLI wrapper test/integration workflow.
- GUI consumer receipts: the GUI wrapper test workflow; never raw CTest.
- TUI consumer receipts: the existing Cargo test workflow.

Source-only jobs continue to run fast structural gates. A native receipt is validated in the job that has the real runtime/toolchain; source-only success cannot satisfy a runtime requirement. The `full` local profile may invoke the native commands in their repository-approved order, but a receipt-only validation path must also exist so CI does not rebuild an adapter twice.

Receipt validation has an explicit scope. `--profile conformance --participant <id> --execution-instance <id>` requires every scenario applicable to that one instance and may report only an instance-slice pass. Omitting `--execution-instance` requires all instances applicable to the participant and may report only a participant-slice pass. Neither can claim repository-wide conformance. `--profile full` requires every applicable semantic adapter, execution instance, and consumer and is the only single-process report allowed to claim complete conformance.

CI does not move raw observations into a later cross-workflow comparison job. Every participant compares independently with the same tracked oracle in its native job. Repository-wide CI success is the conjunction of required participant jobs for the same source revision, and a retained static workflow audit verifies that every applicable participant/profile remains registered as blocking. Deleting, skipping, or weakening one participant job therefore fails CI policy even though another job cannot see its receipt. Same-revision participant artifacts provide the dual-run evidence used to advance a migration ledger row.

## Verification commands

Commands are run from the repository root unless a working directory is stated. The new `conformance`, `participant`, `execution-instance`, receipt, JUnit, and attempt arguments shown here are part of the implementation contract; adapter-specific launchers may add private diagnostic options without changing them.

Tooling and source compliance:

```powershell
uv sync --project python-bindings --inexact
uv run --project python-bindings python -m pytest tools/binding_compliance/tests -q
python tools/binding_compliance/check_compliance.py --repo-root . --profile ci
python tools/cxx_api_parity/check_parity_gate.py --repo-root .
python tools/node_api_parity/check_parity_gate.py --repo-root .
python tools/python_api_parity/check_parity_gate.py --repo-root .
```

CXX conformance uses its private adapter launcher, which may invoke native tests only through the approved CLI wrapper. Frontend validation continues to use the repository wrappers:

```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -Compiler msvc
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -Compiler clang-cl
pwsh -ExecutionPolicy Bypass -File tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Compiler msvc
pwsh -ExecutionPolicy Bypass -File tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Compiler clang-cl
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
```

The CXX launcher prepares the absolute run-plan/output paths and always performs the instance-scoped validation described in [CXX and CLI test-host design](#cxx-and-cli-test-host-design). Invoking the registered CTest without that launcher-provided state only produces a visible skip and grants no evidence.

Node runtime validation, from `node-bindings/classic-node/`:

```powershell
bun run parity:gate:ci
bun run test:types
bun run test:bun
bun run test:node
```

Python runtime validation follows the repository-owned environment sequence:

```powershell
uv sync --project python-bindings --inexact
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python
uv run --project python-bindings python validate_stubs.py `
    --rust-dir . `
    --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json `
    --json-out python-bindings/parity-artifacts/stub_validation_report.json `
    --fail-on-warnings
uv run --project python-bindings python -m pytest python-bindings/tests -q
```

Focused Rust pack tests run through their owning Cargo packages. Workspace-wide Cargo commands that touch PyO3 set `PYO3_PYTHON` first as required by repository policy.

## Completion criteria

The architecture is complete only when all of the following are true:

1. Every runtime-verifiable CXX, Node, and Python parity row has a passing executed receipt, Rust passes the same applicable semantic scenarios, and both required CXX execution instances pass.
2. Every non-runtime row has one named retained structural/negative analyzer or documented policy exception; there is no manual third bucket.
3. Crash Log Scan Run has four-adapter executable coverage for every agreed observation family, both CXX toolchain instances, and separate executable CLI/GUI/TUI consumer coverage.
4. CXX executes through the approved CLI wrapper in the Windows MSVC and clang-cl matrix; source parity alone cannot satisfy runtime coverage.
5. Mutation tests prove that a new public row, new enum variant, missing participant, skipped scenario, stale receipt, changed adapter observation, and extra observation fail closed; changing Rust output alone cannot rewrite the tracked expectation and therefore fails comparison.
6. Structural surface gates, declaration/stub checks, type-level negatives, forbidden exports, Vocabulary owner invariants, and negative Display Content ownership audits remain green without reduced scope.
7. The redundant acknowledgement, marker, and registry evidence listed in the migration ledger is deleted only after its replacement becomes blocking.
8. Adding one scenario or observation changes the shared pack once and automatically obligates every applicable adapter.
9. Current API and contributor documentation names the new canonical commands only after their implementation is blocking.
10. The final report clearly separates structural drift, missing execution, stale/malformed evidence, applicability, coverage, normalization, semantic mismatch, native command failure, and local environment failure.

## Documentation updates by phase

Do not update current API pages to claim executable coverage before it is blocking. Update them in the implementation changes that make each claim true:

- `docs/api/binding-compliance-suite.md` — profiles, receipts, failure kinds, and removal of the CXX runtime gap.
- `docs/api/binding-parity-overview.md` — capability/scenario coverage and participant roles.
- `docs/api/binding-parity-policy.md` — same-change executable obligation and narrow applicability exceptions.
- `docs/api/cxx-parity-gate.md` — distinction between bridge source parity and native CXX semantic conformance.
- Affected domain API pages — scenario-owned behavior and any contract-shaping observation changes.
- CI and contributor command references — only after the corresponding profile is blocking.

This specification introduces tooling terminology, not a new CLASSIC domain concept, so it does not add a glossary entry to `CONTEXT.md`.
