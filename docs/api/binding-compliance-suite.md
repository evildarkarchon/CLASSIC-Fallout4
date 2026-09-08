# Binding Compliance Suite

Migrated fixture-backed selector hashes, test pointers, and positive registry
claims are retired after blocking pack promotion. Mixed selectors retain explicit
unmigrated IDs; metadata readers and focused diagnostics remain. Metadata summaries
distinguish receipt obligations from residual legacy claims. Only authenticated
executed receipts contribute migrated runtime coverage. See the
[issue #211 retirement evidence map](../implementation/fixture_evidence_retirement.md)
for exact deletions and retained boundaries.

Node and Python smoke tests now register independently of registry claims; the
binding-local activation loaders are removed. The remaining JSON metadata and
diagnostic ledger are retained because 1,657 runtime-classified source rows still
lack executable predicates. See [retirement readiness](../implementation/binding_compliance/retirement_readiness.md).
Metadata labels are not runtime proof.

The binding compliance suite is the canonical binding gate for day-to-day validation and CI policy. It maps the documented binding parity policy into explicit executable requirements, then records which lower-level gate or static check proves each requirement.

Run the source-level CI profile from the repo root:

```powershell
python tools/binding_compliance/check_compliance.py --repo-root . --profile ci
```

The command writes:

- `tools/binding_compliance/artifacts/binding_compliance_report.json` - structured output grouped by surface and requirement.
- `tools/binding_compliance/artifacts/binding_compliance_report.md` - human-readable summary with failing checks and known gaps.

## Profiles

| Profile | Purpose |
| --- | --- |
| `ci` | Canonical source-level umbrella check. Runs the C++ parity gate, Node parity/runtime-coverage gate, Python parity/runtime-coverage gate, Python stub validation, the User Settings ownership audit, the Crash Log Scan Run contract-variant check, the diagnostic evidence-migration ledger check, and static policy/artifact/docs checks. |
| `cxx-ci` | CI slice for the Windows C++ workflow. Runs the canonical suite around the CXX parity gate and shared static policy checks. |
| `node-ci` | CI slice for the Node workflow. Runs the canonical suite around Node parity and `index.d.ts` freshness checks. |
| `python-ci` | CI slice for the Python workflow. Runs the canonical suite around Python parity, stub validation, uv drift-guard setup, and the schema-version guard. |
| `conformance` | Receipt-only native-job validation for one participant or execution instance. Requires `--participant` and repeatable `--receipt`; CXX also requires companion `--attempt` and `--junit` diagnostics. |
| `full` | Repository backstop. Adds Bun/Node runtime tests, the Python PyO3 rebuild, and Python smoke tests. Repeatable `--receipt` inputs must cover every tracked family and applicable execution instance. Every source parity row needs executed evidence or a named retained analyzer/policy exception. Missing receipts, unresolved rows, or skipped retained gates fail. |
| `static` | Policy, docs, and artifact checks; command-backed requirements still run unless `--skip-commands` is supplied. It makes no repository conformance claim. |

Use `--skip-commands` when reviewing policy mapping without invoking lower-level gates.
Only a complete `full` run can set the suite summary's `repository_complete` to
true. `ci` and participant slices validate their narrower scopes. Full aggregation
currently reports the unresolved migration obligations rather than certifying
the repository. A single family's receipts cannot complete it:

```powershell
python tools/binding_compliance/check_compliance.py --repo-root . --profile full --receipt <first-receipt> --receipt <next-receipt>
```

Pass every family and instance's receipt, with its sibling immutable plan. The
`conformance` section lists missing families, uncovered rows, retained analyzer
owners, and centrally validated family reports. Adding a shared scenario changes
the adapter denominator automatically. The workflow audit independently derives
required family/participant/compiler combinations from the tracked packs and
source mappings, rejecting omitted CI policies.

Native launchers validate one exact instance with this receipt-only shape:

```powershell
python tools/binding_compliance/check_compliance.py `
  --repo-root . `
  --profile conformance `
  --participant cxx `
  --execution-instance windows-msvc `
  --receipt tools/binding_compliance/artifacts/cxx/windows-msvc/<invocation>/receipt.json `
  --attempt tools/binding_compliance/artifacts/cxx/windows-msvc/<invocation>/attempt.json `
  --junit tools/binding_compliance/artifacts/cxx/windows-msvc/<invocation>/ctest.junit.xml
```

The receipt must have a sibling immutable `run_plan.json`. The engine rebinds it to the current tracked pack and source revision before validation. Attempt and JUnit files can add command diagnostics but cannot supply semantic facts, row coverage, or a broader scope claim. Participant reports require every source-derived execution instance; only `full` can claim repository completeness, and missing row coverage or unresolved consumer obligations fails that claim closed. Full aggregation independently authenticates each participant-specific source digest and requires their embedded Git revisions to match; the digests themselves may differ because each run plan declares its own runner source roots.

The Crash Log Scan Run pack also has private blocking launchers for its
Rust, Node, Python, and native CXX semantic adapters, plus separate CLI, GUI,
and TUI consumer participants:

```powershell
python tools/binding_compliance/run_scan_run_conformance.py --participant rust
python tools/binding_compliance/run_scan_run_conformance.py --participant node
uv run --project python-bindings python tools/binding_compliance/run_scan_run_conformance.py --participant python
pwsh -ExecutionPolicy Bypass -File tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Compiler msvc
pwsh -ExecutionPolicy Bypass -File tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Compiler clang-cl
pwsh -ExecutionPolicy Bypass -File tools/binding_compliance/conformance/adapters/run_cli_consumer_conformance.ps1 -Compiler msvc
pwsh -ExecutionPolicy Bypass -File tools/binding_compliance/conformance/adapters/run_gui_consumer_conformance.ps1 -Compiler msvc
python tools/binding_compliance/run_scan_run_consumer_conformance.py --participant tui
```

Each invocation creates a fresh input-only `run_plan.json` and calls only the
selected adapter's public scan-run seam. Rust, Node, and Python publish
`receipt.json`, `attempt.json`, and `conformance_report.json` beneath
`tools/binding_compliance/artifacts/<participant>/<instance>/<invocation>/`.
The CXX launcher hosts its bridge-only target through the approved CLI wrapper,
uses a 15-minute child-process bound, and publishes `receipt.json`, mandatory
`ctest.junit.xml`, `attempt.json`, separate `stdout.log`/`stderr.log`, and the
instance-scoped JSON/Markdown compliance reports beneath
`tools/binding_compliance/artifacts/cxx/windows-<compiler>/<invocation>/`.
Ordinary full CLI wrapper runs visibly skip that target when no current plan and
receipt destination are supplied. The native workflows run every promoted
launcher with `!cancelled()` and upload its diagnostics with `always()`, so a
retained-gate failure does not suppress replacement evidence and a replacement
failure still fails the job. Retained fixture, source-inventory, negative-export,
parity, declaration/stub, rebuild, and runtime gates remain blocking. Both `windows-msvc` and
`windows-clang-cl` receipts are required
before CXX completes its participant denominator; three Rust/Node/Python
receipts alone remain incomplete.

The source-owned catalog at `tests/conformance/consumer-obligations.json`
independently selects frontend obligations and expectations. Consumer plans
withhold those expectations, and validated observations appear only under
`consumerCoverage`: they never grant semantic parity-row coverage. Consumer
jobs are blocking for this family, while their artifacts remain available even
when execution or validation fails.

## Autoscan Report Blocking Execution

`tests/conformance/packs/autoscan_report/v1.json` selects the original empty,
populated, and FCX golden cases. The central validator reads their immutable
expected Markdown; adapters receive only inputs and return actual persisted
bytes, digest, length, typed Display Content, and durable effects. Neither
adapter output nor a generated replacement oracle can establish expectations.

```powershell
python tools/binding_compliance/run_scan_run_conformance.py --family autoscan-report --participant rust
python tools/binding_compliance/run_scan_run_conformance.py --family autoscan-report --participant node
uv run --project python-bindings python tools/binding_compliance/run_scan_run_conformance.py --family autoscan-report --participant python
pwsh -ExecutionPolicy Bypass -File tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Family autoscan-report -Compiler msvc
pwsh -ExecutionPolicy Bypass -File tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Family autoscan-report -Compiler clang-cl
```

Run each adapter's retained build prerequisites first. All three scenarios and
both CXX compiler instances require fresh same-revision receipts; missing or
failed evidence remains blocking alongside existing gates. Only FCX path
tokens expand on the expectation side; actual report bytes remain exact. The
[evidence map](../implementation/autoscan_report_conformance_equivalence.md)
records the original oracle, database fixture, source-preservation checks, and
retained owner diagnostics. Frontend transport and layout remain under their
existing consumer obligations.

## Installed YAML Data Blocking Execution

`tests/conformance/packs/installed_yaml_data/v1.json` owns fifteen public
inspection/preparation scenarios with input-only JSON fixtures. Every semantic
adapter runs the same cases, and CXX requires both compiler instances. The
[evidence map](../implementation/installed_yaml_data_conformance_equivalence.md)
records exact scope and retained tests, including scan-owned recovery facts.

```powershell
python tools/binding_compliance/run_semantic_conformance.py --family installed-yaml-data --participant rust --artifact-root tools/binding_compliance/artifacts/installed-yaml-data
python tools/binding_compliance/run_semantic_conformance.py --family installed-yaml-data --participant node --artifact-root tools/binding_compliance/artifacts/installed-yaml-data
uv run --project python-bindings python tools/binding_compliance/run_semantic_conformance.py --family installed-yaml-data --participant python --artifact-root tools/binding_compliance/artifacts/installed-yaml-data
pwsh -ExecutionPolicy Bypass -File tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Family installed-yaml-data -Compiler msvc -ArtifactRoot tools/binding_compliance/artifacts/installed-yaml-data
pwsh -ExecutionPolicy Bypass -File tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Family installed-yaml-data -Compiler clang-cl -ArtifactRoot tools/binding_compliance/artifacts/installed-yaml-data
```

Run the retained build prerequisites before invoking an adapter, including the
Python `uv sync --project python-bindings --inexact` and Rust extension rebuild.
The shared launcher requires a fresh authenticated plan and completed receipt
for every scenario. Source mappings for the migrated Node/Python entrypoints
delegate to `receipt_required`; registry claims cannot report them as executed.

## User Settings Blocking Execution

`tests/conformance/packs/user_settings/v1.json` selects opening and operation cases from
`tests/fixtures/user_settings_compatibility/expectations.json`. The existing
compatibility expectations are the single independent oracle: the central
engine resolves case references in memory and binds the oracle and input fixture
bytes into the expectation digest. Expected document fixtures also participate
in freshness checks and remain outside the adapter fixture map. Adapter plans
contain fixture placement, typed requests, field selectors, and caller commit
decisions, never expected observations.

The Rust, CXX, Node, and Python runners open their public User Settings seam in an
isolated temporary root and emit actual source metadata, commit eligibility,
diagnostic codes, selected typed settings, original-content/revision checks, and
whole-tree preservation observations. Exact central comparison rejects missing,
extra, mistyped, or changed observations. Cases cover canonical and missing
documents, legacy shape/location, alias precedence, invalid values, malformed
and future-major fallback, unknown entries, and GUI geometry.

Operation cases exercise bootstrap and update previews separately from caller
commit decisions, including declined and rejected requests, successful commits,
and stale revisions after a controlled external edit. Runners project actual
accepted fields and ordered diagnostics with field, code, and message. They
capture full directory trees and exact file bytes immediately after preview and
after the optional commit. Central comparison checks successful publication's
YAML semantics against independent oracle documents and verifies its returned
revision against the actual published bytes. Every other artifact remains
byte-exact, including external edits and the retained coordination lock. This
covers unknown entries, aliases, and untouched invalid settings without making
adapters owners of persistence or validation policy. Explicit legacy TUI import
retains its existing tests for a subsequent slice.

Migration cases extend the same compatibility oracle with current, missing,
supported flat and previous-location, alias-only/conflicting, malformed, older,
and future-major documents. Each runner calls its public planner twice and
reverses the plan twice before any write. The comparator authenticates the exact
original revision, deterministic proposals, inverse endpoints and ordered review
rows, and an unchanged installation tree. Proposed documents and YAML review
fragments compare against independently authored typed YAML; published bytes
must equal the exact approved proposal, and backups and restored content remain
byte-exact. Expected documents never enter adapter input plans.

Explicit apply/restore scenarios exercise declined approval, stale source and
destination revisions, dormant legacy-source conflicts, unavailable or tampered
backups, and an obstructed backup directory. Opaque applied receipts authorize
restoration; their paths and revisions are checked against complete durable tree
checkpoints. Operational outcomes retain stable core codes without adapter error
envelopes. A stale apply may leave one empty coordination lock in Rust/Python,
while CXX/Node reject during their approval preflight; this specific optional
empty file is normalized only for apply conflicts through scenario-owned
`optionalEmptyFiles` declarations naming each tree path, relative filename, and
rationale. No other tree entry is excluded. Internal publication fault injection remains in the retained core
tests; no public test API is introduced to reach internal durability failures.

```powershell
python -m pip install "ruamel.yaml>=0.18,<0.19"
uv sync --project python-bindings --inexact --group drift-guards
python tools/binding_compliance/run_user_settings_conformance.py --participant rust
python tools/binding_compliance/run_user_settings_conformance.py --participant node
uv run --project python-bindings python tools/binding_compliance/run_user_settings_conformance.py --participant python
pwsh -ExecutionPolicy Bypass -File tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Compiler msvc -Family user-settings
pwsh -ExecutionPolicy Bypass -File tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Compiler clang-cl -Family user-settings
```

Run these after the maintained native build prerequisites. The CXX launcher uses
the same bridge-only CTest target and approved CLI wrapper as scan conformance;
each compiler emits its own receipt and mandatory JUnit evidence. CI requires
successful execution and comparison and uploads diagnostics even after failure
under `tools/binding_compliance/artifacts/user-settings/`. Missing, skipped,
stale, malformed, or mismatching receipts fail the applicable native job.
Migrated settings rows require validated semantic receipts; registry enrollment
cannot grant their runtime coverage. Source parity, declarations, stubs, type
negatives, forbidden exports, and the Rust ownership audit remain blocking.

The Node and Python registries no longer contain owner-wide User Settings
selectors, selector hashes, or claims for migrated rows and identifiers.
Explicit retained contract IDs cover only the still-unmigrated accessors,
builders, defaults, and frontend/legacy-import semantics. Shared registry
loaders remain for those rows and other unmigrated owners. Migrated summary
rows omit legacy test pointers and prose claims; duplicate registry-only
identifiers cannot restore a runtime-verified classification.

The Rust launcher executes `compatibility_contract` and `open_conformance` in
one Cargo invocation, with both sources included in the invocation identity.
CI retains the existing native runtime suites at the same checkout as the new
receipts. The [equivalence map](../implementation/user_settings_conformance_equivalence.md)
records shared facts and focused evidence that must remain.

Maintained CLI, GUI, and TUI settings boundaries have separate obligations in
`tests/conformance/consumer-obligations.json`. Run the existing CLI/GUI consumer
launchers with `-Family user-settings`, or the TUI consumer launcher with
`--participant tui --family user-settings`. Each consumer emits current native
observations under `consumerCoverage`; it cannot satisfy semantic adapter rows.
Only maintained frontend actions are enrolled; an adapter's restore API does
not imply that every frontend has a restore action.

The GUI launcher accepts `-Preset` and forwards it to the approved build wrapper.
CI uses `-Preset ci-system-qt` for both its full GUI test run and its consumer
receipts, reusing the installed Qt package and build tree. Local runs can use
the same preset with `CMAKE_PREFIX_PATH` pointing to an MSVC Qt installation,
or keep the default vcpkg preset. Match the preceding build's preset; switching
toolchain strategies in an existing CMake cache requires a fresh configuration.

## What The Suite Proves

The suite does not replace lower-level parsers. It owns the top-level pass/fail result, policy mapping, and gap report while reusing existing gates as executable evidence:

- C++: `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`
- Node: `python tools/node_api_parity/check_parity_gate.py --repo-root .` plus `bun run dts:freshness:check` in the Node CI slice.
- Python: `python tools/python_api_parity/check_parity_gate.py --repo-root .` plus `validate_stubs.py`.
- User Settings ownership: `python tools/user_settings_ownership/check.py --repo-root .` rejects first-party production references that reintroduce flat models, generic User Settings variants/key policies, raw `CLASSIC_Settings` interpretation outside `classic-user-settings-core`, or runtime use of the generated default mirror.
- Crash Log Scan Run parity and contraction: `python tools/binding_compliance/scan_run_contract.py --repo-root .` validates the shared corpus under `tests/fixtures/crash_log_scan_run/` and compares its variant inventory with the Rust enums. The trusted variant policy maps every source-derived variant to a required executable scenario fact or a named retained analyzer. The inventory includes Installed YAML Data roles, provenance, diagnostic kinds, Local Ignore states, both explicit recovery decisions, resume-error kinds, and continuation/reset invariants in addition to lifecycle variants. The same manifest carries a per-surface forbidden-export inventory; the check fails if a removed orchestration, analysis-only execution, batch lifecycle, direct report-writing, resettable cancellation, or global-FCX name remains in public source, CXX parity data, Node declarations/parity/runtime coverage, or Python stubs/parity/runtime coverage. Blocking semantic and consumer receipts supply executable scenario and presentation coverage. Copied adapter acknowledgements, positive source markers, and per-scenario or presentation required-owner lists are retired.
- Evidence migration ledger: `python tools/binding_compliance/migration_ledger.py --repo-root .` fails closed when a tracked parity row, raw runtime-registry claim, retained Crash Log Scan Run audit, or current consumer/source audit is missing, duplicated, stale, or unclassified. The check is blocking in every source-level profile because inventory drift must be classified, but the ledger and its migration states are diagnostic only: they cannot grant compliance, runtime coverage, or receipts. Retired acknowledgement and positive-marker rows no longer belong to its active inventory. The named `scan-run-local-ignore-reset-internal-faults` analyzer keeps replacement-publication and durability-unknown projection tests blocking. The separate `scan-run-structured-failure-internal-faults` analyzer retains injected analysis, FormID database access, initialization, and internal-invariant projections that have no hermetic public cross-adapter trigger; it grants no semantic-adapter coverage. The C++, Node, Python, User Settings, and Crash Log Scan Run gates above remain the executable evidence owners.

Existing C++, Node, and Python parity gates remain available as focused debugging commands. Do not remove or weaken them unless the compliance suite demonstrably covers the same check and the replacement is documented in the same change.

## Current Coverage Gaps

The six focused families `crash-suspect`, `crashgen-settings`, `mod-guidance`,
`formid-lookup`, `named-record`, and `plugin-evidence` now also require blocking
receipts from Rust, Node, Python, and CXX on both MSVC and clang-cl. Launch one
with `python tools/binding_compliance/run_semantic_conformance.py --family
<family> --participant <rust|node|python>` after its native build, or use
`tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Family
<family> -Compiler <msvc|clang-cl>`. CI retains the existing runtime suites and
registry evidence and uploads each family's diagnostics separately. Successful
hits, misses, disabled lookup, empty findings, authored guidance, and structured
failures remain distinct typed observations. See the
[equivalence map](../implementation/semantic_conformance_equivalence.md) for
fixture ownership and retained evidence. These family slices make no new
frontend-consumer or full-repository completeness claim.

The suite reports known weak coverage instead of silently rewriting policy around it. The remaining gaps are:

- C++ has no editable runtime-coverage registry equivalent to the Node and Python registries. Crash Log Scan Run, User Settings, and the six focused semantic v1 packs close their family-specific gaps with executable CXX receipts on MSVC and clang-cl; other CXX domains still rely on their source-derived parity dispositions until their own packs migrate.
- The Crash Log Scan Run v1 report is blocking across Rust, Node, Python, both required CXX execution instances, and the separate CLI, GUI, and TUI consumer instances. Its copied acknowledgements and positive source-marker evidence have been retired. The fixture, source-inventory, negative-export, parity, declaration/stub, rebuild, runtime, and native wrapper gates remain blocking; other families have not inherited this retirement.
- Replacement-publication failure, replacement durability uncertainty, and the non-hermetic structured-failure injections remain blocking internal fault analyzers, not semantic receipts. A deterministic public scenario may replace that classification later; a test-only public binding hook or fabricated adapter receipt may not.
- Public enum values without a hermetic v1 scenario—such as no-log/setup terminal states, alternate Installed YAML candidate diagnostics, and custom Unsolved Logs movement—remain exact blocking dispositions under `scan-run-contract-validator`. They grant no semantic receipt credit; the variant policy prevents them, or any newly added value, from falling through to an unrelated happy-path fact.

Treat new drift, stale generated artifacts, stale baselines, missing runtime coverage, policy/source contradictions, tooling bugs, and local environment failures as separate failure classes in the structured report.

## Crash Log Scan Run Contract Changes

The `config-vocabulary` and `scan-run-vocabulary` v1 packs cover ten public
resolver selectors, including the CXX scanner provenance alias that shares the
config accessor in Node and Python. Source-owned tokens determine the complete
input inventory; expected wording remains independently authored in the packs.
Each adapter invokes the real public resolver for known and unknown inputs.
Use `run_semantic_conformance.py --family <family> --participant <adapter>` for
Rust, Node, and Python, and the approved CXX conformance wrapper with each
required compiler. The [Vocabulary and Display Content evidence map](../implementation/vocabulary_display_conformance_equivalence.md)
records validation, exact retirement scope, and the retained internal tests.

The scan-run pack also compares complete ordered Display Content: severity and
every segment's kind, text, path, and count, including inactive fields and the
count noun selected by Rust. Its current cases cover 84 lines, all five
severities, and five emitted segment kinds. The unproduced `Name` kind remains
an explicit retained disposition and grants no semantic receipt credit.

`tests/fixtures/crash_log_scan_run/manifest.json` is the machine-readable owner for normalized cross-interface expectations. Paths are compared relative to each runner's temporary root; processing timings and exact concurrent event interleavings are deliberately excluded. Discovery, Rust-selected effective concurrency, serialized event variants, discovery-order outcomes, structured failures, Installed YAML Data and reset metadata, valid/generated/malformed/repaired Local Ignore behavior, retained-snapshot continuation resume, reset conflict/operational outcomes, both reset cancellation boundaries, replay, byte-exact backup, durable artifact presence, and report-byte stability remain contractual.

Separately, `tests/conformance/packs/crash_log_scan_run/v1.json` owns the
independently authored nineteen-scenario blocking oracle: Standard and Targeted
happy paths, generated Local Ignore, pre-discovery cancellation,
post-discovery queued cancellation, admitted/durable cancellation, observer
delivery failure, public request-validation, discovery, intake, report-write,
and Unsolved Logs finalization failures, both recovery decisions, intervening-change conflict,
portable backup failure, both reset cancellation boundaries, replay, and
abandonment. Its
materialized plans contain only declared inputs and normalization policy; the
Rust, Node, Python, and CXX runners cannot read its expected observations. The pack
compares ordered discovery, setup absence, effective concurrency, Installed
YAML Data identities, terminal log outcomes, stable per-log event traces, full
typed Display Content carriers, typed resume diagnostics, byte-exact reset
receipts, structured observer failure, cancellation state, forbidden effects,
structured failure stage, nonempty-message contract, relevant path, terminal
disposition, movement outcome, and ordered artifact types, plus durable report effects.
Timings and cross-log concurrent interleaving are
projected out before receipt emission.
This promoted pack runs conjunctively with the retained fixture, inventory,
negative-export, and internal-fault checks. Its blocking receipts replace the
manifest's copied adapter acknowledgements, positive source markers, and
per-scenario or presentation required-owner lists.

The manifest's `forbiddenExports` section is negative evidence for the completed
contract step. Identifier-shaped markers use identifier boundaries, so removing
`scan_run_execute` does not reject the surviving
`scan_run_contract_execute`. Required tracked files fail closed when missing;
only an explicitly optional legacy-only file may disappear as proof of removal.
Do not weaken the list when a generated artifact is inconvenient to refresh:
remove the source export, regenerate the declaration/stub and parity artifacts,
and remove its runtime-coverage registration together.

When a Rust request, event, status, discovery source, disposition, failure stage, infrastructure stage, movement intent, progress phase, scan-run Installed YAML Data role/provenance/diagnostic kind, scan-run Local Ignore state, recovery decision, or resume-error kind changes, update the manifest inventory, trusted variant evidence policy, and affected executable pack expectations or retained analyzer dispositions in the same change. Update adapter projections and tests where the contract changes; do not add copied acknowledgements or source-marker evidence. The validator derives those final-operation enum variants directly from Rust, so adding a variant only to Rust fails the canonical compliance profile. Config-owned reset decisions remain separate from this scan-run inventory.

When intentionally contracting a scan-execution symbol, add it to every
applicable `forbiddenExports` surface before removing it. This keeps a later
compatibility shim or stale generated artifact from silently restoring the
second execution path.


## Config, file, path, and message operation packs

The five blocking packs `config-operations`, `file-operations`, `path-operations`,
`path-normalization`, and `message-operations` use the semantic launcher above.
All require Rust, Node, and Python receipts. The first three additionally require
CXX receipts and JUnit on MSVC and clang-cl; the latter two have no corresponding
CXX public export. Their domain shapes preserve values, successful misses,
structured failures, exact file effects, and narrowly normalized temporary paths.
Existing registry and positive evidence remain available; migrated rows require
receipts. See the [operation equivalence map](../implementation/config_file_path_message_conformance_equivalence.md)
for precise coverage, fixtures, retained class methods, and commands.

## Database, Version Registry, and Scan Game packs

`database-operations`, `version-registry`, and `scan-game` are blocking semantic
families using the same launcher. All require Rust, Node, Python, and native CXX
receipts; CXX additionally requires MSVC and clang-cl JUnit/attempt evidence.
Owned SQLite bytes, fixture-seeded version metadata, and disposable INI/ENB
directories replace contributor-machine state. Observations preserve each
domain's public results, misses, errors, and exact durable effects.

The [same-revision evidence map](../implementation/database_version_scangame_conformance_equivalence.md)
lists executed operations and retained diagnostics. Existing suites run before
the receipt jobs at the same checkout. Migrated rows require actual receipts;
frozen unrelated methods retain their original evidence without granting credit
to newly added operations. No frontend consumer obligation is introduced.

## Auxiliary, performance, and shared operation packs

Auxiliary, performance, shared utilities, registry, and generic settings now
also have blocking domain packs. The [owner operation evidence map](../implementation/aux_perf_shared_conformance_equivalence.md)
lists their public observations, applicable adapters, transport limitations,
and retained analyzers. Each pack uses the same authenticated semantic launcher;
native participants require both MSVC and clang-cl. Existing registry evidence
remains available until its final cleanup.

## Registry, settings, and version owners

Additional blocking packs exercise registry accessors and keys, YAML lifecycle
and ordered batch operations, cache retrieval, typed settings validation, version
extraction, synthetic PE resources, and Version Registry queries. The
[owner evidence map](../implementation/registry_settings_version_conformance_equivalence.md)
lists each pack's exact participant set and transport contract. Source-derived
applicability does not enroll absent binding methods, and method-level facts
cannot be borrowed by newly added aliases. These additions retain existing
runtime evidence; expanding a family does not expand its earlier retirement set.

## XSE and installation-dependent evidence

`xse-operations` is blocking across Rust, CXX (MSVC and clang-cl), Node, and Python. Eighteen scenarios observe all six extender types in missing, loader-only, and detected states. Each uses a disposable directory and records the final file bytes; constructor coverage requires the corresponding variant observation.

`xse-folder` is blocking for Rust and CXX, the public adapters that expose `resolve_xse_folder_for_scan`. Six scenarios exercise Local.yaml precedence, configured documents fallback, VR folder naming, and fail-soft malformed/missing local data. They initialize the Version Registry from fixed fixture metadata and reject inputs that could enter host discovery. Run it with `run_semantic_conformance.py --family xse-folder --participant rust`, or the CXX launcher with `-Family xse-folder -Compiler msvc` (and `clang-cl`).

`installation-paths` is blocking across all four adapters and both CXX compilers. Its two directory layouts exercise validated cached game/documents lookup and ordered missing-INI reports, including paths with spaces, while checking the complete unchanged file and directory inventory.

The [installation discovery evidence boundary](../implementation/installation_discovery_conformance_equivalence.md) distinguishes cached-path/checker execution from the named retained `installation-discovery-source-boundary` analyzer. Platform registry and home-directory fallback have no public injected provider; structural evidence makes no runtime discovery claim. Existing focused diagnostics remain in place, and passing receipts stay untracked.
