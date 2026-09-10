# Autoscan Report conformance equivalence

> Subsequent retirement: the [issue #211 evidence map](fixture_evidence_retirement.md) records migrated registry claims removed after this promotion. Canonical owner goldens and focused diagnostics remain.

Issue #207 adds the blocking `autoscan-report` family at
`tests/conformance/packs/autoscan_report/v1.json`. It reuses the existing
`tests/fixtures/autoscan_report_goldens/` corpus through complete public Crash
Log Scan Run requests in Rust, Node, Python, and CXX. Autoscan Report Assembly
and its contribution collector remain private Rust implementation details.

## Oracle and observable behavior

The existing `expected.md` files are the independent byte oracle. Central pack
compilation reads those files and binds their bytes, scenario expectations,
and input fixtures into the expectation digest. It does not generate report
expectations from adapter output. Input-only adapter plans omit expected
reports; receipts contain the actual persisted bytes as hexadecimal, their
SHA-256, byte length, and returned report path.

| Original golden | Conformance scenario | Public observations and retained byte contract |
| --- | --- | --- |
| `cases/empty/expected.md` | `empty-findings` | Completed run; one successful log; FormID/plugin/suspect counts `0/1/0`; explicit no-match output and empty-findings section placement |
| `cases/populated/expected.md` | `populated-findings` | Counts `4/4/4`; Crashgen placements and disabled setting notice; Crash Suspect sources; all four Mod Guidance groups; Plugin Evidence, Named Records, resolved/unresolved FormIDs, and lookup hit/miss text |
| `cases/fcx/expected.md` | `fcx-mode` | FCX request with Anniversary Edition configuration; retained setup result; counts `0/1/0`; complete canonical setup text in the persisted report |

Every scenario also compares semantic request inputs, terminal status and
counts, structured log outcomes, and ordered typed Display Content. The
populated input deliberately retains Unicode, multiline guidance, and
authored trailing spaces. Exact bytes pin separators, ordering, and the final
newline as well as text.

The prebuilt `formids.db` input contains the populated manifest's database rows.
Each adapter copies it to the normal scan-owned Main FormID database location;
the Rust core performs lookup. The original owner golden test continues to
build the equivalent database from the manifest.

FCX game and documents directories are isolated beneath the adapter's
execution root. The central comparison expands only the three existing
`{{FCX_GAME_ROOT}}`, `{{FCX_DOCUMENTS_ROOT}}`, and `{{PATH_SEPARATOR}}` tokens
on the expectation side, using the reported absolute execution root. Actual
report bytes are never rewritten or whitespace-normalized. The report digest
and byte length must agree with those bytes.

Durable observations include the post-run SHA-256 and byte length of every
declared input, absence of each forbidden path, and a recursive inventory of
unexpected files. They therefore detect source mutation and unlisted output
alongside the expected report. Relative report and typed display paths retain
their public identity across temporary installation roots.

## Required execution

Run the retained adapter build prerequisites first. Python requires
`uv sync --project python-bindings --inexact`, the current-shell `PYO3_PYTHON`
pin, and `./rebuild_rust.ps1 -Target python`; Node requires the built native
binding. See the project guide for the platform-specific build commands.

```powershell
python tools/binding_compliance/run_scan_run_conformance.py --family autoscan-report --participant rust
python tools/binding_compliance/run_scan_run_conformance.py --family autoscan-report --participant node
uv run --project python-bindings python tools/binding_compliance/run_scan_run_conformance.py --family autoscan-report --participant python
pwsh -ExecutionPolicy Bypass -File tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Family autoscan-report -Compiler msvc
pwsh -ExecutionPolicy Bypass -File tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Family autoscan-report -Compiler clang-cl
```

Every applicable adapter must produce a fresh authenticated receipt covering
all three scenarios. CXX requires both `windows-msvc` and `windows-clang-cl`
execution instances through the approved CLI test wrapper. Receipt identities
must match their invocation, input-only plan, expectation digest, and current
source revision. Repository-wide aggregation requires same-revision evidence
from every participant; partial, stale, missing, skipped, or mismatched
receipts cannot satisfy the blocking family.

These commands describe required validation, not a record of successful runs.
The invocation artifacts contain execution and comparison results. Receipts
remain conjunctive with retained parity, declaration/stub, runtime, and native
wrapper checks, and CI preserves diagnostics when a retained gate fails.

## Coverage boundary and retained diagnostics

This family observes completed `LogResult` and `LogDisposition` facts at the
public Scan Run seam. It grants no coverage to private assembly helpers,
unexecuted request factories, or continuation/recovery operations. Existing
Crash Log Scan Run lifecycle and recovery scenarios retain those obligations.

Typed Display Content is Rust-authored meaning: ordered line severity and
segment kind, text, count, and path carriers. Receipt comparison preserves
that structure. Transport delivery, terminal/Qt layout, wrapping, and frontend
interaction remain under the existing consumer obligations and frontend tests;
this family does not fabricate new consumer receipts.

No owner diagnostics are retired. In particular, retain:

- `business-logic/classic-scanlog-core/tests/autoscan_report_goldens.rs` for the
  original complete-run byte characterization and mismatch artifacts.
- `business-logic/classic-scanlog-core/src/report_tests.rs` for assembly order,
  absent versus completed-empty contributions, sorting, placement, and FCX text.
- `business-logic/classic-scanlog-core/src/autoscan_report_contribution_collector_tests.rs`
  for collection boundaries and internal contribution behavior.
- Existing semantic analyzer, Scan Run, presentation, binding, and consumer
  tests for their focused contracts and failure diagnostics.

The immutable oracle has no auto-update mode. Intentional report-contract
changes require an explicit reviewed change to the original golden and its
affected expectations; a receipt is evidence, never an oracle author.
