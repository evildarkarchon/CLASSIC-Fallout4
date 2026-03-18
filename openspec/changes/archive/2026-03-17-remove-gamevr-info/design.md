## Context

The "deprecate-gamevr-info" change (archived 2026-02-23) migrated all Rust core consumers away from `GameVR_Info`. However, residual references remain in:

1. **C++ frontends** -- `scanner.cpp` and `scancontroller.cpp` still branch on VR to pick `"GameVR_Info.Docs_Folder_XSE"` vs `"Game_Info.Docs_Folder_XSE"`.
2. **Node bindings** -- `run-scan.ts` builds the key path using VR branching; test fixtures and tests embed `GameVR_Info` sections in YAML literals.
3. **Rust API** -- `get_config_suffix()` in `classic-registry-core` exists solely to build `"GameVR_Info"` key names. Its doc comment references the dead namespace. The Python `.pyi` stub mirrors it.
4. **YAML template** -- `CLASSIC Main.yaml` `default_localyaml` includes a `GameVR_Info` block that gets written into every new local YAML.
5. **Comments** -- `classic-tui/src/app.rs` has deprecation comments referencing `GameVR_Info`.

All Rust core crates already use `"Game_Info"` unconditionally; the Version Registry is the single source of truth for version-specific metadata. This change finishes the cleanup.

## Goals / Non-Goals

**Goals:**
- Eliminate every `GameVR_Info` string literal, key-path branch, doc comment, and test fixture across the entire codebase.
- Remove the `get_config_suffix()` function from `classic-registry-core` and its Python/Node binding exports.
- Update the `default_localyaml` template in `CLASSIC Main.yaml` so newly generated local YAML files have no `GameVR_Info` block.
- Update the `version-registry-game-metadata` spec to reflect the completed removal.

**Non-Goals:**
- Changing any Version Registry data model or adding new fields.
- Modifying the `Game_Info` namespace behavior (it remains unchanged).
- Touching the game database YAML (`CLASSIC Fallout4.yaml`) `GameVR_Info` section -- this was already removed by the prior change.

## Decisions

### 1. Remove `get_config_suffix()` entirely rather than deprecating it

**Decision**: Delete the function from `classic-registry-core`, its Python binding, and its Node binding.

**Rationale**: The function's only purpose is to return `"VR"` so callers can interpolate `Game{suffix}_Info`. Since all consumers now use `"Game_Info"` unconditionally, there are zero legitimate callers. A deprecation period provides no value because the function was already documented as deprecated in the prior change.

**Alternative considered**: Keep the function but mark it `#[deprecated]`. Rejected because there are no callers and it would just accumulate dead code.

### 2. C++ frontends use `"Game_Info.Docs_Folder_XSE"` unconditionally

**Decision**: In `scanner.cpp`, replace the VR-branching ternary with a hardcoded `"Game_Info.Docs_Folder_XSE"` string. In `scancontroller.cpp`, remove the loop over both key paths and read `"Game_Info.Docs_Folder_XSE"` directly.

**Rationale**: The local YAML is now written with `Game_Info` for all versions. There is no runtime scenario where data lives under `GameVR_Info` in local YAML.

### 3. Node binding `run-scan.ts` uses `"Game_Info"` unconditionally

**Decision**: Remove the VR ternary in `resolveXsePath()` and hardcode `"Game_Info"` as the local key.

**Rationale**: Same as C++ -- local YAML only uses `Game_Info`.

### 4. Test fixtures stripped of `GameVR_Info` sections

**Decision**: Remove `GameVR_Info` blocks from `cli.fixtures.ts`, `config.spec.ts`, and `runtime.node.test.mjs` YAML literals.

**Rationale**: These fixtures model the expected YAML format. Including `GameVR_Info` misleads future test authors into thinking the namespace is active.

## Risks / Trade-offs

- **[Risk] Users with old local YAML files that still have `GameVR_Info` blocks.** -> Mitigation: Not a concern for this change. The runtime already reads `Game_Info` unconditionally. Old `GameVR_Info` blocks in user local YAML are simply ignored -- they are inert data. No migration needed.
- **[Risk] Removing `get_config_suffix()` breaks external callers.** -> Mitigation: The function is only exported in Python and Node bindings. No external consumers exist outside this project. The Python binding is internal-only. The Node binding is not published.
- **[Risk] `scancontroller.cpp` loop removal misses an edge case.** -> Mitigation: The loop currently tries `Game_Info` first, then `GameVR_Info` as fallback. Since VR local YAML has used `Game_Info` since the deprecation change, the fallback path is dead. Build + existing integration tests verify correctness.
