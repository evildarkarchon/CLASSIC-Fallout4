# Workspace baseline before the first owner move

This is the starting evidence for [issue #237](https://github.com/evildarkarchon/CLASSIC-Fallout4/issues/237) and the [23-crate layout work](https://github.com/evildarkarchon/CLASSIC-Fallout4/issues/234). The branch source revision is `ddb260a8ef55619e0099522843a6f5ae96a56c3e`, after the Node and Python parity prerequisites in #235 and #236. Its tracked tree was clean when the graph and local gate observations were captured on 2026-09-24 (Pacific time).

The [Binding Compliance CI run](https://github.com/evildarkarchon/CLASSIC-Fallout4/actions/runs/36095292890) is a pull-request run for that branch head. GitHub checked out synthetic merge commit `810ea57651fbaa5d4c1ecb4246fbaf7d9ac39c13`. Both commits have Git tree `e2b043876f62fd2f2f19bcf59a9f0e1c603c7e9f`, so they contain identical source files. CI receipts are bound to the **merge commit**, while the local graph and source report are bound to the **branch commit**. Preserve that distinction when comparing later revisions; a receipt from this run cannot be revalidated under the branch commit ID.

## Physical workspace graph

[`graph.json`](graph.json) records every physical workspace crate and every direct internal dependency entry. It was derived from `cargo metadata --locked --offline --format-version 1 --no-deps` at the branch revision. The crate set is `workspace_members`. A dependency is internal when its package name belongs to that set and `source` is null. A null dependency `kind` counts as `normal`; entries retain their kind even if the same source and target also appear under another kind. Groups are the first directory of each manifest path relative to the workspace root. Rows are sorted and paths use `/` so a later graph can be compared directly.

| Manifest group | Physical crates |
| --- | ---: |
| `foundation` | 4 |
| `business-logic` | 19 |
| `python-bindings` | 17 |
| `node-bindings` | 1 |
| `ui-applications` | 1 |
| `cpp-bindings` | 1 |
| **Total** | **43** |

There are **161 normal**, **14 dev**, and **0 build** internal dependency entries. Two source/target pairs occur in both normal and dev kinds, leaving 173 distinct pairs across 175 entries. The four foundation crates include `classic-shared-py`; the 17 `python-bindings` crates plus that crate account for the 18 Python extension identities in the layout plan.

## Gate observations and provenance

The local `python tools/binding_compliance/check_compliance.py --repo-root . --profile ci` run passed all **16** source requirements with **0** failures, gaps, or skips. [`source-compliance-report.json`](source-compliance-report.json) preserves the requirement-level observations. The `ci` profile does not certify runtime conformance or repository completion.

Before that run, `uv sync --project python-bindings --inexact` refreshed the binding environment and `PYO3_PYTHON` pointed at `python-bindings/.venv/Scripts/python.exe`.

The local capture used Windows PowerShell 7.6.6, Python 3.14.5, Cargo 1.98.0, rustc 1.98.0, rustfmt 1.9.0, and uv 0.12.15. The CI run uses the toolchain setup in its linked workflow, not these local tool versions.

`cargo fmt --all -- --check` failed on existing formatting in `node-bindings/classic-node/src/scan_run_tests.rs` (the `include_str!` expression and three assertion continuations). [`rustfmt-check.txt`](rustfmt-check.txt) preserves the command, exit code, and diff. The CI rustfmt job is disabled. Formatting is therefore an **exposed pre-existing failure**, not passing baseline evidence; this issue makes no change to that source file.

The CI run supplies Rust build, lint, and tests; Node parity, declarations, build, and runtime/type tests; Python parity, stubs, rebuild, and smoke tests; CXX parity and CLI/GUI consumer tests under MSVC and clang-cl; and semantic participant receipts. Its `full` Binding Compliance job must authenticate the same-run immutable plans and receipts before a repository-wide result can be claimed.

## Durable receipt snapshot

[`ci-receipts.zip`](ci-receipts.zip) preserves all 351 producer artifacts from that workflow run: 1,830 files including each `receipt.json` beside its immutable `run_plan.json`, and native `attempt.json` and `ctest.junit.xml` evidence. [`receipt-index.json`](receipt-index.json) records each family, participant, execution instance, source identity, observation status counts, and SHA-256 hashes of the receipt, plan, and native evidence. The archive itself has a SHA-256 hash in the index. All 1,898 recorded scenario or consumer observations have `completed` execution status. This snapshot survives GitHub's seven-day artifact retention and lets the final workspace compare actual observations, not only a run URL.

The plans bind Git revision, participant source bytes, and fixture paths. Keep the archived files unchanged. The CI `full` job validates them in its original merge checkout; the archive is not a substitute for revalidation under the branch commit or a later workspace.

## Same-tree CI result

[`ci-run.json`](ci-run.json) preserves all 15 job outcomes at the identical source tree: 13 succeeded, the rustfmt job was skipped by workflow policy, and **Full Repository Conformance failed**. [`ci-artifacts.json`](ci-artifacts.json) preserves GitHub's IDs, upload digests, sizes, and expiry dates for all 352 uploaded artifacts, including the full report.

The [`full` report](full-compliance-report.json) and [readable summary](full-compliance-report.md) show **23/23 retained requirements passed**, **85/85 conformance families passed**, and no missing families or failed scenario executions. Nevertheless, `repositoryComplete` is **false** because these two Python parity rows have no executed or retained coverage disposition:

- `parity:python:scangame.crashgen_orchestrator.check_crashgen_settings`
- `parity:python:scangame.wrye.parse_wrye_report`

This is an exposed baseline failure. The passing participant jobs and source profile are valid scoped observations, but the failed `full` gate is **not** migration evidence of repository completion. A later owner move must not borrow this run's receipts or treat these two rows as covered without a fresh, passing full aggregation.

The gap is in coverage selection, not an unexecuted Python runner: #236 corrected these contract rows to Rust symbols `check_with_rules` and `format_report`, while the corresponding `crashgen_check` and `wrye_report` conformance pack capabilities and trusted predicates still omit those symbols. Their Python runners do call the public operations. Updating the pack capabilities and predicates, then producing fresh same-revision receipts and a passing `full` report, is the follow-up needed to close this gap.

## Passing follow-up

The two selectors were corrected before any crate owner move. [Validated run 36127742320](validated-36127742320/README.md) records a fresh same-tree graph, all participant receipts and retained-gate evidence, and a passing `full` report. The failed report above remains the accurate observation for the original revision.
