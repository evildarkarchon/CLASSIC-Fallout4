# User Settings conformance equivalence

Issue #203 makes the User Settings v1 family blocking without deleting the
compatibility corpus or its focused tests. The independent oracle remains
`tests/fixtures/user_settings_compatibility/expectations.json`; no adapter output
is used to generate expected observations. This map describes the facts shared
by the old and replacement evidence, rather than granting coverage itself.

## Same source revision

The Rust launcher runs `compatibility_contract` and `open_conformance` together
in one Cargo invocation. Both source files participate in its source digest.
The first checks the authored corpus invariants, including complete flat-leaf
migration and typed preservation; the second executes the public operations and
emits the receipt. A failed corpus test fails the command even if a receipt was
written. A skipped receipt producer cannot pass central validation.

The native CI jobs retain their existing Rust workspace, Bun, Node smoke,
rebuilt Python pytest, and CLI/GUI wrapper suites and run the new receipts from
the same checkout. CXX semantic and CLI/GUI consumer instances execute on both
MSVC and clang-cl. Every receipt is checked against its unique prepared
invocation, current source identity, and expectation digest; CXX additionally
requires associated JUnit and attempt evidence. Repository success is the
conjunction of those jobs for the same revision, not a later comparison of
observations from unrelated builds.

## Shared facts

All scenario IDs below are in `tests/conformance/packs/user_settings/v1.json`.
Every applicable semantic adapter must complete every scenario. The pack
compiler rejects omitted or duplicate oracle references and expected output
documents stay outside input-only adapter plans.

| Existing corpus fact | Replacement scenarios | Equal or stronger public observations |
| --- | --- | --- |
| Current open and no-write outcome (`open_current_without_writing`) | `canonical-current-nested` | Source selection/classification, typed values, eligibility, diagnostics, original bytes/revision, and unchanged complete tree |
| Malformed safe fallback (`open_malformed_with_safe_fallbacks`) | `malformed-document` | Exact fallback values and ordered diagnostics, blocked eligibility, preserved malformed source bytes and complete tree |
| Legacy flat and previous location | `flat-classic-config`, `previous-settings-location` | Read-only source/location selection, typed projection, migration eligibility, exact preservation |
| Missing source and future major | `missing-document`, `newer-major-schema` | Distinct defaults and safety fallbacks, no open-time creation, eligibility and source identity |
| Invalid values, alias precedence, unknown values, GUI geometry | `invalid-known-values`, `alias-only`, `canonical-alias-conflict`, `unknown-entries`, `gui-geometry` | Exact selected typed views/diagnostics and original bytes; read-only tree preservation |
| Multi-field pure preview | `preview-multi-field-update` | Actual accepted field paths/values, base revision, ordered diagnostics, no durable change before consent |
| Accepted update and unrelated-node preservation | `commit-one-canonical-field-without-losing-unknowns`, `commit-preserves-alias-only`, `commit-preserves-canonical-alias-conflict`, `commit-preserves-invalid-known-values` | Published typed YAML equals the authored full document, truthful byte revision, untouched unknown/invalid/alias values, complete durable tree |
| Atomic invalid rejection and stale conflict | `reject-invalid-update-as-one-unit`, `refuse-stale-revision` | Exact field/code/message rejection, no partial write, expected/actual conflict revisions, retained external bytes |
| Ineligible ordinary updates | `reject-update-malformed`, `reject-update-newer-major-schema`, `reject-update-flat-classic-config`, `reject-update-missing` | Rejected preview and eligibility, no publication or source repair |
| Explicit first-run bootstrap | `bootstrap-missing-declined`, `bootstrap-missing-defaults`, `bootstrap-missing-overrides`, `bootstrap-invalid-update`, `bootstrap-concurrent-creation` | Preview separated from consent, full defaults/overrides compared to corpus YAML, invalid rejection, and conflict-safe preservation of concurrent creation |
| Ineligible bootstrap | `reject-bootstrap-canonical-current-nested`, `reject-bootstrap-malformed`, `reject-bootstrap-newer-major-schema` | Caller approval cannot override preview rejection or replace existing state |
| Complete flat migration (`migrate_every_flat_classic_config_leaf`) and verified restore (`restore_verified_flat_backup`) | `migration-flat-restore` | The same `flat_migrated.yaml` oracle, ordered review rows, two pure plans, double reversal, exact approved publication, reverified byte-exact backup and restoration |
| Previous-location and alias migration | `migration-previous-restore`, `migration-alias-conflict`, `migration-alias-only` | Authored proposed YAML, anchored endpoints, unchanged planning tree, durable apply/restore checkpoints |
| No migration or declined review | `migration-current`, `migration-missing`, `migration-unsupported`, `migration-older`, `migration-malformed`, `migration-review-only` | Exact planning status, diagnostics and proposal/reversal when available; no unauthorized write |
| Stale and operational migration/restore outcomes | `migration-stale-apply`, `migration-previous-shadowed`, `migration-stale-restore`, `migration-legacy-edited`, `migration-tampered-backup`, `migration-missing-backup`, `migration-blocked-backup` | Exact conflicts and stable operational codes, verified backup integrity, all durable files/directories at every checkpoint |

The nineteen bootstrap/update scenarios reference the corresponding existing
operation IDs directly (hyphens replace underscores in scenario IDs). Migration
references the seventeen authored `migration_scenarios`. Neither mapping copies
expected values into a second oracle. Successful publication compares typed YAML
while backups, source bytes, and other files remain byte-exact. The one declared
optional empty coordination lock applies only to the specified apply-conflict
checkpoints; it does not permit arbitrary extra files.

## Evidence deliberately retained

The corpus contract's exhaustive flat-leaf mapping, default mirror checks,
complete typed group tests, legacy TUI import, and internal publication fault
injection retain unique evidence beyond the selected public receipt facts.
They remain in their existing core and binding suites. Consumer receipts cover
maintained CLI, GUI, and TUI actions only and appear under `consumerCoverage`;
they cannot stand in for semantic adapter execution or invent a frontend restore
action. The catalog records exact maintained obligations independently of this
document.

The Rust ownership audit, source/signature inventories, declaration freshness,
Python stubs, compile-only type negatives, forbidden exports, namespace absence,
and other negative checks remain independent blocking evidence. Registry claims
alone cannot satisfy migrated semantic rows. Migration ledger entries and this
map are diagnostic and never grant runtime coverage.

Migrated operation rows include open, update/bootstrap preview, accepted commit,
migration planning, in-memory reversal, and application, in addition to their
observed DTOs. The current CXX source inventory names both migration-receipt
restoration and legacy-TUI-import restoration `restore`. That ambiguous method
symbol stays in the retained legacy evidence rather than claiming that executing
one operation proves both. Migration restoration itself is mandatory in every
semantic receipt, including its restoration outcome and receipt facts. Legacy
TUI import and its restoration remain covered by their existing focused tests.
Frontend geometry methods likewise retain their semantic tests; consumer
execution is separate evidence and cannot promote those semantic rows.

Issue #204 retires the broad Node/Python User Settings registry selectors and
hashes, the migrated contract/identifier claims, and their copied summary test
pointers and prose. Explicit registry contract IDs retain the rows outside
the current family coverage policy; focused binding identifiers retain the
additional unmigrated property, geometry, and legacy-import diagnostics.
Neither the narrowed registries nor this map can grant migrated coverage.

The Node smoke test's five positive function-existence assertions for open,
update preview/commit, and migration planning/application are removed. Blocking
adapter receipts execute these operations and compare their observations;
source/declaration checks still validate their exported signatures. The smoke
test retains forbidden-export negatives and its actual Node-runtime open and
bootstrap calls, since the semantic receipt runner uses Bun.

No corpus or focused semantic test is retired. Further deletion requires a
separate fact-by-fact proof for the specific evidence being removed.
