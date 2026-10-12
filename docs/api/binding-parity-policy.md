# Binding Parity Policy

Reference: [`AGENTS.md`](../../AGENTS.md), [`binding-parity-overview.md`](binding-parity-overview.md).

---

## One-Tier Policy Statement

All Rust public API symbols in business-logic `-core` crates are exposed through the one binding surface, the C++ bridge (CXX). The Python and Node bindings retired with ADR-0010 (in [`docs/adr/`](../adr/)). There is no deferred tier, no backlog tier, and no graduated promotion process.

When a new `pub fn` or `pub struct` is added to a `-core` crate's `lib.rs`, the bridge must expose it before CI passes. The only current exception is `classic-resource-core`, which has no dedicated C++ bridge module -- its functionality is accessed transitively through the `classic-file-io-core` bridge surface.

### Scope: methods from workspace-internal traits

Implementing a workspace-internal trait on a `-core` type does not by itself create a parity obligation. The obligation attaches to the crate's own exported surface -- the `pub fn` and `pub struct` entries a binding is meant to publish -- not to every method a shared trait makes callable. `Vocabulary` from [`classic-vocabulary`](classic-vocabulary.md) is the current case: `as_str()` supplies the Vocabulary Token that the bindings already published under their own names, so adopting it changes nothing on any surface, while `label()` becomes projectable rather than automatically projected. A Display Label crosses a binding seam when a frontend needs to render it, and that projection is a deliberate, separately reviewed addition.

No CI check decides this for you. Treat it as a contributor judgement recorded in review.

### Scope: inherent methods that supply an already-published value

The same reasoning covers an inherent method added to a type a binding already publishes. `Revision::token()` and `Revision::from_token()` in [`classic-user-settings-core`](classic-user-settings-core.md) are the current case: each binding previously carried its own byte-identical copy of that formatting, so consolidating it changes which code produces the revision strings the bridge already exposes, not which strings it exposes. No new adapter symbol is warranted.

For the semantic Autoscan Report Contribution architecture, parity is both
positive and negative. CXX exposes the six public Focused
Semantic Analyzers, owned inputs/results, and shared typed errors. They must not expose
the private contribution collector, Autoscan Report Assembly, report
primitives, or fragment-producing compatibility aliases. A breaking removal is
complete only when the bridge wrappers and the Scan Run contract manifest's
`forbiddenExports` describe that same final surface. See
[ADR-0005](../adr/0005-semantic-autoscan-report-contributions.md).

---

## Canonical Conformance Verdict

The repository conformance verdict is the conformance-only `full` profile:

```powershell
python tools/binding_compliance/check_compliance.py --repo-root . --profile full --receipt-directory tools/binding_compliance/artifacts/downloaded
```

Only `--profile full` with all family receipts can certify repository-wide
conformance. Full aggregation fails on any missing family, and each family
report requires every applicable participant and execution instance declared by
`tests/conformance/participants.json` and the consumer obligation catalog.
Registry metadata never supplies that proof. The static requirement catalog and its retained-gate evidence retired with
the Python and Node bindings; the checks CI now runs as direct steps are listed in
[repository gates](../development/repository-gates.md).

Crash Log Scan Run and User Settings have blocking executable conformance obligations. Rust,
CXX on both MSVC and clang-cl, CLI and GUI on both compiler legs,
and TUI must emit current same-revision receipts for their exact applicable
scopes. Central validation requires the full scenario and observation-family
denominator plus every source-owned consumer obligation. Missing, skipped,
stale, malformed, duplicate, or semantically mismatched evidence fails the
applicable workflow. These receipts run conjunctively with the runtime,
Rust-variant, and native wrapper gates; promotion
does not weaken or retire those checks.

See [repository gates](../development/repository-gates.md).

Autoscan Report output also has a blocking semantic family across Rust and CXX
on MSVC and clang-cl. Fresh same-revision receipts compare
actual persisted bytes with the original immutable goldens, typed Display
Content, and durable filesystem effects. Existing owner goldens and focused
assembly diagnostics remain required. This family adds no public assembly API
or frontend layout contract; see the
[Autoscan Report evidence map](../implementation/autoscan_report_conformance_equivalence.md).

---

## Lower-Level Gate Ownership

The CXX bridge surface is checked by `cargo xtask cxx-bridge-gate` (wired into CI
by T2) and by the production CLI and GUI builds. Conformance applicability is
declared in `tests/conformance/participants.json`; see
[repository gates](../development/repository-gates.md).

---

## How To Add a New Public Rust API

Step-by-step workflow for contributors:

1. **Add the `pub fn`/`pub struct` to the `-core` crate's `lib.rs`** -- implement the business logic in the Rust core crate.

2. **Add the C++ bridge entry** in `cpp-bindings/classic-cpp-bridge/src/` -- create a CXX shared struct if it is a DTO, or an opaque type if it is stateful. Use `block_on()` for async wrapping.

3. **Build and test the consumers** through the wrappers: `classic-cli/build_cli.ps1 -Test` and `classic-gui/build_gui.ps1 -Test`.

4. **Commit all changes in the same PR** -- the bridge wrapper and the frontend code that calls it should land together.

If you are translating an older `ClassicLib-rs/...` instruction into the live repo-root workflow, use the shared [`workspace migration matrix`](../workspace-migration-matrix.md) instead of restating the full migration in each binding page.

---

## Reference

- [`AGENTS.md`](../../AGENTS.md) -- project-wide binding guidance
- [`binding-parity-overview.md`](binding-parity-overview.md) -- per-crate binding surface reference
