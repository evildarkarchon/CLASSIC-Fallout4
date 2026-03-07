## Why

The crash log segmentation engine treats crashgen-owned section headers (e.g., `[Compatibility]`, `[Patches]`) as required boundary markers, so a fork with a different section name causes the state machine to stall at boundary index 0 — producing empty segments for the entire log. Addictol's arrival exposed this: its `[Patches]` header required a hardcoded special-case fallback, and without it all downstream analysis silently produced no results. The fundamental issue is that game-output anchors (stable across all crashgens) and crashgen-owned headers (variable, fork-defined) are treated identically, which means every new fork risks breaking segmentation until a patch is shipped.

## What Changes

- **BREAKING** Replace ordered-marker segmentation with anchor-first segmentation: the settings section is defined as content before `SYSTEM SPECS:` regardless of what bracket header the crashgen uses; the XSE modules section is the sub-section between `MODULES:` and `PLUGINS:` regardless of its header name
- **BREAKING** Replace `Vec<Vec<Arc<str>>>` positional segment output with a named segment map (`HashMap<String, Vec<Arc<str>>>`) throughout the orchestrator; removes all `segments[N]` index access
- Remove the `[Patches]` special-case fallback in `parse_segments()` — no longer needed with anchor-first approach
- Remove the `buffout_settings_checks_enabled()` name gate in `settings_validator.rs` — replaced by registry routing
- Remove the `_is_buffout_4_name()` name gate in `check_crashgen.py` — replaced by registry routing
- Add per-crashgen schema registry in YAML config: each entry declares its display section name, per-crashgen ignore key list, and named check set
- Move `CRASHGEN_Ignore` from game-level config to per-crashgen registry entries
- Unknown crashgens (not in registry) fall back to `check_disabled_settings()` baseline with an empty ignore list

## Capabilities

### New Capabilities

- `anchor-first-segmentation`: Segmentation engine that anchors boundaries to game-output section markers (`SYSTEM SPECS:`, `PROBABLE CALL STACK:`, `MODULES:`, `PLUGINS:`, `REGISTERS:`, `STACK:`), producing a named segment map. Crashgen-owned headers are captured as segment metadata but do not affect boundary detection.
- `crashgen-schema-registry`: Per-crashgen configuration schema covering display section name, settings key ignore list, and registered named checks. Defines routing behavior (lookup by crashgen name, fallback to default for unknown crashgens) and the baseline `check_disabled_settings()` that runs for all crashgens.

### Modified Capabilities

<!-- No existing specs are affected at the requirements level -->

## Impact

**Rust core**
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/parser.rs` — segmentation algorithm, boundary definitions, `parse_segments()` and `parse_all_sections()` return types
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/orchestrator.rs` — all `segments[N]` index accesses replaced with named map lookups
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/settings_validator.rs` — `buffout_settings_checks_enabled()` gate replaced with registry-driven routing

**Python**
- `ClassicLib/scanning/logs/parser.py` — `extract_segments()` boundary list, `[Patches]` is removed as an explicit boundary
- `ClassicLib/integration/rust/parser_rust.py` — `SEGMENT_BOUNDARIES_TEMPLATE`, response unpacking
- `ClassicLib/scanning/game/check_crashgen.py` — `_is_buffout_4_name()` gate removed

**Config / data**
- `CLASSIC Data/databases/CLASSIC Fallout4.yaml` — `Game_Info.CRASHGEN_Ignore` moved into per-crashgen registry entries; new `crashgens:` registry section added
- `CLASSIC Data/databases/CLASSIC Main.yaml` — no structural changes; version registry entries remain as-is

**PyO3 bindings**
- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/` — `ScanOutput.segments` type changes from `list[list[str]]` to `dict[str, list[str]]`; all callers updated
