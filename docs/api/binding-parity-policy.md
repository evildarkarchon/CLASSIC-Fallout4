# Binding Parity Policy

Reference: [`AGENTS.md`](../../AGENTS.md), [`binding-parity-overview.md`](binding-parity-overview.md).

---

## One-Tier Policy Statement

All Rust public API symbols in business-logic `-core` crates are exposed through all three binding surfaces: C++ (CXX), Node (NAPI-RS), and Python (PyO3). There is no deferred tier, no backlog tier, and no graduated promotion process.

When a new `pub fn` or `pub struct` is added to a `-core` crate's `lib.rs`, all three bindings must expose it before CI passes. The only current exception is `classic-resource-core`, which has no dedicated C++ bridge module -- its functionality is accessed transitively through the `classic-file-io-core` bridge surface.

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
