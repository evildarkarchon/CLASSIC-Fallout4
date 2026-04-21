# Binding Parity Policy

Reference: [`AGENTS.md`](../../AGENTS.md), [`binding-parity-overview.md`](binding-parity-overview.md).

---

## One-Tier Policy Statement

All Rust public API symbols in business-logic `-core` crates are exposed through all three binding surfaces: C++ (CXX), Node (NAPI-RS), and Python (PyO3). There is no deferred tier, no backlog tier, and no graduated promotion process.

When a new `pub fn` or `pub struct` is added to a `-core` crate's `lib.rs`, all three bindings must expose it before CI passes. The only current exception is `classic-resource-core`, which has no dedicated C++ bridge module -- its functionality is accessed transitively through the `classic-file-io-core` bridge surface.

---

## Gate Ownership

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
