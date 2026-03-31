## 1. Remove `get_config_suffix()` API

- [x] 1.1 Delete `get_config_suffix()` function from `ClassicLib-rs/business-logic/classic-registry-core/src/registry.rs` and remove its public export
- [x] 1.2 Remove `get_config_suffix` from the Python binding in `classic-registry-py` (both the Rust PyO3 impl and the `.pyi` stub)
- [x] 1.3 Remove `get_config_suffix` from the Node binding in `classic-node` if exported
- [x] 1.4 Remove any tests for `get_config_suffix()` in registry core tests

## 2. Fix C++ frontend key-path branching

- [x] 2.1 Update `classic-cli/src/scanner.cpp` -- replace VR-branching ternary with hardcoded `"Game_Info.Docs_Folder_XSE"`
- [x] 2.2 Update `classic-gui/src/controllers/scancontroller.cpp` -- remove the loop over `{"Game_Info.Docs_Folder_XSE", "GameVR_Info.Docs_Folder_XSE"}` and read `"Game_Info.Docs_Folder_XSE"` directly

## 3. Fix Node binding key-path branching

- [x] 3.1 Update `ClassicLib-rs/node-bindings/classic-node/cli/run-scan.ts` -- remove VR ternary in `resolveXsePath()`, hardcode `"Game_Info"` as the local key

## 4. Clean up YAML template

- [x] 4.1 Remove the `GameVR_Info` block from the `default_localyaml` value in `CLASSIC Data/databases/CLASSIC Main.yaml`

## 5. Clean up Node binding test fixtures

- [x] 5.1 Remove `GameVR_Info` section from YAML literal in `classic-node/__test__/runtime.node.test.mjs`
- [x] 5.2 Remove `GameVR_Info` section from `CLI_LOCAL_YAML` in `classic-node/__test__/fixtures/cli.fixtures.ts`
- [x] 5.3 Remove `GameVR_Info` section from YAML literal in `classic-node/__test__/config.spec.ts`

## 6. Clean up doc comments and deprecation comments

- [x] 6.1 Update doc comment on any remaining VR-related function in `registry.rs` that references `GameVR_Info` (remove the `GameVR_Info` mention)
- [x] 6.2 Remove `GameVR_Info` deprecation comments from `ClassicLib-rs/ui-applications/classic-tui/src/app.rs` (lines 1491, 1864)

## 7. Verify

- [x] 7.1 Run `rg "GameVR_Info"` across the codebase and confirm zero hits outside `openspec/` archives
- [x] 7.2 Build C++ targets (`classic-cli`, `classic-gui`) and confirm no errors
- [x] 7.3 Run Rust tests (`cargo test` in `ClassicLib-rs/`) and confirm no failures
- [x] 7.4 Run Node binding tests and confirm no failures
