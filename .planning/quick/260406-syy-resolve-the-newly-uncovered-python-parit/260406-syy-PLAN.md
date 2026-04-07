---
phase: quick-260406-syy-resolve-the-newly-uncovered-python-parit
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json
  - docs/implementation/python_api_parity/governance/tier2_wave_manifest.json
  - ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.json
  - ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.md
  - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json
  - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md
autonomous: true
requirements:
  - quick-260406-syy
must_haves:
  truths:
    - "The Python parity gate classifies binding:rust:FcxResetError as deferred instead of newly_uncovered."
    - "Python runtime coverage summaries report newly_uncovered_total: 0 after the metadata refresh."
    - "The Python binding contract stays unchanged; FcxResetError remains Rust-only Tier-2 deferred per D-01."
  artifacts:
    - path: "docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json"
      provides: "Deferred Tier-2 governance entry for FcxResetError"
      contains: "FcxResetError"
    - path: "docs/implementation/python_api_parity/governance/tier2_wave_manifest.json"
      provides: "Regenerated wave manifest including the deferred scanlog gap"
      contains: "FcxResetError"
    - path: "ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.json"
      provides: "Current Python runtime coverage classification"
      contains: "\"newly_uncovered_total\": 0"
    - path: "docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json"
      provides: "Checked-in baseline coverage summary aligned with current gate output"
      contains: "\"newly_uncovered_total\": 0"
  key_links:
    - from: "docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json"
      to: "tools/python_api_parity/generate_wave_manifest.py"
      via: "deferred backlog input"
      pattern: "FcxResetError"
    - from: "tools/python_api_parity/check_parity_gate.py"
      to: "ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.json"
      via: "--update-baseline runtime coverage refresh"
      pattern: "newly_uncovered_total"
    - from: "ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.json"
      to: "docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json"
      via: "baseline sync"
      pattern: "FcxResetError"
---

<objective>
Reclassify the newly uncovered Python parity surface for `FcxResetError` as an intentional Tier-2 deferred Rust-only gap.

Purpose: Restore the Python parity gate to the previously approved Phase 3 policy without broadening the Python API.
Output: Refreshed governance metadata and runtime coverage summary artifacts showing `FcxResetError` as deferred.
</objective>

<execution_context>
@.planning/quick/260406-syy-resolve-the-newly-uncovered-python-parit/260406-syy-CONTEXT.md
@.planning/quick/260406-syy-resolve-the-newly-uncovered-python-parit/260406-syy-RESEARCH.md
@.planning/STATE.md
</execution_context>

<context>
@docs/implementation/python_api_parity/governance/tier2_backlog_and_governance.md
@docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json
@docs/implementation/python_api_parity/governance/tier2_wave_manifest.json
@ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.json
@docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json
@docs/api/classic-scanlog-core.md

Locked decision to honor:
- D-01: Keep `FcxResetError` as a Rust-only Tier-2 deferred Python surface. Do not add a Python export, stub row, or runtime registry entry for this quick task.

Implementation note:
- Follow the repo-standard Python parity workflow from the project guide: use governance metadata plus generator scripts, not hand-edited generated summaries.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Classify FcxResetError in deferred governance metadata</name>
  <files>docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json, docs/implementation/python_api_parity/governance/tier2_wave_manifest.json</files>
  <action>Add the missing deferred Tier-2 backlog entry for `FcxResetError` under the `scanlog` wave-1 backlog per D-01, using the existing deferred-gap schema and owner/wave conventions already used for other Rust-only scanlog symbols. Then regenerate `tier2_wave_manifest.json` with `python tools/python_api_parity/generate_wave_manifest.py --repo-root .` so the manifest includes `FcxResetError` in the canonical generated output. Do not add `FcxResetError` to `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json`, and do not add any Python export/stub/API surface.</action>
  <verify>
    <automated>python tools/python_api_parity/generate_wave_manifest.py --repo-root .</automated>
  </verify>
  <done>`deferred_runtime_backlog.json` contains a deferred `FcxResetError` entry, and the regenerated wave manifest includes the same Rust symbol in the scanlog Tier-2 backlog.</done>
</task>

<task type="auto">
  <name>Task 2: Refresh Python runtime coverage summaries and baseline</name>
  <files>ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.json, ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.md, docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json, docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md</files>
  <action>Run the parity gate with baseline refresh so the generated runtime coverage artifacts consume the updated deferred backlog and reclassify `binding:rust:FcxResetError` from `newly_uncovered` to `deferred` per D-01. Commit the refreshed artifact pairs from both the live parity-artifacts directory and the checked-in baseline. Keep scope limited to metadata refresh; if the command tries to broaden the Python contract, stop and keep the contract unchanged.</action>
  <verify>
    <automated>python tools/python_api_parity/check_parity_gate.py --repo-root . --update-baseline</automated>
  </verify>
  <done>Both runtime coverage summary JSON/MD pairs are regenerated, `binding:rust:FcxResetError` is classified as `deferred`, and `newly_uncovered_total` is zero in the refreshed summaries.</done>
</task>

</tasks>

<verification>
- `python tools/python_api_parity/generate_wave_manifest.py --repo-root .`
- `python tools/python_api_parity/check_parity_gate.py --repo-root . --update-baseline`
</verification>

<success_criteria>
- The Python parity gate no longer reports `FcxResetError` as newly uncovered.
- Deferred governance artifacts and generated coverage summaries agree on the Tier-2 deferred status.
- No Python binding/stub/runtime-registry surface is added for `FcxResetError`.
</success_criteria>

<output>
After completion, create `.planning/quick/260406-syy-resolve-the-newly-uncovered-python-parit/260406-syy-SUMMARY.md`.
</output>
