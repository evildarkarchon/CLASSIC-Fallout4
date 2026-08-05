# Binding Parity Policy

Reference: [`AGENTS.md`](../../AGENTS.md), [`binding-parity-overview.md`](binding-parity-overview.md).

---

## One-Tier Policy Statement

All Rust public API symbols in business-logic `-core` crates are exposed through all three binding surfaces: C++ (CXX), Node (NAPI-RS), and Python (PyO3). There is no deferred tier, no backlog tier, and no graduated promotion process.

When a new `pub fn` or `pub struct` is added to a `-core` crate's `lib.rs`, all three bindings must expose it before CI passes. The only current exception is `classic-resource-core`, which has no dedicated C++ bridge module -- its functionality is accessed transitively through the `classic-file-io-core` bridge surface.

### Scope: methods from workspace-internal traits

Implementing a workspace-internal trait on a `-core` type does not by itself create a parity obligation. The obligation attaches to the crate's own exported surface -- the `pub fn` and `pub struct` entries a binding is meant to publish -- not to every method a shared trait makes callable. `Vocabulary` from [`classic-vocabulary`](classic-vocabulary.md) is the current case: `as_str()` supplies the Vocabulary Token that all three bindings already published under their own names, so adopting it changes nothing on any surface, while `label()` becomes projectable rather than automatically projected. A Display Label crosses a binding seam when a frontend needs to render it, and that projection is a deliberate, separately reviewed addition with its own baseline and coverage-registry cost.

Note that the gates cannot decide this for you. Both surface parsers match `pub fn` and `pub struct` at the start of a line, and trait-impl members carry no `pub`, so a trait method is invisible to them either way. Treat this as a contributor judgement recorded in review, not a check CI will make.

For the semantic Autoscan Report Contribution architecture, parity is both
positive and negative. CXX, Node, and Python expose the six public Focused
Semantic Analyzers, owned inputs/results, and shared typed errors. They must not expose
the private contribution collector, Autoscan Report Assembly, report
primitives, or fragment-producing compatibility aliases. A breaking removal is
complete only when authored wrappers, generated declarations, maintained
stubs, runtime coverage registries, compliance reports, and committed parity
baselines all describe that same final surface. See
[ADR-0005](../adr/0005-semantic-autoscan-report-contributions.md).

---

## Canonical Compliance Gate

The canonical binding gate is the compliance suite:

```powershell
python tools/binding_compliance/check_compliance.py --repo-root . --profile ci
```

The suite owns the top-level pass/fail result, policy mapping, structured report, and known-gap report. The surface-specific gates below remain available as lower-level checks and focused debugging commands.

See [`binding-compliance-suite.md`](binding-compliance-suite.md).

---

## Lower-Level Gate Ownership

### CXX Gate

- **Script:** `tools/cxx_api_parity/check_parity_gate.py`
- **Baseline:** `docs/implementation/cxx_api_parity/baseline/parity_contract.json`
- **Baseline generator:** `tools/cxx_api_parity/generate_baseline.py`
- **Contributor docs:** [`docs/api/cxx-parity-gate.md`](cxx-parity-gate.md)
- **Run command:** `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`

### Python Gate

- **Script:** `tools/python_api_parity/check_parity_gate.py`
- **Baseline:** `docs/implementation/python_api_parity/baseline/parity_contract.json`
- **Baseline generator:** `tools/python_api_parity/generate_baseline.py`
- **Run command:** `python tools/python_api_parity/check_parity_gate.py --repo-root .`

### Node Gate

- **Baseline:** `docs/implementation/node_api_parity/baseline/parity_contract.json`
- **Primary working directory:** `node-bindings/classic-node/`
- **Run command:** `bun run parity:gate`
- **Intentional refresh command:** `bun run parity:gate:update-baseline`
- **Follow-up checks:** `bun run test:bun`, `bun run test:node`, and `bun run dts:freshness:check`

---

## When Gates Refresh

Gates refresh when the tracked contract drifts from the live Rust surface. CXX and Python refresh through the repo-root parity scripts, while Node refreshes through the `classic-node` package workflow.

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

The shared implementation is `tools/parity_artifact_io.py`; the byte-stability property is locked by `tools/test_parity_artifact_io.py` plus a `test_baseline_timestamp_stability.py` in each of the three `tools/*_api_parity/tests/` suites.

### Shared Gate Tooling

Three modules under `tools/` are shared by the per-binding gates. Change them with the understanding that all three gates consume them:

| Module | Owns |
|---|---|
| `parity_rust_surface.py` | Parsing the public Rust surface — crate source collection, `pub use` expansion, symbol extraction |
| `parity_artifact_io.py` | Reading, comparing, and writing artifacts — `write_json`, `stable_id_hash`, `sync_baseline_artifacts`, timestamp preservation |
| `binding_parity_runtime_coverage.py` | Runtime coverage summaries |

The Node and Python gates previously carried independent copies of the Rust parser, which let them disagree about which Rust exports exist while both reported success. They now share one parser and differ only in their **crate list** — `RUST_TARGET_CRATES` / `RUST_OWNER_BY_CRATE` stay per-gate and are passed into `parse_rust_surface()` at call time. When you add a `-core` crate that a binding depends on, add it to that binding's crate list; a crate missing from the list is invisible to that gate, and any contract row naming one of its symbols will be rejected as "not in the parsed Rust surface".

### What a Contract Row Must Prove

A row's `rustSymbol` check used to be satisfied by *any* symbol of any kind. That is weaker than it reads, and placeholder rows accumulated behind it — at one point 82 unrelated Node exports all named the Rust module `path_core`, and the gate still reported 913/913 matched. Three rules now hold:

1. **A binding export may not map to a Rust module.** A module match verifies nothing about the export. Map the row to the specific core symbol the wrapper actually uses. Two resolvers derive that from the binding source rather than guessing — `tools/node_api_parity/resolve_node_rust_symbols.py` for NAPI wrappers and `tools/python_api_parity/resolve_python_rust_symbols.py` for PyO3 wrappers. Run either against the repo to see the proposed mapping and the evidence behind it.
2. **`@rust` proxy rows may name a module.** They carry no binding export and exist precisely to record Rust-only surface.
3. **An export with no verified counterpart must say so.** Set `rustSymbol` to `null` and add an `unmappedReason`. The row is then counted in the diff report's `tier1_unmapped` rather than being disguised as a match. A `null` `rustSymbol` without a reason is a malformed row.

`tier1_unmapped` is **tracked debt, not drift** — it does not fail the gate, but it is the number to drive toward zero. It is deliberately separate from `tier1_matched` so neither figure lies.

### Resolver Evidence Tiers

Both resolvers rank evidence rather than pattern-matching on names alone, because the obvious guess is sometimes wrong. Strongest first:

| Tier | Evidence |
|---|---|
| `exact` | The wrapper calls a crate-qualified core symbol of the same name |
| `from_impl` | `impl From<CoreType> for Wrapper` |
| `conversion_fn` | A helper `fn …(x: CoreType) -> JsDto` pairs a DTO with its core type |
| `inner_field` | The wrapper struct holds a field of a core type — the newtype pattern |
| `js_prefix` / `name_match` | The exported name matches a core type, case-insensitively for acronyms |
| `core_method` | A method called on a core-typed value, when that method exists in the surface |
| `core_assoc` | `CoreType::assoc(…)`, an enum variant, or a `parse::<CoreType>()` turbofish |
| `qualified` / `imported` | Any other core symbol the wrapper references — weakest; `imported` is not auto-applied |

The ordering earns its keep. `FormIDAnalyzer` exists in `classic-scanlog-core`, so a name match looks right — but the PyO3 wrapper is `PyRustFormIDAnalyzer { inner: RustFormIDAnalyzer }`, and `inner_field` picks the type actually wrapped.

Two filters keep the weaker tiers honest:

- **Plumbing is never a counterpart.** `get_runtime`, `block_on`, `*Error` appear in nearly every wrapper.
- **Ubiquitous method names are never a counterpart.** Almost every crate defines a `new`, `all`, or `as_str`, so matching one says only "this wrapper called a constructor". Without this filter the resolver produced `checkForUpdates -> new` and `getAllGameIds -> all` — as meaningless as the module matches it exists to replace.

If a resolver reports `unresolved`, that is a real answer: the export may have no core counterpart. Seven Node DTOs (`QueryParam`, `ResourceCount`, `JsBatchEntry` …) are assembled entirely in the binding layer and have none. Record those with `rustSymbol: null` and an `unmappedReason` rather than inventing one.

---

## How To Add a New Public Rust API

Step-by-step workflow for contributors:

1. **Add the `pub fn`/`pub struct` to the `-core` crate's `lib.rs`** -- implement the business logic in the Rust core crate.

2. **Add the C++ bridge entry** in `cpp-bindings/classic-cpp-bridge/src/` -- create a CXX shared struct if it is a DTO, or an opaque type if it is stateful. Use `block_on()` for async wrapping.

3. **Add the Node NAPI wrapper** in `node-bindings/classic-node/src/` -- NAPI auto-converts `snake_case` to `camelCase` for JS consumers. Add the module import in `src/lib.rs` if it is a new file.

4. **Add the Python PyO3 wrapper** in `python-bindings/classic-*-py/src/` and update the matching `.pyi` stub file with the new public surface.

5. **Refresh the owned per-surface artifacts:**
   ```bash
   python tools/cxx_api_parity/generate_baseline.py --repo-root .
   python tools/python_api_parity/generate_baseline.py --repo-root .
   cd node-bindings/classic-node && bun run parity:gate:update-baseline
   ```

6. **Run all three gates to verify zero drift:**
   ```bash
   python tools/cxx_api_parity/check_parity_gate.py --repo-root .
   python tools/python_api_parity/check_parity_gate.py --repo-root .
   cd node-bindings/classic-node && bun run parity:gate
   ```

   Then finish the Node flow with `bun run test:bun`, `bun run test:node`, and `bun run dts:freshness:check` from `node-bindings/classic-node/`.

7. **Commit all changes in the same PR** -- binding wrappers, stub updates, baseline refreshes, and gate verification should land together.

If you are translating an older `ClassicLib-rs/...` instruction into the live repo-root workflow, use the shared [`workspace migration matrix`](../workspace-migration-matrix.md) instead of restating the full migration in each binding page.

---

## Reference

- [`AGENTS.md`](../../AGENTS.md) -- project-wide binding guidance
- [`binding-parity-overview.md`](binding-parity-overview.md) -- per-crate binding surface reference
- [`binding-contract-refresh-note.md`](binding-contract-refresh-note.md) -- when to refresh contract artifacts
- [`node-python-contract-map.md`](node-python-contract-map.md) -- where Node and Python contract files live
- [`cxx-parity-gate.md`](cxx-parity-gate.md) -- CXX gate internals
