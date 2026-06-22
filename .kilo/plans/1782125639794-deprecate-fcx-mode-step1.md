# Deprecate FCX Mode — Step 1: Remove "disabled" report notice + mark deprecated in UIs/data

## Goal
First step of deprecating the FCX Mode feature:
1. Stop emitting the "FCX MODE IS DISABLED…" notice in scan reports.
2. Mark the feature as **deprecated** in the live UIs (GUI toggle, CLI flag) and in the user-facing data/help layer.

The feature stays **functionally unchanged** — we only remove the disabled-state report nag and add deprecation labeling. No behavior change when FCX is enabled.

## Scope decisions (resolved)
- **Report:** Remove only the disabled-state notice. Keep the enabled-state notice (lines 219–220) and all FCX check results/issues.
- **UI marking style:** Label suffix `(Deprecated)` + GUI tooltip; CLI help-text suffix. Controls remain functional.
- **Data/help:** Update both `GUI_Help.yaml` (`fcx_mode` topic) and the `FCX Mode` comment in `CLASSIC Main.yaml`.
- **TUI:** No FCX surface exists in `ui-applications/classic-tui/` — nothing to change.

## Out of scope (later deprecation steps)
- Removing the feature/config field, the enabled-state notice, the `--fcx-mode` flag, or the GUI toggle entirely.
- Changing the `FCX Mode: false` default value.
- Touching the Python "skipping game files check" default messages in `python-bindings/classic-scanlog-py/src/fcx_handler.rs` (separate strings, not the report notice).

---

## Tasks (ordered)

### 1. Rust core — remove disabled-state report notice
File: `business-logic/classic-scanlog-core/src/fcx_handler.rs`, fn `get_fcx_messages()` (currently lines 215–249).
- In the `else` (disabled) branch, remove the two `lines.push(...)` statements:
  - `"* NOTICE: FCX MODE IS DISABLED. YOU CAN ENABLE IT TO DETECT PROBLEMS IN YOUR MOD & GAME FILES * \n\n"` (line 244)
  - `"[ FCX Mode can be enabled in the exe or CLASSIC Settings.yaml located in your CLASSIC folder. ] \n\n"` (line 245)
- Result: when `fcx_mode == false`, `get_fcx_messages()` returns an empty `ReportFragment` (the FCX section disappears from reports for the default/disabled case).
- Keep the enabled branch (219–220 + results + detected-issues section) intact.
- Either leave an empty `else {}` or drop the `else` so the function only pushes lines when enabled — implementer's choice, keep it clean.

### 2. Rust core — update the sibling test
File: `business-logic/classic-scanlog-core/src/fcx_handler_tests.rs`, `test_fcx_disabled_messages` (lines 42–50).
- Current assertions expect a **non-empty** fragment containing `"DISABLED"`. These will now fail.
- Update to assert the disabled fragment is **empty** (e.g., `assert!(fragment.is_empty())` and/or `assert!(fragment.to_list().is_empty())`); remove the `"DISABLED"` content assertion.
- Leave `test_fcx_enabled_messages` (52–60) and `test_fcx_with_results` (62+) unchanged.
- Keep the sibling-test layout (`#[cfg(test)] #[path = "fcx_handler_tests.rs"] mod tests;`) — do not introduce inline test modules.

### 3. GUI — mark toggle deprecated
File: `classic-gui/src/app/settingsdialog.cpp`, `setupScanningTab()` (line 165).
- Change label: `m_chkFcxMode = new ToggleSwitch(QStringLiteral("FCX Mode (Deprecated)"));`
- Add a tooltip right after creation, e.g.:
  `m_chkFcxMode->setToolTip(QStringLiteral("FCX Mode is deprecated and will be removed in a future release."));`
- Do not change load/save/reset wiring (`settingsdialog.cpp:388`, `:453`, `:535`) or the config key `CLASSIC_Settings.FCX Mode`. Toggle stays functional.

### 4. CLI — mark flag deprecated
File: `classic-cli/src/cli_args.cpp` (line 32).
- Change help text only:
  `app.add_flag("--fcx-mode", args.fcx_mode, "Enable FCX enhanced analysis (deprecated)");`
- Keep the flag name `--fcx-mode` and `args.fcx_mode` unchanged (CLI tests parse the flag name, not help text).

### 5. Data/help — Help topic
File: `CLASSIC Data/Help/GUI_Help.yaml`, `fcx_mode` topic (467–519).
- Add a deprecation note: update `title` to indicate deprecation (e.g., `"FCX Mode (Deprecated)"`) and/or add a leading line in `content` such as: `> **Deprecated:** FCX Mode is being phased out and will be removed in a future release.`
- Preserve YAML structure (`title`, `content`, `related`). This file has **no** `schema_version` and is not under `databases/`.

### 6. Data/help — Settings comment
File: `CLASSIC Data/databases/CLASSIC Main.yaml` (line 30, inside the `default_settings: |` block).
- Update the comment above `FCX Mode: false` to note deprecation, e.g.:
  `# FCX - File Check Xtended (DEPRECATED, will be removed) | Set to true if you want CLASSIC to check the integrity of your game files and core mods.`
- **Do not** change `FCX Mode: false`.
- **Do not** bump root `schema_version: "2.0"` — this is a comment-only change (no key/value-shape change). Bumping would force a matching `client_schemas.rs` constant bump and is unnecessary.

---

## Validation

Rust (pure core crate — `PYO3_PYTHON` not required when scoped to this crate):
- `cargo fmt`
- `cargo clippy -p classic-scanlog-core`
- `cargo test -p classic-scanlog-core` (confirms updated `test_fcx_disabled_messages` + unchanged enabled/results tests pass)

GUI (repo wrapper only — never invoke ctest/binaries directly):
- `classic-gui/build_gui.ps1 -Test` (optionally `-CTestName test_scan_settings_wiring`)

CLI (repo wrapper only):
- `classic-cli/build_cli.ps1 -Test` (confirms `test_cli_args` still passes with unchanged flag name)

Schema drift guard (needs the drift-guards venv group for `ruamel.yaml`):
- `python tools/schema_version_gate.py` — should pass; the guard checks only root `schema_version` vs client constants, not file content.

---

## Risk / impact notes
- **Behavior change:** With FCX disabled (the default), the FCX section is now omitted from reports entirely. Confirmed acceptable; no test or golden fixture depends on the disabled notice text.
- **No parity refresh needed:** `get_fcx_messages()` / `get_fcx_status_message()` signatures are unchanged, so CXX, Node, and Python parity gates and baselines are unaffected. The Python smoke test `test_fcx_mode_handler_get_fcx_messages_empty` asserts only `isinstance(msgs, list)` and still passes with an empty list.
- **No golden-report dependency:** The ~250 `Crash Logs/*-AUTOSCAN.md` files are generated outputs, not test fixtures. Tests referencing `AUTOSCAN` check filename patterns/headers only.
- **Strings not changed (intentional):** `get_fcx_status_message()` ("FCX Mode: DISABLED"), the Python "skipping game files check" defaults, and the GUI "FCX Mode Requires Paths" path-gating dialog are out of scope for this step.
- **YAML publish:** The `CLASSIC Main.yaml` comment edit is a `databases/` content change that will ride along in the next `yaml-data-v*` publish; no schema bump means no client-compat action required.

## Repo guardrails honored
- Business logic stays in Rust core; C++ GUI/CLI changes are interface-only (label/help/tooltip).
- Rust unit tests remain in the sibling `*_tests.rs` file.
- C++ tests run only via the repo PowerShell wrappers.
- No public Rust/bridge/binding API contract changes → no `docs/api/` updates required.

## Implementation note
This plan requires source edits and running build/test commands. Switch to an implementation-capable agent to execute it.
