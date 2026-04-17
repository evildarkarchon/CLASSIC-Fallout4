## 1. Asset acquisition and licensing

- [x] 1.1 Download Inter v4.x Regular, Italic, Bold, and Bold-Italic TrueType face files from the upstream release (`https://github.com/rsms/inter/releases`).
- [x] 1.2 Verify upstream release hash/signature before checking any font binary into the repo.
- [x] 1.3 Place the four `.ttf` files and the upstream `OFL.txt` under a new directory `classic-gui/resources/fonts/Inter/`.
- [x] 1.4 Confirm the license text matches the SIL Open Font License version referenced in Inter's upstream repo, and record the exact Inter version in a short `classic-gui/resources/fonts/Inter/README.md` so future updates are reproducible.

## 2. Qt resource wiring

- [x] 2.1 Extend `classic-gui/resources/resources.qrc` with a new `<qresource prefix="/fonts/Inter">` block that lists `Inter-Regular.ttf`, `Inter-Italic.ttf`, `Inter-Bold.ttf`, `Inter-BoldItalic.ttf`, and `OFL.txt`.
- [x] 2.2 If `classic-gui/CMakeLists.txt` does not already pick up `resources.qrc` via `AUTORCC` or `qt_add_resources`, add an explicit entry so the font resource binary links into the `classic-gui` executable.
- [x] 2.3 Run a throwaway Qt build locally and confirm that `QFile(":/fonts/Inter/Inter-Regular.ttf").exists()` returns `true` (small debug line, removed before merge).

## 3. Startup font registration and default QFont

- [x] 3.1 Add a GUI-local helper (either a new pair `classic-gui/src/app/typography.h` + `.cpp`, or two static free functions inside `classic-gui/src/main.cpp`) that exposes `registerBundledFonts()` and `installDefaultFont()`.
- [x] 3.2 Implement `registerBundledFonts()` so it calls `QFontDatabase::addApplicationFont` for each bundled face and, on any `-1` return value, emits a structured warning via `classic::message::log_startup_*` identifying `classic-gui.startup` and the failed resource path.
- [x] 3.3 Implement `installDefaultFont()` so it constructs `QFont("Inter", 10)`, calls `setStyleStrategy(QFont::PreferAntialias)` and `setHintingPreference(QFont::PreferVerticalHinting)`, and invokes `QApplication::setFont(...)`.
- [x] 3.4 Invoke both helpers from `classic-gui/src/main.cpp` immediately after `app.setApplicationName(...)` and before the Rust runtime is initialized, mirroring the existing placement of `app.setWindowIcon(...)`.
- [x] 3.5 Verify via a throwaway debug print (removed before merge) that at the point just before `MainWindow window;` the values `QApplication::font().family()`, `QApplication::font().styleStrategy()`, and `QApplication::font().hintingPreference()` match the spec requirements.

## 4. Stylesheet updates (all three synchronized copies)

- [x] 4.1 Update `classic-gui/src/styles/dark_theme.qss` so the global `*` selector uses `font-family: "Inter", "Segoe UI Variable", "Segoe UI", sans-serif;` and keeps the existing `color: #e0e0e0;` value.
- [x] 4.2 Decide (per Open Question in `design.md`) whether to leave the global `font-size` as `13px` for minimum diff or migrate to `10pt`; keep the choice consistent across all three QSS copies.
- [x] 4.3 Apply the identical `*`-selector change to `classic-gui/dist/styles/dark_theme.qss`.
- [x] 4.4 Apply the identical `*`-selector change to `classic-gui/install/styles/dark_theme.qss`.
- [x] 4.5 Confirm that per-widget font sizes (primary scan buttons, About title, section headers, field labels) still resolve correctly by opening the GUI and eyeballing the Main, Backup, Articles, and About tabs.

## 5. About-dialog license attribution

- [x] 5.1 Locate the About dialog implementation under `classic-gui/src/app/` (search for `aboutTitle` / `QLabel#aboutTitle`).
- [x] 5.2 Add a short attribution line that names Inter and references the SIL Open Font License, linking to either the bundled `:/fonts/Inter/OFL.txt` resource or a short text paragraph.
- [x] 5.3 Verify the About dialog still renders at its current size and does not clip the new attribution line.

## 6. Build, package, and verify

- [x] 6.1 Run `classic-gui/build_gui.ps1 -Test` and confirm the build succeeds and all existing Qt tests pass.
- [x] 6.2 Open the built GUI, visually confirm that primary scan buttons, tab labels, report views, and dialogs all render with Inter.
- [x] 6.3 Check the CPack ZIP output at `classic-gui/build/packages/_CPack_Packages/win64/ZIP/CLASSIC-1.0.0-win64/styles/dark_theme.qss` and confirm the new fallback chain is present.
- [x] 6.4 Confirm the packaged binary either embeds the Inter faces in its resource binary or ships them as files, matching the spec's requirement that distributed builds carry the font and OFL text.
- [x] 6.5 On a Windows 10 VM or machine (if available), run the packaged build and visually confirm Inter is active; if no Win10 host is available, document this in the PR description so a reviewer can verify.

## 7. Failure-mode verification

- [x] 7.1 Temporarily rename the Inter entries out of `resources.qrc` in a local branch, rebuild, and confirm that the GUI still starts, logs a structured warning via the startup bridge, and visually falls back to Segoe UI Variable (on Win11) or Segoe UI (on Win10).
- [x] 7.2 Revert the temporary failure-mode change before merge.

## 8. Documentation and PR hygiene

- [x] 8.1 Update `classic-gui/` README or similar GUI-side docs, if any, with a short note on the bundled font and its license; skip if no such README exists.
- [x] 8.2 Remove all throwaway debug prints added during tasks 2.3 and 3.5 before opening the PR.
- [x] 8.3 In the PR description, include a before/after screenshot pair of the Main tab and the About dialog so the visual change is reviewable. (Skipped: solo project, no external reviewer, visual change verified interactively during implementation.)
- [x] 8.4 Confirm that no file under `foundation/`, `business-logic/`, `cpp-bindings/`, `python-bindings/`, `node-bindings/`, or `ui-applications/` is touched by the diff, and note this explicitly in the PR description.
- [x] 8.5 Run `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`, `python tools/python_api_parity/check_parity_gate.py --repo-root .`, and `cd node-bindings/classic-node && bun run parity:gate` as a sanity check; all three gates MUST pass without baseline drift because no binding surface changed.
