## Why

The `GameVR_Info` YAML namespace was used to store VR-specific runtime paths and static metadata, but the "deprecate-gamevr-info" change already migrated all Rust core consumers to use `Game_Info` unconditionally and source static metadata from the Version Registry. Residual `GameVR_Info` references remain in C++ frontends, Node bindings, test fixtures, YAML templates, doc comments, and the `get_config_suffix()` API. These leftovers are confusing (they suggest VR branching is still needed) and risk reintroducing the split-namespace pattern in new code.

## What Changes

- **BREAKING**: Remove the `get_config_suffix()` function from `classic-registry-core` and its Python/Node binding exports. This function exists solely to build `"GameVR_Info"` key paths and has no remaining legitimate use.
- Remove `GameVR_Info` key-path branching in `classic-cli/src/scanner.cpp` and `classic-gui/src/controllers/scancontroller.cpp` so they use `"Game_Info.Docs_Folder_XSE"` unconditionally.
- Remove `GameVR_Info` key-path branching in `classic-node/cli/run-scan.ts`.
- Remove `GameVR_Info` entries from the `default_localyaml` template in `CLASSIC Main.yaml`.
- Remove `GameVR_Info` sections from all Node binding test fixtures and test YAML.
- Remove `GameVR_Info` references from doc comments in `registry.rs` and `classic_registry.pyi`.
- Remove `GameVR_Info` deprecation comments in `classic-tui/src/app.rs` (the comments themselves reference the dead namespace).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `version-registry-game-metadata`: The spec currently says "`GameVR_Info` SHALL NOT be used for any purpose" and includes scenarios verifying its absence. After this change the spec language should be updated to reflect that the namespace has been fully removed (present tense) rather than "shall not be used" (future prohibition). The `get_config_suffix()` function referenced in the spec as a migration bridge is also removed.

## Impact

- **Rust crates**: `classic-registry-core` (remove `get_config_suffix()`), doc comment updates.
- **C++ frontends**: `classic-cli/src/scanner.cpp`, `classic-gui/src/controllers/scancontroller.cpp` -- remove VR key-path branching.
- **Node bindings**: `classic-node/cli/run-scan.ts` -- remove VR key-path branching; test fixtures and test files updated.
- **Python bindings**: `classic_registry.pyi` -- remove `get_config_suffix()` stub and doc comment.
- **YAML data**: `CLASSIC Main.yaml` `default_localyaml` template loses `GameVR_Info` block.
- **Test fixtures**: Node test YAML and CLI fixtures lose `GameVR_Info` sections.
- **Binding parity**: Python and Node binding exports must be updated in tandem with the Rust API removal.
