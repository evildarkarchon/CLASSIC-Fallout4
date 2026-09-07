# Installed YAML Data conformance equivalence

Issue #206 adds blocking receipts for the config-owned Installed YAML Data
inspection and preparation operations. The source-owned pack is
`tests/conformance/packs/installed_yaml_data/v1.json`; the independent inputs are
under `tests/fixtures/installed_yaml_data_conformance/`. Expected observations
were authored from the public contract, with exact fixture byte identities,
before comparing native adapter observations. Adapter output never authors or
refreshes the oracle.

## Public evidence

| Existing public behavior | Replacement scenarios | Observed facts |
| --- | --- | --- |
| Independent installed selection | `updated-main-bundled-game` | Updated Main and bundled game, role/schema/provenance, exact selected identities, complete unchanged file tree |
| Interrupted-install previous candidate | `previous-selected-read-only`, `invalid-previous-falls-back` | Previous bytes selected without promotion; rejected previous diagnostics retain candidate attribution |
| Present canonical blocks previous | `invalid-canonical-blocks-previous` | Bundled fallback, parse diagnostic for canonical, intact canonical and previous bytes |
| Compatibility and role validation | `independent-rejected-candidates`, `invalid-schema-falls-back` | Independent ordered Main/Game rejection kinds, selected bundled identities, all rejected bytes preserved |
| Required source and supported game policy | `missing-main-no-usable-source`, `unsupported-game-before-io`, `vr-uses-fallout4-data` | Typed error role, absent selected arms on errors, empty unsupported-game tree, VR's registered Fallout4 data role |
| Inspection ignores Local Ignore | `inspection-ignores-malformed-local` | Successful Main/Game inspection and exact unchanged malformed Local Ignore bytes |
| Operation-scoped ready snapshot | `ready-snapshot-retains-original-bytes` | Returned Main/Game/Ignore identities and parsed version/game/ignore values retain original content after all three files change |
| Legacy Local Ignore adoption | `legacy-ignore-adopted-byte-for-byte`, `canonical-ignore-wins-over-legacy` | Byte-exact canonical copy with preserved CRLF legacy file; existing canonical precedence over distinct legacy bytes |
| Recovery preparation with unavailable defaults | `recovery-plan-without-defaults`, `missing-ignore-invalid-defaults` | Retained malformed identity and selected game version, explicit absent default identity, distinct ready/recovery/error arms, no repair or generation on rejected defaults |

All fifteen scenarios run through Rust, Node, Python, and native CXX (MSVC and
clang-cl). The launchers materialize fresh input-only plans and validate the
returned receipts against their invocation, source identity, family digest,
scenario inventory, and exact normalized observations. CI retains each native
suite and runs these receipts in the same checkout; failures remain blocking
and diagnostics upload even when an earlier retained check fails.

## Coverage boundary and retained evidence

Runtime row credit is limited to `inspect_installed_yaml_data`,
`load_installed_yaml_data`, the public inspection/snapshot request/result/error
carriers actually crossed, and exact CXX status/take/getter operations exercised
by each returned arm. A new operation cannot borrow an existing carrier's
fact. Node/Python source mappings identify the two public operation entrypoints;
legacy config registry selectors can only report `receipt_required` for them.
The two canonical operation mappings added to each Node/Python parity contract
name existing public entrypoints so applicability is source-derived; they add
no public API or binding behavior.
Other config mappings retain their prior evidence.

The observed recovery metadata proves the load operation's recovery arm. It
does not claim all `LocalIgnoreRecoveryPlan` methods, vocabulary label helpers,
or generic YAML operations. These remain outside this pack's row denominator.
The existing [Crash Log Scan Run pack](../../tests/conformance/packs/crash_log_scan_run/v1.json)
and its blocking pack continue to own scan-level continuation and proceed/reset
observations, including cancellation, conflict, replay rejection, verified
backup, retained defaults, and forbidden writes.

No existing positive evidence is removed. In particular,
`business-logic/classic-config-core/src/installed_yaml_data_tests.rs` retains
concurrent publication, injected failures, invalid UTF-8, cache-unavailable,
durability-unknown, no-clobber, direct reset, and diagnostic-message tests.
Existing CXX, Node, and Python installed-YAML tests, all source parity gates,
declaration/stub checks, negative checks, and the scan pack remain in place.
Ordered typed diagnostic attribution is compared here; prose and OS-specific
error formatting retain their focused existing tests.

Frontend consumer receipts are not fabricated: this family adds direct semantic
adapters, while established scan-run consumer obligations continue to describe
the maintained frontends. Network update publication and atomic updater
rollback are separate operation owners and are not claimed by this pack.
