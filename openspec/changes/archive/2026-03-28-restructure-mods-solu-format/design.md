## Context

`Mods_SOLU` is currently loaded as `IndexMap<String, String>` in `classic-config-core`, exposed through bindings as key/value data, and passed into `classic-scanlog-core` as `mods_solu`. Detection uses the YAML key as the only match criterion, then renders the first line of the value as the readable title and the remaining lines as the body text. That makes a single YAML field responsible for identity, matching, display text, and formatting behavior.

This change is cross-cutting because it touches the game database YAML, Rust config models, scanlog detection/reporting, binding contracts, parity fixtures, and contributor API docs. It also changes a binding-facing config shape, so the break needs to be explicit and documented rather than hidden behind partial compatibility helpers.

## Goals / Non-Goals

**Goals:**
- Replace the free-form `Mods_SOLU` map with a structured ordered entry model that separates identity, criteria, readable name, and description.
- Support grouped match criteria with simple `any` or `all` semantics plus optional false-positive `exceptions`.
- Keep matching deterministic and compatible with the current substring-based plugin detection model.
- Generate report entries from explicit structured fields so results rendering no longer depends on splitting the first line from a blob.
- Expose the same structured data through Rust, Python, Node, and C++ config surfaces and update the affected API docs.

**Non-Goals:**
- Redesign `Mods_FREQ`, `Mods_CONF`, `Mods_CORE`, or unrelated YAML sections.
- Introduce nested boolean logic, regex-based criteria, or arbitrary expression parsing for mod matching.
- Rewrite the broader markdown/results-view rendering pipeline beyond switching `Mods_SOLU` entries to structured inputs.

## Decisions

### 1. Represent `Mods_SOLU` as an ordered entry list
`Mods_SOLU` will move from a string map to an ordered sequence of `ModSolutionEntry` records. Each record will carry `id`, `criteria`, `exceptions`, `name`, and `description`.

Representative YAML shape:

```yaml
Mods_SOLU:
  - id: high-resolution-dlc
    criteria:
      any:
        - DLCUltraHighResolution
    exceptions: []
    name: High Resolution DLC
    description: |
      I STRONGLY ADVISE AGAINST USING IT...
```

Rationale: a sequence preserves author-controlled order and decouples identity from the match keys. A map keyed by criterion or id cannot express grouped criteria cleanly without inventing nested map conventions that are harder to read and harder to bind.

Alternatives considered:
- Keep `IndexMap<String, String>` and encode extra metadata inside the value string. Rejected because it preserves the current ambiguity and keeps rendering coupled to text parsing.
- Use an `IndexMap<String, ModSolutionEntry>` keyed by `id`. Rejected because the YAML would still need a nested object per id and ordering is clearer as an explicit sequence.

### 2. Model criteria as a single grouped matcher with optional exceptions
Internally, each entry will normalize into a structured matcher with exactly one active mode: `any(Vec<String>)` or `all(Vec<String>)`. `exceptions` will be a separate `Vec<String>` of case-insensitive plugin-filename substrings.

Rationale: the user requirement is grouped matching with either disjunctive or conjunctive behavior plus simple exclusions. A one-group model covers that need without adding a boolean expression language that would be harder to validate, document, and expose across bindings.

Alternatives considered:
- A flat `mode: any|all` plus `values: []` shape. Rejected because `criteria.any` / `criteria.all` is easier to read in YAML and more self-describing in docs.
- Nested boolean trees (`all` containing `any`, etc.). Rejected as unnecessary complexity for the current problem.

### 3. Add a dedicated structured `Mods_SOLU` detector
`classic-scanlog-core` will gain a dedicated matcher for structured solution entries instead of routing them through `detect_mods_single(IndexMap<String, String>)`. The matcher will evaluate grouped criteria and exceptions, capture the plugin ids that satisfied the match, and sort detected entries by the earliest matched plugin load-order id so visible ordering stays stable.

Rationale: the existing single-map detector assumes one criterion per entry and couples report text extraction to the stored string value. Extending it would either add awkward optional parameters or force structured data to be flattened and then re-expanded during rendering.

Alternatives considered:
- Reuse `detect_mods_single()` by precomputing synthetic keys and concatenated values. Rejected because it cannot express `all` matching or exception suppression without obscuring the new rules.
- Make `detect_mods_single()` fully generic for every mod database. Rejected because only `Mods_SOLU` is changing shape here, and a generic abstraction would add churn to unaffected paths.

### 4. Keep the API break explicit across bindings and docs
`YamlDataCore.game_mods_solu` and the corresponding Node, Python, and C++ bridge exposures will move to structured entries in the same change. The affected contributor docs under `docs/api/` will be updated together, especially the YAML schema page, scanlog-core behavior docs, and binding contract pages.

Rationale: a parallel legacy map API would discard grouped criteria and exceptions or require maintaining two competing interpretations of the same source data. Making the break explicit keeps the contract coherent and forces parity fixtures and docs to stay aligned.

Alternatives considered:
- Add new structured getters while retaining the old map getters. Rejected because the old shape cannot faithfully represent the new matching rules and would prolong duplicated maintenance.

## Risks / Trade-offs

- [Binding/API breakage] Existing consumers expect `game_mods_solu` to be key/value data. → Mitigation: update all in-repo bindings, parity fixtures, and `docs/api/` pages in the same change so failures surface at compile/test time.
- [Behavior drift during matcher rewrite] `any`/`all` and exception handling could change detection order or produce unexpected matches. → Mitigation: add focused tests for YAML parsing, matcher semantics, exception suppression, and report ordering based on matched plugin ids.
- [Manual YAML migration errors] Converting the Fallout 4 database section by hand could introduce malformed or duplicated ids. → Mitigation: migrate the database in the same change as parser tests and keep ids stable and human-auditable.
- [UI expectations remain markdown-based] Structured entries improve how text is constructed, but the broader results view still renders markdown. → Mitigation: limit this change to cleaner entry construction and avoid claiming a full rendering-system redesign.

## Migration Plan

1. Add the new `Mods_SOLU` entry types and parser path in `classic-config-core`, then update the game database YAML and config fixtures to the structured sequence format.
2. Replace the `Mods_SOLU` detection path in `classic-scanlog-core` with the structured matcher and explicit name/description rendering.
3. Update Python, Node, and C++ binding exposures to mirror the structured entry model, along with parity fixtures and binding-facing tests.
4. Refresh `docs/api/README.md`, `classic-config-core-yaml-schema.md`, `classic-scanlog-core.md`, and `classic-cpp-bridge-data-entrypoints.md` to describe the new contract.
5. Validate with Rust unit/integration tests plus Python/Node parity checks relevant to the changed surfaces.

Rollback is straightforward because the change affects source-controlled YAML and code contracts only; reverting the entry model, YAML conversion, and binding/doc updates restores the prior behavior.

## Open Questions

None at proposal time.
