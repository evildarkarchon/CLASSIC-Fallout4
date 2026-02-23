## Context

The crash log parser uses a single-pass ordered state machine driven by a fixed boundary list. Segment 0 (crashgen settings) is gated on finding `[Compatibility]` or `[Patches]` — both crashgen-owned headers. When a log uses neither, the state machine stalls at boundary index 0 and all segments are empty, silently voiding the entire analysis. The `[Patches]` fallback added for Addictol is a symptom: it solved one instance of the problem by extending the hardcoded list rather than removing the dependency on crashgen-owned names.

Two downstream components compound the issue. `buffout_settings_checks_enabled()` in `settings_validator.rs` and `_is_buffout_4_name()` in `check_crashgen.py` both gate settings analysis on the crashgen name normalizing to `"Buffout4"`, which means Addictol and any future fork receive no named settings checks regardless of whether their schema warrants them. The `CRASHGEN_Ignore` list lives at game level and is shared across all crashgens, so it cannot be tuned per-crashgen.

The codebase already contains a named-segment API (`parse_all_sections()`) returning `HashMap<String, Vec<String>>`. It is used by the Node.js binding but ignored by the orchestrator, which continues to use the positional `parse_segments()`.

## Goals / Non-Goals

**Goals:**
- Segmentation that never depends on crashgen-owned headers for boundary detection
- Named segment map as the primary output type, replacing all positional `segments[N]` access
- Per-crashgen settings schema registry: routing, per-entry ignore lists, and named check sets driven by YAML
- `check_disabled_settings()` runs universally; named checks run only when registered for a crashgen
- A new crashgen fork requires only a YAML registry entry — no code changes to segmentation or validator plumbing

**Non-Goals:**
- FCX mode TOML checker (`toml.rs` hardcoded `Buffout4/` path) — separate change
- Streaming / lazy segmentation for very large logs — out of scope
- Surfacing unknown sections (e.g., `OBJECT REFERENCES:`) as first-class named segments
- Changes to the version registry in `CLASSIC Main.yaml`
- Implementing new named checks for Addictol (no known schema yet)

## Decisions

### 1. Settings section has no start anchor — collect from line 1

**Problem:** Removing `[Compatibility]`/`[Patches]` from the boundary list leaves segment 0 with no start trigger. The state machine never begins collecting.

**Options considered:**
- **A. Implicit start:** Treat line 1 as the implicit start of the settings section; `SYSTEM SPECS:` is its only boundary. Collect from the first line, stop at the first game-output anchor.
- **B. Two-pass discovery:** Scan all lines for game-output anchor positions first, then slice.
- **C. Keep a configurable start-marker list** in YAML (just move the special-case to config).

**Decision: Option A.** The settings section has no game-output start marker by nature — it is the file's preamble. Starting collection at line 1 is the correct model; `SYSTEM SPECS:` is the only true boundary. This simplifies the state machine: segment 0 is no longer driven by a start marker at all, removing the entire class of "wrong section name" failures. Option B adds a pass with no benefit for files already in memory. Option C just relocates the fragility.

**Implementation:** In the revised `parse_all_sections()`, the `settings` key is populated by collecting all lines from the start of the file until the first occurrence of `SYSTEM SPECS:` (exclusive). The existing special-case check at `current_boundary_idx == 0` in `parse_segments()` is deleted.

---

### 2. `parse_all_sections()` becomes the primary output, `parse_segments()` is deprecated

**Problem:** Two parallel APIs exist. The orchestrator uses the positional one; the named one is only used by Node.js.

**Options considered:**
- **A. Extend `parse_all_sections()`** to fully replace `parse_segments()` as the orchestrator's input.
- **B. Add a new `parse_named_segments()` function** and migrate gradually.
- **C. Wrap `parse_segments()` output** into a named map at the orchestrator call site.

**Decision: Option A.** `parse_all_sections()` already exists, is already PyO3-exposed, and already uses the right shape. Extending it to add `xse_modules`, guarantee all keys present, and use anchor-first collection is the minimal change path. Option B creates a third API. Option C adds indirection without removing the fragility from `parse_segments()` itself.

`parse_segments()` is retained as a deprecated shim (returns the positional `Vec<Vec<Arc<str>>>` built from `parse_all_sections()`) to avoid breaking any external callers during transition; it will be removed in a follow-up once callers are migrated.

**`ScanOutput.segments` in the PyO3 binding changes from `list[list[str]]` to `dict[str, list[str]]`.** This is the primary breaking change for Python callers.

---

### 3. XSE sub-section detected by header pattern within MODULES content

**Problem:** The `modules`/`xse_modules` split currently requires knowing the exact header name (`F4SE PLUGINS:`, `SKSE64 PLUGINS:`, etc.). New forks may use different names.

**Options considered:**
- **A. Pattern match:** Within MODULES–PLUGINS content, any line matching `^[A-Z][A-Z0-9 ]+:\s*$` or starting with `[` (trimmed) is treated as a sub-section header.
- **B. Known list in YAML:** Enumerate recognized XSE header names in config.
- **C. Heuristic by content:** Lines without `.dll` extension and not matching a file path format are candidates.

**Decision: Option A.** The pattern `^[A-Z][A-Z0-9 ]+:\s*$` (an all-caps colon-terminated label) is structurally distinctive within a section that otherwise contains file paths and version strings. False-positive risk is low — DLL names do not match this pattern. Known-list (Option B) has the same fragility as the original problem. Content heuristic (Option C) is fragile for edge cases.

The first matching line within the MODULES content becomes the `xse_modules` sub-boundary. Lines before it are `modules`; lines after it (exclusive of the header itself) are `xse_modules`. The matched header line is also stored as `settings_header`-equivalent metadata for the XSE section (used for display only).

---

### 4. `CrashgenRegistry`: hybrid YAML-data / in-code checks

**Problem:** The four named checks (`achievements`, `memory_management`, `archive_limit`, `looksmenu`) are imperative logic and cannot be in YAML. But which checks run for which crashgen is pure data.

**Decision:** Implement a `CrashgenRegistry` struct loaded from YAML at startup. Each entry holds `display_section: String`, `ignore_keys: HashSet<String>`, and `checks: Vec<CheckId>` where `CheckId` is a Rust enum of known check identifiers. The `SettingsValidator` is constructed with a pre-resolved `CrashgenEntry` (looked up by crashgen name before the scan). The four check methods are called only when their `CheckId` is present in the resolved entry's check list.

This satisfies the spec requirement: adding a new crashgen or assigning an existing named check to it requires only a YAML change. Implementing a new named check requires adding a `CheckId` variant and its corresponding method.

**YAML schema addition to `CLASSIC Fallout4.yaml`:**
```yaml
Crashgen_Registry:
  "Buffout 4":
    display_section: "[Compatibility]"
    ignore_keys: [F4EE, WaitForDebugger, Achievements, InputSwitch, AutoOpen,
                  PromptUpload, MemoryManagerDebug, BSTextureStreamerLocalHeap,
                  ArchiveLimit, MemoryManager]
    checks: [achievements, memory_management, archive_limit, looksmenu]
  "Addictol":
    display_section: "[Patches]"
    ignore_keys: []
    checks: []
  default:
    display_section: ""
    ignore_keys: []
    checks: []
```

The existing `Game_Info.CRASHGEN_Ignore` key is removed. `GameVR_Info.CRASHGEN_Ignore` is also removed; VR-specific behavior for MemoryManager is absorbed into a VR-aware `memory_management` check implementation (already present in `settings_validator.rs`).

---

### 5. Name lookup: whitespace-normalized, case-insensitive

The crashgen name parsed from the log header (e.g., `"Buffout 4 v1.37.0 ..."`) is trimmed to its name portion before registry lookup. Lookup normalizes both sides: strip whitespace, lowercase. This matches the existing behavior in `buffout_settings_checks_enabled()` and `_is_buffout_4_name()`, which is correct and should be preserved in the registry lookup.

---

### 6. LRU cache: key strategy unchanged, cached type updated

The segment cache key (xxhash3 of line count + first 10 + middle 5 + last 10 lines) is retained. The cached value type changes from `Vec<Vec<Arc<str>>>` to `HashMap<String, Vec<Arc<str>>>`. Cache capacity (100 entries) is unchanged.

## Risks / Trade-offs

**Positional `segments[N]` access in orchestrator (9 sites)** → Mechanical but high-coverage change. Each site must be audited to confirm the correct named key is substituted. Risk: a wrong key name silently returns an empty list rather than causing a compile error. Mitigation: the named keys are an enum or set of constants, not bare string literals, to catch typos at compile time.

**`ScanOutput.segments` is a breaking PyO3 change** → Python callers that unpack segments by index will break at runtime (dict does not support integer indexing). Mitigation: update all Python callers in the same PR; update the `.pyi` stub and add a runtime test that exercises the dict interface.

**Test fixture updates are large** → Many fixtures embed `"\t[Compatibility]"` as a segment boundary or construct positional segment lists. All must be updated to the named map format. This is mechanical but time-consuming. Mitigation: fixtures are centralized in `tests/fixtures/crash_log_fixtures.py` and `tests/rust_integration/fixtures/`; bulk-update these first.

**Addictol `ignore_keys` is currently unknown** → The registry entry ships with `ignore_keys: []`. `check_disabled_settings()` will produce more warnings for Addictol logs than a tuned list would, since no keys are suppressed. This is conservative (more warnings, not fewer) and acceptable until the community characterizes the schema. The YAML can be updated without a code release.

**XSE sub-header pattern could misfire on unusual module names** → A module with an all-caps colon-terminated name inside the MODULES section would be incorrectly treated as an XSE sub-header boundary. This is unlikely in practice (DLL names don't follow this pattern) but not impossible. Mitigation: the first such line is used as the boundary; if it is wrong, `xse_modules` will have unexpected content but `modules` will still be correct up to that point.

**`parse_segments()` shim adds maintenance surface** → Keeping the deprecated shim means two code paths exist temporarily. Mitigation: mark with `#[deprecated]` in Rust and `# deprecated` in Python, and add a tracking comment pointing to the removal follow-up.

## Migration Plan

1. **Update `parse_all_sections()`** — anchor-first collection for settings, `xse_modules` sub-section detection, guarantee all 7 keys always present, capture `settings_header` metadata. Update LRU cache value type.
2. **Add `CrashgenRegistry`** — YAML schema, loading logic in `classic-config-core`, `CrashgenEntry` struct, `CheckId` enum.
3. **Update `SettingsValidator`** — remove `buffout_settings_checks_enabled()`, accept pre-resolved `CrashgenEntry`, route named checks via entry's check list.
4. **Switch orchestrator** — replace `parse_segments()` call with `parse_all_sections()`, replace all 9 `segments[N]` accesses with named key lookups.
5. **Update PyO3 bindings** — `ScanOutput.segments` type, `.pyi` stub.
6. **Update Python callers** — `find_segments()` return type, `SEGMENT_BOUNDARIES_TEMPLATE` removal, positional unpacking → named key access, `_is_buffout_4_name()` gate removal.
7. **Update YAML** — add `Crashgen_Registry` section, remove `CRASHGEN_Ignore` from `Game_Info` and `GameVR_Info`.
8. **Remove deleted code** — `[Patches]` special case in `parse_segments()`, `SEGMENT_BOUNDARIES_TEMPLATE` in Python, both name-gate functions.
9. **Update tests** — fixture updates, new scenarios for unknown-header segmentation and registry routing.

Steps 1–2 can proceed in parallel. Steps 3–4 depend on step 2. Steps 5–6 depend on step 4. Steps 7–8 can proceed after step 3. Step 9 runs alongside all steps.

**Rollback:** The deprecated `parse_segments()` shim means the orchestrator can be reverted to the positional path without re-implementing the old logic. The YAML change is additive (`Crashgen_Registry` alongside the existing `CRASHGEN_Ignore`); the old key can be restored from version control.

## Open Questions

1. **What are the correct `ignore_keys` for Addictol?** The registry ships with an empty list. This should be populated once the Addictol settings schema is understood. Tracking via a follow-up task rather than blocking this change.

2. **Should `parse_segments()` be removed in this change or a follow-up?** Keeping it as a shim reduces risk but extends the maintenance window. Recommendation: remove it in this change if all callers are updated; otherwise defer. Decision to be made during implementation once caller audit is complete.

3. **VR-specific `MemoryManager` check:** Currently lives in `settings_validator.rs` as a conditional inside `scan_buffout_memorymanagement_settings()`. With the registry approach, should VR vs. non-VR be two separate named checks (`memory_management` and `memory_management_vr`) or should the single check remain VR-aware internally? The simpler path is to keep it VR-aware internally and not expose the distinction in the registry.
