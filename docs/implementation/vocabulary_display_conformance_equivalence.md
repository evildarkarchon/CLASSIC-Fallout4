# Vocabulary and Display Content conformance equivalence

Issue #208 moves public Vocabulary label observations into two executable
families and carries complete typed Display Content through the existing Crash
Log Scan Run family. The packs own independently authored expected wording;
adapters emit only observations from real public Rust, CXX, Node, and Python
operations. Adapter output cannot generate or refresh expected labels.

## Scope and ownership

| Family | Public operation selectors | Evidence |
| --- | --- | --- |
| `config-vocabulary` | `installed_yaml_data_provenance_label`, `scan_run_installed_yaml_data_provenance_label`, `installed_yaml_data_diagnostic_kind_label`, `local_ignore_yaml_data_state_label` | Every source-owned token, exact independently authored label, input order, unknown-token rejection |
| `scan-run-vocabulary` | `scan_run_installed_yaml_data_diagnostic_kind_label`, `scan_run_local_ignore_yaml_data_state_label`, `scan_run_log_disposition_label`, `scan_run_log_failure_stage_label`, `scan_run_infrastructure_error_stage_label`, `scan_run_local_ignore_reset_failure_stage_label` | Every source-owned token, naming twins, exact label, input order, unknown-token rejection |
| `crash-log-scan-run` | Existing execute, resume, abandonment, event, and result carriers | Ordered Display Content lines and segments alongside the existing run-state and durable-effect observations |

These are ten operation selectors. CXX exposes a distinct scanner provenance
alias; Node and Python use their existing config provenance resolver for both
provenance selectors. This is shared public behavior, not a new API or an
adapter-authored label. The source inventory follows the enum owner and reviewed
naming delegation to derive canonical tokens, including durable-publication
stages. It does not derive expected wording from Rust `display_label` bodies.

The vocabulary plans contain direct `operation` and `tokens` input, with no
fixture or expected values. Each receipt preserves the original operation and
ordered `{token, label, rejected}` entries. Node converts canonical token spelling
to the public PascalCase enum carrier where required; string-token APIs receive
the canonical token unchanged. Unknown inputs invoke the real public resolver
or enum decoder and retain its rejection as a null label. Unexpected adapter
failures remain failed executions.

The scan pack contains 84 typed display lines across its nineteen scenarios.
They exercise all five severities (`info`, `success`, `notice`, `warning`,
`failure`) and five emitted segment kinds (`text`, `emphasis`, `label`, `path`,
`count`). Receipts preserve severity, line/segment order, and every segment's
`kind`, `text`, `path`, and `count`, including inactive carrier fields and
Rust-selected count nouns. Only declared temporary-root path normalization is
permitted. `Name` has no current public scan-run producer; its explicit retained
inventory disposition supplies no executable receipt credit.

## Same-revision observations and retirement

Validation was performed in the issue #208 working tree based on
`f44310296b5d7c0117353f2ced68f1542350914c`. Native public implementations and
declarations were unchanged between the old suites and the new observations.
The Python bindings were rebuilt successfully (18 crates) before their suite.
The already-built Node addon was exercised through the real public seam.

Before retirement, `bun run test:bun` passed 1,047 tests, including the existing
label blocks and four new transport tests. The Python suite passed 534 tests;
`bun run test:node` passed 17 tests. Node `test:types` and `parity:gate:ci` also
passed, including declaration freshness. A positive transport test first
detected incorrect enum casing and then passed after the adapter used the
actual PascalCase carrier; no expected wording was changed to make it pass.

Fresh Node receipts passed both vocabulary families with the same native
implementation. Their retained invocation directories under
`tools/binding_compliance/artifacts/issue208-node/node/node/` are
`eaa07169-7c8c-4f5f-b948-b543a1b0e67c` (config) and
`41640995-71e9-46eb-bea2-7bac0d8a06cf` (scan run). Each includes the input-only
plan, source identity, receipt, and passing conformance report.

Only then were twelve duplicated JavaScript tests retired: the config
`Installed YAML Data Display Labels` block and the scanlog `Crash Log Scan Run
Display Labels` and `Crash Log Scan Run token Display Labels` blocks. Their
unknown-token checks are covered by the exhaustive pack and native transport
tests. Comments inside those deleted test bodies were removed with their code;
unrelated comments remain. The two affected suites subsequently passed 159
tests, and the scan-run TypeScript contract check passed.

Six redundant Display Content tests were also retired: three CXX sibling tests
for successful results/events and rejected discovery, two Node sibling tests
for successful results/events, and one Python sibling test for successful
execution. Their complete public observations are now checked centrally.
Comments attached to these deleted tests were removed with the code.

After all four vocabulary adapters and both native compiler instances passed,
five copied Python wording tests were retired: two configuration label tests
and three scan-run label tests. The mixed recovery-state test keeps its unique
negative assertion that configuration rejects the run-only state; only its
copied positive label assertion was removed. Two additional Rust binding
sibling glossary-wording tests (Node and Python) were retired in favor of the
same exhaustive public receipts. No comparable copied CXX sibling wording
assertion remained. Comments belonging to retired code were removed, and the
remaining negative ownership test's explanation now refers to the receipts.
After these final removals, focused Python binding tests passed 59 tests, and
the Rust binding sibling suites passed 26 Node tests and 25 Python tests.

Rust owner and the remaining binding sibling tests retain conversion,
delegation, and internal invariants beyond public expected wording. Remaining
Python tests, frontend consumer obligations, source parity, declaration/stub
checks, negative exports, fault analyzers, and the other semantic families also
remain. The new families do not claim unrelated vocabulary or unreachable
Display Content variants. Both vocabulary families also passed Rust, Python,
CXX MSVC, and CXX clang-cl receipt and coverage checks. Rust owner suites passed
633 tests with 11 ignored; all three parity gates and Python stub validation
passed without baseline changes. The complete compliance suite passed 454
tests before the final resolver-identity and CI mutation tests were added.

Final verification passed 466 compliance tests. The complete
`cargo test --workspace --all-features` run passed 3,082 tests with zero failures
and 39 ignored before the final two sibling glossary tests were retired; the
focused sibling rerun above verifies those removals. Both native compiler
instances passed the Crash Log Scan Run and both vocabulary families under
`tools/binding_compliance/artifacts/issue208-final-native/`. Final Node and
Python vocabulary and display receipts passed under the
`tools/binding_compliance/artifacts/issue208-final/` and
`tools/binding_compliance/artifacts/issue208-final-display/` roots. The final Node
transport descriptor keeps each resolver beside its enum-input convention;
all four transport tests, type checking, and fresh receipts for both vocabulary
families passed after that change.

The remaining lower-level fault tests cover OS-dependent diagnostic wording
and inaccessible injected failures. Exact public display expectations were
extended only for deterministic request-validation, recovery, and replay
paths; no arbitrary prose exclusions or new test-only public APIs were added.

## Commands

```powershell
python tools/binding_compliance/run_semantic_conformance.py --family config-vocabulary --participant node --artifact-root tools/binding_compliance/artifacts/issue208-node
python tools/binding_compliance/run_semantic_conformance.py --family scan-run-vocabulary --participant node --artifact-root tools/binding_compliance/artifacts/issue208-node
uv run --project python-bindings python -m pytest python-bindings/tests -q
```

From `node-bindings/classic-node`:

```powershell
bun run test:bun
bun run test:node
bun run test:types
bun run parity:gate:ci
bun test __test__/config.spec.ts __test__/scanlog.spec.ts
```

The semantic launcher accepts `--participant rust` or `--participant python`
for the other direct adapters. Native CXX runs use
`tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1` with
`-Family config-vocabulary` or `-Family scan-run-vocabulary` and a separately
recorded `-Compiler msvc` or `-Compiler clang-cl`. The existing scan-run launcher
continues to produce the full Display Content observations.
