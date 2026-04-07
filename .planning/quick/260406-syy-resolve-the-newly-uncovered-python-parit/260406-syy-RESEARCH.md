# Quick Task 260406-syy - Research

**Researched:** 2026-04-06  
**Domain:** Python parity governance metadata  
**Confidence:** HIGH

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Keep `FcxResetError` as a Rust-only Tier-2 deferred surface for Python. Align the Python parity governance/runtime metadata so the surface is classified as deferred instead of newly uncovered. Do not expand the Python binding contract for this quick task.

### the agent's Discretion
- Choose the smallest set of Python parity registry, governance, and generated artifact updates needed to clear the newly uncovered status while matching existing repo policy and prior Phase 3 intent.
- Use repo-standard Python parity validation depth appropriate for the touched files.

### Deferred Ideas (OUT OF SCOPE)
None provided in `260406-syy-CONTEXT.md`.

## Project Constraints (from AGENTS.md)

- Prioritize active work in `ClassicLib-rs/`.
- Keep business logic in Rust; keep Python thin.
- Maintain the single shared Tokio runtime; do not introduce another runtime.
- Keep docs synchronized with workflow/architecture changes.
- Never write to `NUL`/`nul` on Windows.
- Consult `docs/api/README.md` if changing public binding-facing APIs.
- For Python binding validation, use the repo-local Python parity workflow and `ClassicLib-rs/python-bindings/.venv`.

## Summary

`FcxResetError` is already an intentional Tier-2 deferred Rust-only Python surface. The repo state records that decision explicitly, and the current Python parity diff already sees the symbol as a Tier-2 deferred-style gap. The gate is failing only because the Python deferred backlog/governance artifacts were not refreshed to classify `binding:rust:FcxResetError`, so `build_coverage_summary()` falls back to `newly_uncovered`.

**Primary recommendation:** add `FcxResetError` to `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json`, refresh `tier2_wave_manifest.json`, then run the parity gate with baseline refresh so both runtime coverage summary artifact sets move from `newly_uncovered` to `deferred`.

## Standard Stack

| Tool / Artifact | Purpose | Use Here |
|---|---|---|
| `tools/python_api_parity/generate_wave_manifest.py` | Regenerates deferred backlog + wave manifest from parity diff | Canonical way to classify this as deferred |
| `tools/python_api_parity/check_parity_gate.py --update-baseline` | Regenerates runtime coverage summaries and syncs checked-in baseline artifacts | Required to clear gate + stale-artifact check |
| `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json` | Runtime-verified metadata only | **Do not add `FcxResetError` here** |

## Architecture Patterns

### Pattern: Deferred Rust-only Tier-2 gap lives in governance, not runtime registry
Use the deferred backlog for Rust public symbols that Python intentionally does not expose. `FcxResetError` matches this pattern exactly.

Evidence:
- `STATE.md` already says: "Track `FcxResetError` as deferred Tier-2 parity while runtime-verifying the new Node-only FCX exports."
- `docs/api/classic-scanlog-core.md` documents `FcxResetError` as a core reset contract, not a Python export.
- `tools/binding_parity_runtime_coverage.py` marks any gap as `newly_uncovered` unless it is found in the deferred backlog or runtime registry.

### Pattern: Keep Python runtime registry limited to runtime-verified surfaces
`runtime_coverage_registry.json` only feeds `runtime_verified` coverage. Using it for a non-exported Rust-only gap would misstate coverage.

## Don't Hand-Roll

| Problem | Don't Do | Use Instead | Why |
|---|---|---|---|
| Clear the gate by faking coverage | Add `FcxResetError` to `runtime_coverage_registry.json` | Add a deferred backlog entry | Registry means runtime-verified, which is false here |
| Refresh summaries manually | Edit generated summary JSON/MD by hand | Run `generate_wave_manifest.py` + `check_parity_gate.py --update-baseline` | Generated files will drift again |
| Expand Python API | Add a Python exception/export/stub | Keep surface Rust-only and deferred | Violates locked decision |

## Files That Must Change Together

### Required
1. `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json`
   - Must gain a deferred entry for `FcxResetError`.
2. `docs/implementation/python_api_parity/governance/tier2_wave_manifest.json`
   - Must be refreshed so governance matches the backlog.
3. `ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.json`
4. `ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.md`
5. `docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json`
6. `docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md`
   - These will flip `binding:rust:FcxResetError` from `newly_uncovered` to `deferred` and restore `newly_uncovered_total: 0`.

### Usually unchanged for this quick fix
- `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json` — leave untouched.
- `docs/implementation/python_api_parity/baseline/parity_diff_report.json|md` — likely already include the Rust gap; refresh only if the generated diff also changed.

## Common Pitfalls

### Pitfall 1: Putting `FcxResetError` in the runtime registry
That would mark a non-exported Rust-only symbol as runtime-verified. Repo tooling treats the runtime registry as coverage evidence, not deferment metadata.

### Pitfall 2: Updating backlog but not baseline/runtime summaries
`check_parity_gate.py` fails both on `newly_uncovered_total > 0` and on stale checked-in artifacts. Governance-only edits are not enough.

### Pitfall 3: Hand-editing generated artifacts without rerunning the scripts
`generate_wave_manifest.py` and `check_parity_gate.py` will overwrite them. Use the scripts as the source of truth.

### Pitfall 4: Broadening the Python API to “fix” the gate
Out of scope and contradicts the locked decision.

## Validation Architecture

### Test Framework
| Property | Value |
|---|---|
| Framework | Repo Python parity scripts + pytest-backed smoke metadata |
| Config file | `tools/python_api_parity/*.py` + `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json` |
| Quick run command | `python tools/python_api_parity/generate_wave_manifest.py --repo-root .` |
| Full gate command | `python tools/python_api_parity/check_parity_gate.py --repo-root . --update-baseline` |

### Minimal command set for this fix
```powershell
python tools/python_api_parity/generate_wave_manifest.py --repo-root .
python tools/python_api_parity/check_parity_gate.py --repo-root . --update-baseline
```

### When to run the heavier repo-standard checks
Only if the quick metadata refresh unexpectedly changes stubs/bindings or if CI still disagrees:
```powershell
python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry
uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q
```

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---:|---|---|
| Python | parity scripts | ✓ | 3.14.3 | — |
| `uv` | repo-standard Python env flow | ✓ | 0.11.3 | Use existing venv only if already prepared |

## Sources

### Primary (HIGH confidence)
- `tools/binding_parity_runtime_coverage.py` - classification logic (`newly_uncovered` vs `deferred`)
- `tools/python_api_parity/check_parity_gate.py` - gate failure conditions and baseline sync behavior
- `tools/python_api_parity/generate_wave_manifest.py` - deferred backlog + wave manifest generation flow
- `docs/implementation/python_api_parity/governance/tier2_backlog_and_governance.md` - required local checks and governance rules
- `ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.json` - current failing state (`binding:rust:FcxResetError` = `newly_uncovered`)
- `.planning/STATE.md` - prior locked intent for `FcxResetError`
- `docs/api/classic-scanlog-core.md` - FCX reset contract

## Metadata

**Confidence breakdown:**
- Classification approach: HIGH - direct repo policy + tool logic agree
- Files-to-update set: HIGH - derived from the generator/gate code paths
- Validation commands: HIGH - taken from repo docs/scripts
