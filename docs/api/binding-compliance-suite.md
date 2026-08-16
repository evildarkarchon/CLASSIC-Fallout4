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
| `full` | Local release/backstop profile. Adds Bun/Node runtime tests, the Python PyO3 rebuild, and Python smoke tests. Repeatable `--receipt` inputs may also produce a full-repository shadow aggregation without making absent shadow receipts block the legacy profile. |
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

The Crash Log Scan Run pack also has private shadow launchers for its
Rust, Node, Python, and native CXX semantic adapters:

```powershell
python tools/binding_compliance/run_scan_run_conformance.py --participant rust
python tools/binding_compliance/run_scan_run_conformance.py --participant node
uv run --project python-bindings python tools/binding_compliance/run_scan_run_conformance.py --participant python
pwsh -ExecutionPolicy Bypass -File tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Compiler msvc
pwsh -ExecutionPolicy Bypass -File tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Compiler clang-cl
```

Each invocation creates a fresh input-only `run_plan.json` and calls only the
selected adapter's public scan-run seam. Rust, Node, and Python publish
`receipt.json`, `attempt.json`, and `shadow_report.json` beneath
`tools/binding_compliance/artifacts/<participant>/<instance>/<invocation>/`.
The CXX launcher hosts its bridge-only target through the approved CLI wrapper,
uses a 15-minute child-process bound, and publishes `receipt.json`, mandatory
`ctest.junit.xml`, `attempt.json`, separate `stdout.log`/`stderr.log`, and the
instance-scoped JSON/Markdown compliance reports beneath
`tools/binding_compliance/artifacts/cxx/windows-<compiler>/<invocation>/`.
Ordinary full CLI wrapper runs visibly skip that target when no current plan and
receipt destination are supplied. The native workflows upload these diagnostics
from explicitly nonblocking shadow steps after their existing runtime tests.
They do not replace or weaken the manifest, parity, declaration/stub, rebuild,
or runtime gates. Both `windows-msvc` and `windows-clang-cl` receipts are required
before CXX completes its participant denominator; three Rust/Node/Python
receipts alone remain incomplete.

## What The Suite Proves

The suite does not replace lower-level parsers. It owns the top-level pass/fail result, policy mapping, and gap report while reusing existing gates as executable evidence:

- C++: `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`
- Node: `python tools/node_api_parity/check_parity_gate.py --repo-root .` plus `bun run dts:freshness:check` in the Node CI slice.
- Python: `python tools/python_api_parity/check_parity_gate.py --repo-root .` plus `validate_stubs.py`.
- User Settings ownership: `python tools/user_settings_ownership/check.py --repo-root .` rejects first-party production references that reintroduce flat models, generic User Settings variants/key policies, raw `CLASSIC_Settings` interpretation outside `classic-user-settings-core`, or runtime use of the generated default mirror.
- Crash Log Scan Run parity and contraction: `python tools/binding_compliance/scan_run_contract.py --repo-root .` validates the shared corpus under `tests/fixtures/crash_log_scan_run/`, compares its variant inventory with the Rust enums, and fails unless Rust, CXX, Node, and Python acknowledge every variant. The inventory includes Installed YAML Data roles, provenance, diagnostic kinds, Local Ignore states, both explicit recovery decisions, resume-error kinds, and continuation/reset invariants in addition to lifecycle variants. The same manifest carries a per-surface forbidden-export inventory; the check fails if a removed orchestration, analysis-only execution, batch lifecycle, direct report-writing, resettable cancellation, or global-FCX name remains in public source, CXX parity data, Node declarations/parity/runtime coverage, or Python stubs/parity/runtime coverage. It also requires executable Standard, Targeted, existing/generated/recovery/reset Installed YAML Data, cancellation on both sides of the reset critical section, replay, retained-snapshot, byte-exact backup, structured-failure evidence, and CLI, GUI, and TUI presentation evidence.
- Evidence migration ledger: `python tools/binding_compliance/migration_ledger.py --repo-root .` fails closed when a tracked parity row, raw runtime-registry claim, Crash Log Scan Run marker/audit, or current consumer/source audit is missing, duplicated, stale, or unclassified. The check is blocking in every source-level profile because inventory drift must be classified, but the ledger and its migration states are diagnostic only: they cannot grant compliance, runtime coverage, or receipts. The named `scan-run-local-ignore-reset-internal-faults` analyzer keeps replacement-publication and durability-unknown projection tests blocking because those faults have no safe deterministic public-adapter trigger. The C++, Node, Python, User Settings, and Crash Log Scan Run gates above remain the executable evidence owners.

Existing C++, Node, and Python parity gates remain available as focused debugging commands. Do not remove or weaken them unless the compliance suite demonstrably covers the same check and the replacement is documented in the same change.

## Current Coverage Gaps

The first implementation intentionally reports known weak coverage instead of silently rewriting policy around it. The current non-blocking gaps are:

- C++ has no editable runtime-coverage registry equivalent to the Node and Python registries. The Crash Log Scan Run v1 pack now produces executable CXX receipts from generated bridge DTOs and events on MSVC and clang-cl, while the source parity gate and existing CLI/GUI wrapper suites remain blocking during shadow migration.
- The Crash Log Scan Run v1 pack has Rust, Node, Python, and both required CXX execution-instance receipts in shadow. Their scoped reports are useful diagnostics, but they do not retire existing evidence until equivalence review and blocking promotion complete.
- Replacement-publication failure and replacement durability uncertainty remain blocking internal fault analyzers, not semantic receipts. A deterministic public scenario may replace that classification later; a test-only public binding hook or fabricated adapter receipt may not.

Treat new drift, stale generated artifacts, stale baselines, missing runtime coverage, policy/source contradictions, tooling bugs, and local environment failures as separate failure classes in the structured report.

## Crash Log Scan Run Contract Changes

`tests/fixtures/crash_log_scan_run/manifest.json` is the machine-readable owner for normalized cross-interface expectations. Paths are compared relative to each runner's temporary root; processing timings and exact concurrent event interleavings are deliberately excluded. Discovery, Rust-selected effective concurrency, serialized event variants, discovery-order outcomes, structured failures, Installed YAML Data and reset metadata, valid/generated/malformed/repaired Local Ignore behavior, retained-snapshot continuation resume, reset conflict/operational outcomes, both reset cancellation boundaries, replay, byte-exact backup, durable artifact presence, and report-byte stability remain contractual.

Separately, `tests/conformance/packs/crash_log_scan_run/v1.json` owns the
independently authored fourteen-scenario shadow oracle: Standard and Targeted
happy paths, generated Local Ignore, pre-discovery cancellation,
post-discovery queued cancellation, admitted/durable cancellation, observer
delivery failure, both recovery decisions, intervening-change conflict,
portable backup failure, both reset cancellation boundaries, replay, and
abandonment. Its
materialized plans contain only declared inputs and normalization policy; the
Rust, Node, Python, and CXX runners cannot read its expected observations. The pack
compares ordered discovery, setup absence, effective concurrency, Installed
YAML Data identities, terminal log outcomes, stable per-log event traces, full
typed Display Content carriers, typed resume diagnostics, byte-exact reset
receipts, structured observer failure, cancellation state, forbidden effects,
and durable report effects. Timings and cross-log concurrent interleaving are
projected out before receipt emission.
This shadow pack does not supersede the broader blocking manifest.

The manifest's `forbiddenExports` section is negative evidence for the completed
contract step. Identifier-shaped markers use identifier boundaries, so removing
`scan_run_execute` does not reject the surviving
`scan_run_contract_execute`. Required tracked files fail closed when missing;
only an explicitly optional legacy-only file may disappear as proof of removal.
Do not weaken the list when a generated artifact is inconvenient to refresh:
remove the source export, regenerate the declaration/stub and parity artifacts,
and remove its runtime-coverage registration together.

When a Rust request, event, status, discovery source, disposition, failure stage, infrastructure stage, movement intent, progress phase, scan-run Installed YAML Data role/provenance/diagnostic kind, scan-run Local Ignore state, recovery decision, or resume-error kind changes, update the manifest acknowledgements and affected adapter tests in the same change. The validator derives those final-operation enum variants directly from Rust, so adding a variant only to Rust fails the canonical compliance profile. Config-owned reset decisions remain separate from this scan-run inventory.

When intentionally contracting a scan-execution symbol, add it to every
applicable `forbiddenExports` surface before removing it. This keeps a later
compatibility shim or stale generated artifact from silently restoring the
second execution path.

