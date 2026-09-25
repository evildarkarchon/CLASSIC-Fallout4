# Validated 43-crate baseline

This is the passing follow-up to [issue #237](https://github.com/evildarkarchon/CLASSIC-Fallout4/issues/237)'s [initial baseline](../README.md). No crate owner had moved between the initial snapshot and this run. The initial `full` report remains a historical failure; this directory preserves the fresh result after the two uncovered Python parity rows were enrolled and the CI workflow was consolidated.

The branch revision is `36c93978ec19a63359aa4cdd8bb49465ad6cfe9e`. [CI run 36127742320](https://github.com/evildarkarchon/CLASSIC-Fallout4/actions/runs/36127742320) checked out PR merge revision `3704143b8cd109294667c9ad212e9aab6e42f8b2`. Both revisions have Git tree `a29d4f8b260674789dd31c155fae4ebd7579370c`, so the graph and all CI jobs observed identical source files. Receipt identities name the merge revision, not the branch revision.

## Workspace graph

[`graph.json`](graph.json) records all 43 physical crates by manifest group and all 175 typed direct internal dependency entries. Fresh `cargo metadata --locked --offline --format-version 1 --no-deps` matched the initial snapshot exactly: **161 normal**, **14 dev**, and **0 build** internal entries. The group counts remain 4 foundation, 19 business logic, 17 Python bindings, and one each under C++ bindings, Node bindings, and UI applications.

## Gate result

The [full Binding Compliance report](full-compliance-report.json) and its [readable summary](full-compliance-report.md) show `repository_complete: true`: **23/23** retained requirements passed, **85/85** conformance families passed, and **0** missing families, uncovered parity rows, failed requirements, gaps, or skips. The two Python rows uncovered by the initial report are covered here. [`ci-run.json`](ci-run.json) records 15 successful jobs; the workflow's disabled rustfmt job was skipped. The [initial rustfmt failure](../rustfmt-check.txt) remains exposed separately and is not counted as a passing formatting gate.

## Durable provenance

[`ci-receipts.zip`](ci-receipts.zip) preserves **351** same-run producer artifacts, including every `receipt.json` with its immutable `run_plan.json` and each native attempt/JUnit file. [`receipt-index.json`](receipt-index.json) lists their family, participant, execution instance, source identity, file hashes, and archive hash. The receipts contain **1,898 completed** scenario or consumer observations.

[`gate-evidence.zip`](gate-evidence.zip) preserves seven producer evidence files for all **16** retained command gates. [`gate-evidence-index.json`](gate-evidence-index.json) records their run/revision identities, command IDs, file hashes, and archive hash. [`ci-artifacts.json`](ci-artifacts.json) records GitHub's IDs, upload digests, sizes, and expiry dates for all **359** artifacts: 351 conformance, six retained-gate uploads, one pinned Corrosion source, and one full report. These tracked snapshots remain available after GitHub's seven-day artifact retention. Keep receipt/plan pairs and gate evidence unchanged; their identities and fixture paths bind them to the CI checkout.

The full job authenticated current-run gate evidence against its checkout and catalog while independently validating all conformance receipts and plans. Its command was:

```powershell
python tools/binding_compliance/check_compliance.py --repo-root . --profile full --receipt-directory tools/binding_compliance/artifacts/downloaded --gate-evidence-directory tools/binding_compliance/artifacts/retained-downloaded --output-dir tools/binding_compliance/artifacts/full
```
