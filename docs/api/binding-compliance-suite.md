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
| `ci` | Canonical source-level umbrella check. Runs the C++ parity gate, Node parity/runtime-coverage gate, Python parity/runtime-coverage gate, Python stub validation, the User Settings ownership audit, the Crash Log Scan Run contract-variant check, and static policy/artifact/docs checks. |
| `cxx-ci` | CI slice for the Windows C++ workflow. Runs the canonical suite around the CXX parity gate and shared static policy checks. |
| `node-ci` | CI slice for the Node workflow. Runs the canonical suite around Node parity and `index.d.ts` freshness checks. |
| `python-ci` | CI slice for the Python workflow. Runs the canonical suite around Python parity, stub validation, uv drift-guard setup, and the schema-version guard. |
| `full` | Local release/backstop profile. Adds Bun/Node runtime tests, the Python PyO3 rebuild, and Python smoke tests. |
| `static` | Policy, docs, artifact presence, and known-gap reporting without external commands. |

Use `--skip-commands` when reviewing policy mapping without invoking lower-level gates. Use `--fail-on-gaps` when maintainers are ready to turn known non-blocking coverage gaps into blocking failures.

## What The Suite Proves

The suite does not replace lower-level parsers. It owns the top-level pass/fail result, policy mapping, and gap report while reusing existing gates as executable evidence:

- C++: `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`
- Node: `python tools/node_api_parity/check_parity_gate.py --repo-root .` plus `bun run dts:freshness:check` in the Node CI slice.
- Python: `python tools/python_api_parity/check_parity_gate.py --repo-root .` plus `validate_stubs.py`.
- User Settings ownership: `python tools/user_settings_ownership/check.py --repo-root .` rejects first-party production references that reintroduce flat models, generic User Settings variants/key policies, raw `CLASSIC_Settings` interpretation outside `classic-user-settings-core`, or runtime use of the generated default mirror.
- Crash Log Scan Run parity and contraction: `python tools/binding_compliance/scan_run_contract.py --repo-root .` validates the shared corpus under `tests/fixtures/crash_log_scan_run/`, compares its variant inventory with the Rust enums, and fails unless Rust, CXX, Node, and Python acknowledge every variant. The inventory includes Installed YAML Data roles, provenance, diagnostic kinds, and Local Ignore states in addition to lifecycle variants. The same manifest carries a per-surface forbidden-export inventory; the check fails if a removed orchestration, analysis-only execution, batch lifecycle, direct report-writing, resettable cancellation, or global-FCX name remains in public source, CXX parity data, Node declarations/parity/runtime coverage, or Python stubs/parity/runtime coverage. It also requires executable Standard, Targeted, existing/generated Installed YAML Data, cancellation, and structured-failure evidence plus CLI, GUI, and TUI presentation evidence.

Existing C++, Node, and Python parity gates remain available as focused debugging commands. Do not remove or weaken them unless the compliance suite demonstrably covers the same check and the replacement is documented in the same change.

## Current Coverage Gaps

The first implementation intentionally reports known weak coverage instead of silently rewriting policy around it. The current non-blocking gap is:

- C++ has a source-only bridge parity gate, but no dedicated runtime coverage registry equivalent to the Node and Python registries. C++ runtime behavior remains covered through the CLI/GUI build and test wrappers.

Treat new drift, stale generated artifacts, stale baselines, missing runtime coverage, policy/source contradictions, tooling bugs, and local environment failures as separate failure classes in the structured report.

## Crash Log Scan Run Contract Changes

`tests/fixtures/crash_log_scan_run/manifest.json` is the machine-readable owner for normalized cross-interface expectations. Paths are compared relative to each runner's temporary root; processing timings and exact concurrent event interleavings are deliberately excluded. Discovery, Rust-selected effective concurrency, serialized event variants, discovery-order outcomes, structured failures, Installed YAML Data metadata, valid/generated Local Ignore behavior, durable artifact presence, and report-byte stability remain contractual.

The manifest's `forbiddenExports` section is negative evidence for the completed
contract step. Identifier-shaped markers use identifier boundaries, so removing
`scan_run_execute` does not reject the surviving
`scan_run_contract_execute`. Required tracked files fail closed when missing;
only an explicitly optional legacy-only file may disappear as proof of removal.
Do not weaken the list when a generated artifact is inconvenient to refresh:
remove the source export, regenerate the declaration/stub and parity artifacts,
and remove its runtime-coverage registration together.

When a Rust request, event, status, discovery source, disposition, failure stage, infrastructure stage, movement intent, progress phase, scan-run Installed YAML Data role/provenance/diagnostic kind, or scan-run Local Ignore state changes, update the manifest acknowledgements and the affected adapter tests in the same change. The validator derives those final-operation enum variants directly from Rust, so adding a variant only to Rust fails the canonical compliance profile. Config-owned recovery enums are intentionally outside this #146 inventory.

When intentionally contracting a scan-execution symbol, add it to every
applicable `forbiddenExports` surface before removing it. This keeps a later
compatibility shim or stale generated artifact from silently restoring the
second execution path.

