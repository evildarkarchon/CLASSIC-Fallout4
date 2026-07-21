# Autoscan Report Assembly Refactor Brief

> **Status: superseded.** Do not implement or restore the line-bearing
> interfaces, compatibility facades, or sequencing described below. The final
> supported architecture is recorded in
> [`ADR-0005`](../adr/0005-semantic-autoscan-report-contributions.md), the
> current public contract is in
> [`classic-scanlog-core.md`](../api/classic-scanlog-core.md), and exact output
> compatibility is enforced by the immutable
> [`autoscan_report_goldens`](../../tests/fixtures/autoscan_report_goldens/README.md)
> corpus. The remaining body is retained only as historical implementation
> context.

This brief captures the accepted design from the entry #2 grilling session for `architecture-review-20260630-205128.html`: move Autoscan Report ordering and rendering into a deep Rust module.

Canonical domain language is in [`CONTEXT.md`](../../CONTEXT.md). The data-owned placement decision is recorded in [`docs/adr/0003-autoscan-report-placement-yaml-data.md`](../adr/0003-autoscan-report-placement-yaml-data.md).

> Historical status: the `lines` payloads below describe the temporary first
> assembly slice. Crash Suspect, Mod Guidance, and Plugin Evidence have since
> moved to typed semantic payloads; the current contract is documented in
> [`docs/api/classic-scanlog-core.md`](../api/classic-scanlog-core.md).
> The final contract cutover also removed the public `ReportFragment`,
> `ReportComposer`, `ReportGenerator`, `StringPool`, `SettingsValidator`, and
> Python-only `ParallelReportProcessor` compatibility surfaces. They remain
> below only where they explain the historical implementation sequence.

## Target

Deepen Autoscan Report Assembly inside `business-logic/classic-scanlog-core/src/report.rs` so callers cross one seam to turn scan facts and Autoscan Report Contributions into final Autoscan Report lines.

Primary files likely affected:

- `business-logic/classic-scanlog-core/src/report.rs`
- `business-logic/classic-scanlog-core/src/report_tests.rs`
- `business-logic/classic-scanlog-core/src/orchestrator.rs`
- `business-logic/classic-scanlog-core/src/orchestrator_tests.rs`
- `business-logic/classic-scanlog-core/src/settings_validator.rs`
- `business-logic/classic-config-core/src/crashgen_rules.rs`
- `business-logic/classic-config-core/src/crashgen_registry_yaml.rs`
- `business-logic/classic-config-core/src/*_tests.rs`
- `CLASSIC Data/databases/CLASSIC Fallout4.yaml`
- `node-bindings/classic-node/src/crashgen_rules.rs`
- `python-bindings/classic-config-py/src/crashgen_rules.rs`
- API docs under `docs/api/`
- parity artifacts or declarations if binding-visible shape changes

## Design Decisions

- `Autoscan Report Assembly` owns canonical section order, conditional section presence, section headers, separators, footer/header rendering, finding placement, and human-facing report text.
- Orchestrator and collectors gather report facts and Autoscan Report Contributions; assembly does not run analyzers.
- Assembly produces report content only, initially `Vec<String>`. Autoscan Report path selection, writing, write failure handling, and Unsolved Logs behavior stay outside entry #2.
- Assembly happens in the `Finalize` progress phase after analyzers and contribution collectors finish.
- Assembly must be per-log and concurrency-safe. Do not introduce batch-level locks or shared mutable assembler state.
- Existing public `ReportGenerator` APIs remain as compatibility facades in the first slice. The new assembler may reuse them internally to preserve exact text.
- `ReportComposer` must not be used for canonical assembly. Fix its final composition path to be deterministic; the accepted minimal fix is sequential final composition if many-log performance is not regressed.
- Generated Autoscan Report text should be behavior-preserving in the first slice. Do not intentionally improve wording, section titles, or markdown in this refactor.

## Proposed Rust Shape

Keep the first new types `pub(crate)` in `classic-scanlog-core` unless a concrete external consumer requires more.

Suggested scanlog-local types:

```rust
pub(crate) struct AutoscanReportAssembler { ... }

pub(crate) struct AutoscanReportFacts {
    pub classic_version: String,
    pub crashlog_filename: String,
    pub main_error: String,
    pub crashgen_name: String,
    pub crashgen_version: String,
    pub crashgen_status: Option<CrashgenVersionStatus>,
    pub fake_bot_compatible_mode: bool,
    pub fcx_mode_enabled: bool,
}

pub(crate) enum AutoscanReportContribution {
    CrashgenExpectation(CrashgenExpectationContribution),
    DisabledSettingNotice { setting_name: String, crashgen_name: String },
    CrashSuspectFinding { finding: CrashSuspectFinding },
    ModGuidance { result: ModGuidanceAnalysisResult },
    PluginEvidence { result: PluginEvidenceAnalysisResult },
    FormIdFinding { lines: Vec<String> },
    NamedRecordFinding { result: NamedRecordFindingAnalysisResult },
}

pub(crate) struct CrashgenExpectationContribution {
    pub kind: OutcomeKind,
    pub severity: RuleSeverity,
    pub message: String,
    pub fix: Option<String>,
    pub placement: AutoscanReportPlacement,
}

pub(crate) enum ModGuidanceGroup {
    MayConflict,
    FrequentCrashes,
    HasSolutions,
    ImportantMods,
}
```

Implementation notes:

- `AutoscanReportFacts` should contain only values that affect report content. Keep `formid_count`, `plugin_count`, and `suspect_count` as `AnalysisResult` metadata.
- `crashgen_name` in facts must be the effective Crashgen name resolved from the Crash Log, not the configured default.
- `fake_bot_compatible_mode` is a fact rendered in Error Information. Settings collection should preserve current behavior by producing no Crashgen Expectation or Disabled Setting Notice contributions when that mode disables checks.
- `fcx_mode_enabled` is a scan context fact. Do not model FCX as a contribution in this slice; preserve current report-path behavior and do not pull in FCX detail lines such as cached file checks or detected configuration issues.

## Contribution Rules

- Crashgen Expectation Outcomes and Disabled Setting Notices should become structured contributions in the first slice.
- Crash Suspect, Mod Guidance, Plugin Evidence, and Named Record Finding payloads now carry typed semantic results; FormID Finding remains the temporary report-facing body-line payload.
- Mod Guidance carries semantic match state and authored guidance; assembly owns groups and subheaders.
- Plugin Evidence and Named Record Finding carry identity/count records; assembly owns sorting, prose, markdown, and completed-empty rendering.
- Crash Suspect Finding carries one typed finding; assembly always renders the crash-suspect section and the existing no-suspect footer when there are no findings.
- Preserve within-category ordering exactly. Crashgen Expectation outcomes render in evaluator order. Settings-placement outcomes render before Disabled Setting Notices. Same-kind body-line contributions preserve input order.

Canonical report section order for tests:

1. Header
2. Error Information, including Crashgen Expectation Outcomes with `ErrorInformation` placement before that section's separator
3. Crash Suspect Findings section, always present
4. FCX Mode notice when enabled
5. Settings-related guidance when any settings-placement Crashgen Expectation Outcome or Disabled Setting Notice exists
6. Mod Guidance
7. Plugin Evidence
8. FormID Finding
9. Named Record Finding
10. Footer

## YAML Data And Placement Compatibility

`Autoscan Report Placement` belongs in `classic-config-core` because it is parsed from YAML Data and carried through Crashgen Expectation evaluation.

Required decisions:

- Introduce `AutoscanReportPlacement` in `classic-config-core` with current values `Settings` and `ErrorInformation`.
- Keep a deprecated `RuleReportBucket` alias for one transition. `classic-config-core` publicly re-exports the old name and Node/Python wrappers currently use it.
- Keep public Rust field names `PreflightAction.bucket` and `EvaluationOutcome.bucket` for one transition to avoid a hard Rust API break, but document those field names as deprecated compatibility names carrying an `AutoscanReportPlacement` value.
- YAML field `placement` is preferred for new data.
- YAML field `bucket` remains a compatibility alias.
- Parse precedence is: valid `placement`, then valid `bucket`, then default `Settings`.
- Invalid `placement` should fall back to valid `bucket` when present.
- Tracked YAML Data should dual-write `placement` and `bucket` during the transition so older clients keep current behavior.
- `CLASSIC Data/databases/CLASSIC Fallout4.yaml` should bump root `schema_version` from `"1.0"` to `"1.1"` when adding `placement` fields.
- Keep `settings_rules_version: 1`; the rule-language semantics are not breaking.
- Keep `GAME_FALLOUT4_YAML` at `SchemaCompat::new(1, 0)`.
- Keep `client-schema-ranges.yaml` max range unchanged; `1.x` already covers the additive `1.1` file shape.

## Binding Compatibility

Node and Python should follow the same compatibility rule as YAML parsing:

- Accept `placement` first.
- Fall back to `bucket`.
- Emit or document `placement` as canonical.
- Node DTOs should emit both `placement` and legacy `bucket` during the transition.
- Python parsing should accept `placement` first and fall back to `bucket`; if a future Python export DTO is added, it should emit `placement` and optionally legacy `bucket` during the same compatibility window.
- Update binding tests, TypeScript declarations, parity baselines, and runtime coverage artifacts when the public shape changes.

## Implementation Order

1. Add `AutoscanReportPlacement` to `classic-config-core`, keep deprecated `RuleReportBucket` alias, and update parser precedence for YAML `placement`/`bucket`.
2. Update tracked YAML Data to dual-write `placement` and `bucket`; bump `CLASSIC Fallout4.yaml` to schema `1.1`.
3. Update Node and Python binding parsing/DTO behavior for `placement` and `bucket` compatibility.
4. Add scanlog-local structured contribution types and `AutoscanReportAssembler` in `report.rs` with tests in `report_tests.rs`.
5. Convert `SettingsValidator` to expose structured Autoscan Report Contributions. Keep legacy `scan_all_settings*` fragment methods as compatibility facades that delegate to report-module rendering helpers rather than owning markdown.
6. Convert orchestrator collection helpers from fragment collectors to contribution collectors.
7. Rewire `process_log_with_progress` so `Analyze` collects contributions and `Finalize` assembles the report.
8. Fix `ReportComposer` deterministic composition and add or document the accepted performance check.
9. Update API docs and binding parity artifacts.

## Tests To Add Or Update

Rust unit tests must stay in sibling `*_tests.rs` files.

`classic-config-core`:

- `AutoscanReportPlacement::parse` accepts `settings` and `error_information`.
- Deprecated `RuleReportBucket` alias still works for compatibility.
- YAML parser prefers valid `placement` over `bucket`.
- YAML parser falls back to valid `bucket` when `placement` is missing or malformed.
- Omitted or invalid values default to `Settings`.

`classic-scanlog-core/src/report_tests.rs`:

- `AutoscanReportAssembler` applies canonical order even when contributions are scrambled.
- Error Information placement renders before that section's separator.
- Settings placement renders under settings-related guidance.
- Disabled Setting Notices render through assembly.
- Crash-suspect section renders the existing no-suspects footer when no findings exist.
- FCX Mode notice renders from facts.
- Header/footer output remains compatible with `ReportGenerator` behavior.
- `ReportComposer::compose()` preserves order for more than the previous parallel threshold.

`classic-scanlog-core/src/orchestrator_tests.rs`:

- Add a small inline golden Autoscan Report regression for a synthetic Crash Log. It should trigger Error Information placement, settings placement, a Disabled Setting Notice, suspect/no-suspect behavior, and header/footer rendering.
- Keep or update existing ordering tests such as `process_log_promotes_bucketed_compatibility_notice_into_error_information` to use placement language.

Bindings:

- Node parses `placement` first, falls back to `bucket`, and emits both during transition.
- Python parses `placement` first and falls back to `bucket`.

YAML/docs:

- Schema validation passes after `CLASSIC Fallout4.yaml` becomes `1.1`.

## Performance Guard

Protect the real workload, not just individual report size.

Accepted performance requirement:

- No meaningful regression against the current local baseline for about 300 Crash Logs in roughly 1.5 seconds with FormID Value Lookup enabled.
- This should be a documented local before/after check, not a strict CI wall-clock gate.
- If wall-clock variance is high, compare multiple runs and investigate any consistent slowdown before merging.
- A report-composition microbenchmark may be added, but it is secondary to a many-log batch path with FormID Value Lookup enabled.
- Assembly must not serialize logs through shared mutable state.

If a benchmark/check is added, prefer the existing `business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs` area and ensure at least benchmark compilation is validated with `cargo bench --bench scanlog_benchmarks -- --test`.

## Docs To Update During Implementation

- `docs/api/classic-config-core-yaml-schema.md`: document `placement` as preferred, `bucket` as compatibility alias, accepted values, and precedence.
- `docs/api/classic-config-core.md`: replace bucket language with Autoscan Report Placement language, document deprecated field names and alias type.
- `docs/api/classic-scanlog-core.md`: document Autoscan Report Assembly ownership and placement interpretation.
- Node/Python API docs or parity docs if generated binding surfaces change.
- Do not duplicate ADR-0003; link to it for the data-owned placement decision.

## Validation Commands

Minimum expected validation for this implementation surface:

```powershell
cargo fmt --all -- --check
cargo test -p classic-config-core
cargo test -p classic-scanlog-core
python tools/schema_version_gate.py --repo-root .
python tools/publish_yaml_data/validate.py --databases-dir "CLASSIC Data/databases" --schema-ranges "CLASSIC Data/databases/client-schema-ranges.yaml"
```

Node binding validation from `node-bindings/classic-node` when the Node surface changes:

```powershell
bun run dts:refresh
bun run parity:gate
bun run test:bun
bun run test:node
bun run dts:freshness:check
```

Python binding validation from repo root when the Python surface changes:

```powershell
uv sync --project python-bindings --inexact --group drift-guards
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"
uv run --project python-bindings python tools/python_api_parity/check_parity_gate.py --repo-root .
uv run --project python-bindings python validate_stubs.py --rust-dir . --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
uv run --project python-bindings python tools/schema_version_gate.py --repo-root .
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python
uv run --project python-bindings python -m pytest python-bindings/tests -q
```

If a Rust workspace-wide command touches PyO3 crates, set `PYO3_PYTHON` first.

## Non-Goals

- Do not implement entry #1's broader Crash Log Scan Run relocation here.
- Do not move Autoscan Report path selection, file writing, or Unsolved Logs policy into Autoscan Report Assembly.
- Do not make YAML Data address every Autoscan Report section. Placement is currently scoped to Crashgen Expectation Outcomes.
- Do not remove public `ReportGenerator` APIs in the first slice.
- Do not rewrite every analyzer to structured output in this slice.
- Do not intentionally change generated Autoscan Report wording or markdown.
