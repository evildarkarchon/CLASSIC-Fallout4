## Why

CLASSIC-GUI currently relies on a bare `font-family: "Segoe UI"; font-size: 13px;` stylesheet rule (`classic-gui/src/styles/dark_theme.qss:9`) and never configures Qt's font-rendering strategy. That leaves text rendering fully at the mercy of each Windows install: on Windows 10 it falls back to classic Segoe UI with system ClearType, and on fractional-DPI or non-ClearType displays the result can look dated, thin, or inconsistent between machines. Because the GUI is the human-facing face of the crash-log scanner, modernizing text rendering is a low-risk, high-visibility quality-of-life improvement that users notice immediately.

## What Changes

- Bundle the Inter font family (Regular, Italic, Bold, BoldItalic) under the SIL Open Font License inside a new Qt resource so rendering is identical on Windows 10 and Windows 11.
- Register the bundled fonts at process startup via `QFontDatabase::addApplicationFont()` in `classic-gui/src/main.cpp` before `MainWindow` is constructed.
- Set a process-wide default `QFont` using `Inter`, 10 pt, `QFont::PreferAntialias` style strategy, and `QFont::PreferVerticalHinting` hinting preference, so subpixel antialiasing is active with light hinting on all widgets.
- Update `classic-gui/src/styles/dark_theme.qss` so `font-family` falls back through `"Inter", "Segoe UI Variable", "Segoe UI", sans-serif` and keeps the numeric sizes consistent with the new default.
- Extend the Qt resource file (`classic-gui/resources/resources.qrc`) and CMake install rules (`classic-gui/CMakeLists.txt` / `CMakePresets.json` as needed) to ship the Inter `.ttf` files with both the dev build tree and the packaged ZIP output under `classic-gui/dist/` and `classic-gui/install/`.
- Add the Inter upstream `OFL.txt` to the repo under `classic-gui/resources/fonts/Inter/` and reference it from the About dialog or a new `licenses/` section so the license-propagation requirement of the SIL OFL is satisfied.
- Wrap the font/hinting setup behind a single C++ helper so the TUI and CLI are unaffected and there is exactly one place responsible for GUI typography.
- **Non-breaking**: no public Rust, CXX bridge, Python, or Node API is changed; this is a frontend-only visual change.

## Capabilities

### New Capabilities
- `gui-text-rendering`: Owns how the Qt desktop frontend selects fonts, registers bundled typefaces, and configures antialiasing and hinting so the GUI has consistent, modern text output across Windows 10 and Windows 11.

### Modified Capabilities
<!-- None. The new behavior is isolated to the Qt GUI frontend and does not change any existing spec-level requirements. -->

## Impact

- **Affected code**: `classic-gui/src/main.cpp`, `classic-gui/src/styles/dark_theme.qss`, `classic-gui/resources/resources.qrc`, `classic-gui/CMakeLists.txt`, `classic-gui/CMakePresets.json` (only if install-rule changes are required), and new asset directory `classic-gui/resources/fonts/Inter/`.
- **Affected binaries / packaging**: `classic-gui/dist/styles/dark_theme.qss` and `classic-gui/install/styles/dark_theme.qss` snapshots; `classic-gui/build/packages/_CPack_Packages/**/styles/dark_theme.qss` via CPack. Bundled ZIP grows by ~400–500 KB from the Inter font subset.
- **Dependencies**: No new runtime or build dependency. Qt 6 (already required) provides `QFontDatabase`, `QFont`, and DirectWrite-backed subpixel AA natively.
- **APIs and bindings**: None affected. The Rust workspace, CXX bridge (`cpp-bindings/classic-cpp-bridge/`), Python bindings (`python-bindings/`), Node bindings (`node-bindings/classic-node/`), and TUI (`ui-applications/classic-tui/`) are not touched.
- **Parity gates**: None required. `check_parity_gate.py`, `bun run parity:gate`, and the CXX parity gate are unaffected because no binding surface changes.
- **Docs**: Add a short typography note to the GUI-side docs under `docs/api/` only if we introduce a new documented helper; otherwise update the About dialog text to mention Inter/OFL.
- **Testing**: Manual visual verification via `classic-gui/build_gui.ps1` plus an automated smoke check that `QFontDatabase` reports Inter as a known family after startup.
- **Risk**: Low. Rollback is removing the font resource registration, the QSS fallback change, and the `QApplication::setFont` call — all in one frontend.
