## ADDED Requirements

### Requirement: Bundled UI Font Registration

The Qt desktop GUI (`classic-gui/`) SHALL register the bundled Inter font family with Qt's font database at application startup, before any widget is constructed, so that the font is available to `QFont` and QSS lookups regardless of whether the host Windows installation has Inter installed system-wide.

The GUI SHALL ship the Inter Regular, Italic, Bold, and Bold-Italic TrueType files as Qt resources under a stable resource prefix (for example `:/fonts/Inter/`), and SHALL ship the upstream SIL Open Font License text (`OFL.txt`) alongside those files to satisfy the font's license-propagation requirement.

If Inter registration fails for every bundled face, the GUI SHALL log a structured warning through the existing startup-logging bridge helpers and SHALL continue with the platform fallback font; the application MUST NOT abort startup because of font registration failure.

#### Scenario: Inter is registered at startup
- **WHEN** `classic-gui` starts on a Windows machine without Inter installed system-wide
- **THEN** `QFontDatabase::families()` contains `"Inter"` before `MainWindow` is shown
- **AND** widgets that resolve `font-family: "Inter"` via QSS or `QFont` render glyphs from the bundled `.ttf` files

#### Scenario: Bundled font files ship with the install
- **WHEN** the GUI package is produced via `classic-gui/build_gui.ps1` and the CPack ZIP step completes
- **THEN** the packaged install tree under `classic-gui/install/` and the CPack ZIP under `classic-gui/build/packages/_CPack_Packages/**/` both contain the Inter `.ttf` files and `OFL.txt` at the same relative path used by the Qt resource prefix, or embed them inside the Qt resource binary
- **AND** the About dialog or a `licenses/` surface in the GUI references Inter and its SIL Open Font License so distributed builds satisfy the license-propagation requirement

#### Scenario: Font registration failure is non-fatal
- **WHEN** every call to `QFontDatabase::addApplicationFont` for the bundled Inter faces returns `-1`
- **THEN** the GUI logs a structured warning identifying `classic-gui.startup` and the failed resource paths
- **AND** the GUI continues startup using the QSS fallback chain described in the font-fallback requirement

### Requirement: Process-Wide Default UI Font and Hinting

After Inter is registered, the Qt desktop GUI SHALL install a process-wide default `QFont` by calling `QApplication::setFont()` before `MainWindow` is constructed. That default font MUST use `"Inter"` as its family, a nominal size of 10 points, `QFont::PreferAntialias` as its style strategy, and `QFont::PreferVerticalHinting` as its hinting preference.

All GUI widgets that do not override their own font SHALL inherit this default so that subpixel antialiasing and light vertical hinting are active uniformly across the GUI.

The default font MUST NOT be set from business-logic crates or from binding code; it SHALL be set only from the GUI frontend (`classic-gui/src/main.cpp` or a GUI-local helper it calls) so that the TUI, CLI, and bindings remain unaffected.

#### Scenario: Default font is applied before widgets exist
- **WHEN** the GUI startup sequence reaches the point just before `MainWindow window; window.show();` in `classic-gui/src/main.cpp`
- **THEN** `QApplication::font().family()` equals `"Inter"`
- **AND** `QApplication::font().styleStrategy()` has the `QFont::PreferAntialias` bit set
- **AND** `QApplication::font().hintingPreference()` equals `QFont::PreferVerticalHinting`

#### Scenario: Widgets without explicit fonts inherit the default
- **WHEN** a `QLabel` is created with no stylesheet font override and no explicit `setFont` call
- **THEN** its effective `font().family()` resolves to `"Inter"` via inheritance from `QApplication::font()`
- **AND** its effective hinting preference is `QFont::PreferVerticalHinting`

#### Scenario: Non-GUI frontends are unaffected
- **WHEN** the TUI (`ui-applications/classic-tui/`), CLI (`classic-cli/`), or any binding consumer (`python-bindings/`, `node-bindings/classic-node/`, `cpp-bindings/classic-cpp-bridge/`) is built and run
- **THEN** no compile-time or runtime dependency on `QFont` or `QApplication::setFont` is introduced
- **AND** none of their public API surfaces or parity baselines change as a result of this capability

### Requirement: QSS Font Family Fallback Chain

The Qt desktop GUI stylesheet at `classic-gui/src/styles/dark_theme.qss` SHALL declare a font-family fallback chain of `"Inter", "Segoe UI Variable", "Segoe UI", sans-serif` for the global `*` selector, so that if Inter registration ever fails the GUI still renders with the most modern Windows-native face available on the host.

Any per-widget font overrides already present in the stylesheet (for example primary scan buttons, section headers, field labels, and the About title) SHALL continue to work after the change and MUST NOT pin a non-Inter family unless the widget intentionally uses a different face.

#### Scenario: Fallback chain renders on a host without Inter
- **WHEN** the GUI runs on a machine where Inter registration failed and Segoe UI Variable is installed
- **THEN** the effective rendered family for widgets styled by the `*` selector is `"Segoe UI Variable"`

#### Scenario: Per-widget font size overrides are preserved
- **WHEN** the stylesheet is updated to use the new family chain
- **THEN** primary scan buttons (`QPushButton#btnScanCrashLogs`, `QPushButton#btnScanGameFiles`), the About title (`QLabel#aboutTitle`), section headers (`QLabel[class="sectionHeader"]`), and field labels (`QLabel[class="fieldLabel"]`) keep their existing `font-size` and `font-weight` values
- **AND** their resolved family is Inter when Inter is registered successfully

### Requirement: Dev, Install, and Package Stylesheet Parity

Because `classic-gui/` keeps three synchronized copies of `dark_theme.qss` (source at `classic-gui/src/styles/dark_theme.qss`, dev-tree copy at `classic-gui/dist/styles/dark_theme.qss`, and install copy at `classic-gui/install/styles/dark_theme.qss`), any change to the font-family chain or new typography rules SHALL be applied to every copy that the existing build pipeline keeps in sync, or the pipeline SHALL be updated so a single source file is the source of truth and the other copies are produced from it.

The CPack package output under `classic-gui/build/packages/_CPack_Packages/**/styles/dark_theme.qss` SHALL contain the updated font-family chain for any packaged build produced after this change lands.

#### Scenario: All QSS copies carry the new fallback chain
- **WHEN** `classic-gui/build_gui.ps1` is run to produce a packaged build after this change
- **THEN** the source QSS, the dev-tree QSS, the install QSS, and the CPack QSS all contain the `"Inter", "Segoe UI Variable", "Segoe UI", sans-serif` fallback chain on the `*` selector
- **AND** no QSS copy still declares `font-family: "Segoe UI";` as the sole family on the `*` selector
