# Phase 3: FCX State Hardening - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix FCX singleton reset correctness and expose the minimal binding APIs needed for clean scan-session isolation. This phase covers the core reset contract, automatic pre-scan resets in C++ and Node, explicit reset entrypoints, Node-side FCX issue inspection, and the required contention/carryover tests. It does not broaden into a general binding redesign, does not reshape existing scan result payloads, and does not add C++ FCX issue inspection in this phase.

</domain>

<decisions>
## Implementation Decisions

### Node FCX API Contract
- **D-01:** Node standardizes on flat top-level exports named `resetFcxGlobalState()` and `getFcxConfigIssues()`. Do not use the shorter `resetFcxState()` / `getFcxIssues()` naming pair.
- **D-02:** `getFcxConfigIssues()` returns structured issue objects, not preformatted report text.

### Scan-Session Reset Policy
- **D-03:** C++ and Node scan entrypoints auto-reset FCX global state at the start of every scan session, covering both single-log and batch APIs.
- **D-04:** Explicit reset APIs remain available even though scan entrypoints perform the reset automatically.

### Reset Error Handling
- **D-05:** Phase 3 keeps the typed core contract `Result<(), FcxResetError>` for FCX reset behavior.
- **D-06:** A real reset failure is a scan-start failure in the binding layers; do not warn and continue with potentially stale FCX state.
- **D-07:** The `unnecessary` / no-op reset outcome remains non-fatal and stays on the normal execution path.

### Issue Access Scope
- **D-08:** FCX issue inspection lands behind a standalone Node getter and does not get added to `JsAnalysisResult` or other existing scan result payloads.
- **D-09:** C++ remains reset-only in this phase. Do not add C++ FCX issue inspection as part of Phase 3.

### the agent's Discretion
- Exact `FcxResetError` variant names and how each maps onto the existing binding error style, as long as true failures abort scan start and `unnecessary` stays non-fatal.
- Exact DTO naming/field reuse for Node issue objects, as long as the getter returns structured FCX issue data and keeps the locked function names above.
- Exact helper placement for the pre-scan reset calls, as long as every public C++ and Node single/batch scan session path is covered.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Planning
- `.planning/ROADMAP.md` - Phase 3 goal, requirement mapping, and success criteria
- `.planning/PROJECT.md` - milestone constraints: thin bindings, parity in scope, and no broad feature redesign
- `.planning/REQUIREMENTS.md` - `SAFE-01`, `SAFE-02`, `SAFE-03`, `SAFE-04`, `CONS-02`, `TEST-01`, and `TEST-04`
- `.planning/STATE.md` - current milestone note that `CONS-02` is paired with `SAFE-01` in this phase

### Public API And Parity Docs
- `docs/api/README.md` - required contributor reading order and rule to update API docs when public surfaces change
- `docs/api/classic-scanlog-core.md` - public FCX/core scanlog items and integration flow
- `docs/api/binding-parity-overview.md` - current C++/Node/Python scanlog surface boundaries and parity notes

### Core FCX State
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs` - `GLOBAL_FCX_HANDLER`, `ConfigIssue`, current `try_lock()` reset behavior, and cached FCX session state

### Binding Integration Points
- `ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs` - current Node scan entrypoints and public scanlog exports
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` - current C++ scan entrypoints and CXX extern surface
- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/fcx_handler.rs` - existing Python FCX reset hook and issue exposure used as the closest binding reference

### Validation Targets
- `ClassicLib-rs/node-bindings/classic-node/__test__/scanlog.spec.ts` - Node scanlog contract tests and the place to add FCX carryover coverage

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `classic_scanlog_core::FcxModeHandler` and `GLOBAL_FCX_HANDLER` already own the FCX session cache and issue list in core
- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/fcx_handler.rs` already demonstrates a reset hook plus structured issue exposure over the same core state
- `ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs` already follows the flat `#[napi]` free-function export style the new Node FCX APIs should match
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` already exposes standalone helper functions through the `extern "Rust"` block in `classic::scanner`

### Established Patterns
- Business logic and state semantics stay in Rust core; bindings adapt them rather than reimplementing behavior
- Node bindings expose camelCase top-level functions and `#[napi(object)]` DTOs
- The C++ bridge exposes narrow synchronous helpers in the `classic::scanner` namespace
- Public binding changes are expected to update source-backed API docs and parity-facing contract artifacts in the same change

### Integration Points
- Core reset semantics live in `ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs`
- Node auto-reset coverage needs to include `processLog`, `processLogsBatch`, `processLogWithYamlContent`, and `processLogsBatchWithYamlContent`
- C++ auto-reset coverage needs to include the public scan-session entrypoints in `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`
- Validation spans core FCX tests plus Node binding tests for same-process state carryover

</code_context>

<specifics>
## Specific Ideas

- Keep the new Node names explicit: `resetFcxGlobalState()` and `getFcxConfigIssues()`.
- Preserve existing scan result payload shapes; FCX issue inspection is a separate API, not embedded report metadata.

</specifics>

<deferred>
## Deferred Ideas

- C++ FCX issue inspection is deferred beyond Phase 3.
- Embedding FCX issues into existing scan result payloads is deferred; this phase keeps diagnostics as a separate getter surface.

</deferred>

---

*Phase: 03-fcx-state-hardening*
*Context gathered: 2026-04-05*
