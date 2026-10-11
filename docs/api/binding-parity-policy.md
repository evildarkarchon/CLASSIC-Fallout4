# Binding Parity Policy

Reference: [`AGENTS.md`](../../AGENTS.md), [`binding-parity-overview.md`](binding-parity-overview.md).

---

## One-Tier Policy Statement

All Rust public API symbols in business-logic `-core` crates are exposed through the one binding surface, the C++ bridge (CXX). The Python and Node bindings retired with ADR-0010 (in [`docs/adr/`](../adr/)). There is no deferred tier, no backlog tier, and no graduated promotion process.

When a new `pub fn` or `pub struct` is added to a `-core` crate's `lib.rs`, the bridge must expose it before CI passes. The only current exception is `classic-resource-core`, which has no dedicated C++ bridge module -- its functionality is accessed transitively through the `classic-file-io-core` bridge surface.

### Scope: methods from workspace-internal traits

Implementing a workspace-internal trait on a `-core` type does not by itself create a parity obligation. The obligation attaches to the crate's own exported surface -- the `pub fn` and `pub struct` entries a binding is meant to publish -- not to every method a shared trait makes callable. `Vocabulary` from [`classic-vocabulary`](classic-vocabulary.md) is the current case: `as_str()` supplies the Vocabulary Token that the bindings already published under their own names, so adopting it changes nothing on any surface, while `label()` becomes projectable rather than automatically projected. A Display Label crosses a binding seam when a frontend needs to render it, and that projection is a deliberate, separately reviewed addition with its own baseline and coverage-registry cost.

Note that the gate cannot decide this for you. The surface parser matches `pub fn` and `pub struct` at the start of a line, and trait-impl members carry no `pub`, so a trait method is invisible to them either way. Treat this as a contributor judgement recorded in review, not a check CI will make.

### Scope: inherent methods that supply an already-published value

The same reasoning covers an inherent method added to a type a binding already publishes. `Revision::token()` and `Revision::from_token()` in [`classic-user-settings-core`](classic-user-settings-core.md) are the current case: each binding previously carried its own byte-identical copy of that formatting, so consolidating it changes which code produces the revision strings the bridge already exposes, not which strings it exposes. No new adapter symbol is warranted, and no contract row moves.

For the semantic Autoscan Report Contribution architecture, parity is both
positive and negative. CXX exposes the six public Focused
Semantic Analyzers, owned inputs/results, and shared typed errors. They must not expose
the private contribution collector, Autoscan Report Assembly, report
primitives, or fragment-producing compatibility aliases. A breaking removal is
complete only when authored wrappers, compliance reports, and committed parity
baselines all describe that same final surface. See
[ADR-0005](../adr/0005-semantic-autoscan-report-contributions.md).

---

## Canonical Conformance Verdict

The repository conformance verdict is the conformance-only `full` profile:

```powershell
python tools/binding_compliance/check_compliance.py --repo-root . --profile full --receipt-directory tools/binding_compliance/artifacts/downloaded
```

Only `--profile full` with all family receipts can certify repository-wide
conformance. Full aggregation counts every source parity occurrence and fails on
missing families or uncovered runtime rows. Registry metadata never supplies that
proof. The static requirement catalog and its retained-gate evidence retired with
the Python and Node bindings; the checks CI now runs as direct steps are listed in
[repository gates](../development/repository-gates.md).

Crash Log Scan Run and User Settings have blocking executable conformance obligations. Rust,
CXX on both MSVC and clang-cl, CLI and GUI on both compiler legs,
and TUI must emit current same-revision receipts for their exact applicable
scopes. Central validation requires the full scenario and observation-family
denominator plus every source-owned consumer obligation. Missing, skipped,
stale, malformed, duplicate, or semantically mismatched evidence fails the
applicable workflow. These receipts run conjunctively with the source parity,
runtime, Rust-variant, and native wrapper gates; promotion
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

### CXX Gate

- **Script:** `tools/cxx_api_parity/check_parity_gate.py`
- **Baseline:** `docs/implementation/cxx_api_parity/baseline/parity_contract.json`
- **Baseline generator:** `tools/cxx_api_parity/generate_baseline.py`
- **Contributor docs:** [`docs/api/cxx-parity-gate.md`](cxx-parity-gate.md)
- **Run command:** `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`

---

## When Gates Refresh

The gate refreshes when the tracked contract drifts from the live Rust surface. CXX refreshes through the repo-root parity scripts.

Workflow:

1. Run the gate to detect drift
2. If drift is intentional, regenerate or refresh the owned baseline/artifacts for that surface
3. Run the gate again to confirm zero drift
4. Commit the updated baseline in the same change

### Baseline Artifacts Are Byte-Stable

Regenerating or refreshing a baseline when nothing has actually changed produces **no diff at all**. The generators and gates carry the committed `generated_at_utc` forward whenever the regenerated payload matches the committed one, so an unchanged surface never rewrites the tracked files. The `- Generated:` markdown headers follow automatically, because they render from the corresponding JSON payload.

Two consequences for reviewers:

- An empty `git status` after a refresh means "no drift", not "the refresh did not run".
- A timestamp change in a baseline artifact is a real signal: it marks when that surface last actually changed.

The shared implementation is `tools/parity_artifact_io.py`; the byte-stability property is locked by `tools/test_parity_artifact_io.py` plus `tools/cxx_api_parity/tests/test_baseline_timestamp_stability.py`.

### Shared Gate Tooling

Two modules under `tools/` back the CXX gate:

| Module | Owns |
|---|---|
| `parity_rust_surface.py` | Parsing the public Rust surface — crate source collection, `pub use` expansion, symbol extraction |
| `parity_artifact_io.py` | Reading, comparing, and writing artifacts — `write_json`, `stable_id_hash`, `sync_baseline_artifacts`, timestamp preservation |

### What a Contract Row Must Prove

A row's `rustSymbol` check used to be satisfied by *any* symbol of any kind. That is weaker than it reads, and placeholder rows accumulated behind it — at one point 82 unrelated binding exports all named the Rust module `path_core`, and a gate still reported 913/913 matched. These rules now hold:

1. **A binding export may not map to a Rust module.** A module match verifies nothing about the export. Map the row to the specific core symbol the wrapper actually uses.
2. **`@rust` source-inventory rows may name a module.** They record Rust-only source. They do not claim that the module implements that export.
3. **An export with no verified counterpart must say so.** Set `rustSymbol` to `null` and add an `unmappedReason`. The row is then counted in the diff report's `tier1_unmapped` rather than being disguised as a match. A `null` `rustSymbol` without a reason is a malformed row.
`tier1_unmapped` is **tracked debt, not drift** — it does not fail the gate, but it is the number to drive toward zero. It is deliberately separate from `tier1_matched` so neither figure lies.

---

## How To Add a New Public Rust API

Step-by-step workflow for contributors:

1. **Add the `pub fn`/`pub struct` to the `-core` crate's `lib.rs`** -- implement the business logic in the Rust core crate.

2. **Add the C++ bridge entry** in `cpp-bindings/classic-cpp-bridge/src/` -- create a CXX shared struct if it is a DTO, or an opaque type if it is stateful. Use `block_on()` for async wrapping.

3. **Refresh the owned baseline:**
   ```bash
   python tools/cxx_api_parity/generate_baseline.py --repo-root .
   ```

4. **Run the gate to verify zero drift:**
   ```bash
   python tools/cxx_api_parity/check_parity_gate.py --repo-root .
   ```

5. **Commit all changes in the same PR** -- bridge wrappers, baseline refreshes, and gate verification should land together.

If you are translating an older `ClassicLib-rs/...` instruction into the live repo-root workflow, use the shared [`workspace migration matrix`](../workspace-migration-matrix.md) instead of restating the full migration in each binding page.

---

## Reference

- [`AGENTS.md`](../../AGENTS.md) -- project-wide binding guidance
- [`binding-parity-overview.md`](binding-parity-overview.md) -- per-crate binding surface reference
- [`binding-contract-refresh-note.md`](binding-contract-refresh-note.md) -- when to refresh contract artifacts
- [`cxx-parity-gate.md`](cxx-parity-gate.md) -- CXX gate internals
