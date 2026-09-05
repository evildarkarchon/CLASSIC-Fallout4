# Binding Compliance Suite

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
| `full` | Local release/backstop profile. Adds Bun/Node runtime tests, the Python PyO3 rebuild, and Python smoke tests. Repeatable `--receipt` inputs produce a full-repository aggregation whose centrally selected family enforcement is conjunctive with the retained gates. |
| `static` | Policy, docs, artifact presence, and known-gap reporting without external commands. |

Use `--skip-commands` when reviewing policy mapping without invoking lower-level gates. Use `--fail-on-gaps` when maintainers are ready to turn known non-blocking coverage gaps into blocking failures.

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

## User Settings Shadow Execution

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
and migration operations retain their existing tests for subsequent slices.

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
each compiler emits its own receipt and mandatory JUnit evidence. CI runs this
family with `continue-on-error: true` and uploads diagnostics under
`tools/binding_compliance/artifacts/user-settings/`. A failed shadow comparison
remains visible as failure in its report. The current parity gates, runtime
registries, compatibility tests, and ownership audit remain blocking; this slice
does not promote User Settings or retire any existing evidence.

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

The suite reports known weak coverage instead of silently rewriting policy around it. The remaining gaps are:

- C++ has no editable runtime-coverage registry equivalent to the Node and Python registries. The Crash Log Scan Run v1 pack closes that family-specific gap with executable CXX receipts on MSVC and clang-cl; other CXX domains still rely on their source-derived parity dispositions until their own packs migrate.
- The Crash Log Scan Run v1 report is blocking across Rust, Node, Python, both required CXX execution instances, and the separate CLI, GUI, and TUI consumer instances. Its copied acknowledgements and positive source-marker evidence have been retired. The fixture, source-inventory, negative-export, parity, declaration/stub, rebuild, runtime, and native wrapper gates remain blocking; other families have not inherited this retirement.
- Replacement-publication failure, replacement durability uncertainty, and the non-hermetic structured-failure injections remain blocking internal fault analyzers, not semantic receipts. A deterministic public scenario may replace that classification later; a test-only public binding hook or fabricated adapter receipt may not.
- Public enum values without a hermetic v1 scenario—such as no-log/setup terminal states, alternate Installed YAML candidate diagnostics, and custom Unsolved Logs movement—remain exact blocking dispositions under `scan-run-contract-validator`. They grant no semantic receipt credit; the variant policy prevents them, or any newly added value, from falling through to an unrelated happy-path fact.

Treat new drift, stale generated artifacts, stale baselines, missing runtime coverage, policy/source contradictions, tooling bugs, and local environment failures as separate failure classes in the structured report.

## Crash Log Scan Run Contract Changes

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

