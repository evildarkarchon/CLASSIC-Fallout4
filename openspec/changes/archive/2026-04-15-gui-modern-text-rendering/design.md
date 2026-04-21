## Context

The Qt desktop frontend (`classic-gui/`) is the user-facing face of CLASSIC for most end users. Today its typography is configured in exactly one place: a bare `* { font-family: "Segoe UI"; font-size: 13px; color: #e0e0e0; }` rule at `classic-gui/src/styles/dark_theme.qss:9`. Startup in `classic-gui/src/main.cpp` never touches `QApplication::setFont`, never calls `QFontDatabase::addApplicationFont`, and never configures a hinting preference or style strategy for any `QFont`. That leaves three problems:

1. On Windows 10 machines, Segoe UI renders with classic ClearType and looks dated next to modern app chrome. On Windows 11 the system actually has Segoe UI Variable but the GUI does not ask for it.
2. Qt 6 removed the legacy `Qt::AA_*` font-AA flags; subpixel AA and hinting are now per-`QFont` properties through `QFont::StyleStrategy` and `QFont::HintingPreference`. Nobody in `classic-gui` sets those, so rendering quality depends entirely on Qt's platform defaults.
3. The GUI has three copies of `dark_theme.qss` that are kept in sync by the build pipeline (`src/styles/`, `dist/styles/`, `install/styles/`, plus CPack output under `build/packages/_CPack_Packages/**/styles/`). Any font change has to land in whichever copies the pipeline actually rebuilds, or the install and ZIP artifacts drift.

Architecturally, this change is strictly frontend-only. The Rust workspace under `foundation/` and `business-logic/`, the CXX bridge in `cpp-bindings/classic-cpp-bridge/`, and the Python/Node bindings in `python-bindings/` and `node-bindings/classic-node/` are unaffected. The TUI (`ui-applications/classic-tui/`) uses Ratatui and has no concept of a Qt font. The C++ CLI (`classic-cli/`) has no GUI surface. Because this touches only `classic-gui/`, it does not go near any parity gate (`check_parity_gate.py`, `bun run parity:gate`, or the CXX parity gate).

Stakeholders are GUI end users (visual quality), the maintainer (`evildarkarchon`) who owns packaging and release, and any future contributor who extends the stylesheet. There is no legal stakeholder beyond the SIL OFL license-propagation requirement for the bundled font.

## Goals / Non-Goals

**Goals:**
- Ship a consistent, modern-looking UI font (Inter) on every supported Windows version so text no longer looks different between Windows 10 and Windows 11 hosts.
- Turn on subpixel antialiasing and light vertical hinting explicitly and in exactly one place, so future regressions are easy to spot.
- Keep the change isolated to `classic-gui/` so no binding, parity, or cross-language gate is touched.
- Keep rollback trivial: removing the font registration call, the QSS fallback edit, and the resource entries restores prior behavior.
- Satisfy the SIL OFL license-propagation requirement cleanly so distribution of Inter inside the packaged ZIP is legal.

**Non-Goals:**
- Introducing a full theming or per-user font-customization UI. Users do not get to pick fonts in settings; that is a follow-up if requested later.
- Rewriting the GUI's stylesheet pipeline so there is a single canonical `dark_theme.qss`. The current three-copy layout stays; this change adjusts all copies that the existing pipeline keeps in sync.
- Changing monospace rendering in `QTextBrowser`/`QTextEdit` report panes. That can be addressed in a follow-up (JetBrains Mono was rejected as part of the initial question to keep scope small).
- Touching the TUI, CLI, or any binding layer. Any parity or binding-surface change is explicitly out of scope.
- Dynamic runtime switching between "classic" and "modern" rendering. This change sets one default strategy and leaves it there.

## Decisions

### Decision 1: Bundle Inter via Qt resource (`:/fonts/Inter/`) instead of installing it to the OS

**Chosen:** Embed `Inter-Regular.ttf`, `Inter-Italic.ttf`, `Inter-Bold.ttf`, `Inter-BoldItalic.ttf` and `OFL.txt` inside the Qt resource system through `classic-gui/resources/resources.qrc` under a new `fonts/Inter/` prefix, and register each `.ttf` with `QFontDatabase::addApplicationFont(":/fonts/Inter/...")` during startup.

**Rationale:** Qt resource embedding means the font is linked into the binary (or into the `resources.rcc` output that Qt's resource compiler produces); there is no external file dependency at runtime, no OS-level installer step, and no admin-rights requirement. Rendering is deterministic on every host regardless of whether Inter is already present system-wide.

**Alternatives considered:**
- *Ship `.ttf` files alongside the executable and load from disk*: rejected because the existing `classic-gui/install/` and CPack outputs already struggle with synchronizing the three QSS copies; adding more loose assets grows that drift risk. Qt resource embedding removes the path-discovery problem entirely.
- *Require Inter to be installed system-wide*: rejected because end users should not have to install a font to get a decent-looking GUI. Defeats the goal of cross-host consistency.
- *Use `Segoe UI Variable` on Windows 11 and fall back on Win10*: rejected as the primary approach because Win10 would still render as classic Segoe UI — exactly the inconsistency we are trying to eliminate. Segoe UI Variable stays as the *second* entry in the QSS fallback chain, not the primary face.

### Decision 2: Configure per-`QFont` AA strategy via `QApplication::setFont`, not a global Qt attribute

**Chosen:** Build a single `QFont defaultFont("Inter", 10); defaultFont.setStyleStrategy(QFont::PreferAntialias); defaultFont.setHintingPreference(QFont::PreferVerticalHinting); QApplication::setFont(defaultFont);` call in a small GUI-local helper (invoked from `main.cpp` before `MainWindow` is constructed).

**Rationale:** Qt 6 removed the legacy `Qt::AA_*` font-rendering flags; the `StyleStrategy` / `HintingPreference` pair on each `QFont` is now the only supported path. By installing a process-wide default once, every widget that does not override its own font inherits the AA/hinting settings automatically. Centralizing this in a single helper (rather than sprinkling `setFont` calls across dialogs) gives exactly one place to change if we ever revisit the strategy.

**Alternatives considered:**
- *Set font AA through environment variables* (e.g., `QT_FONT_DPI`, `QT_ENABLE_HIGHDPI_SCALING`): rejected because those do not control subpixel AA or hinting directly; they control DPI scaling and are orthogonal.
- *Set per-widget fonts in each dialog/widget*: rejected because it scales badly and the current widget tree has dozens of `QWidget` subclasses under `src/app/`, `src/widgets/`, and `src/controllers/`. Single default is cheaper and more consistent.
- *Expose a `classic-gui/core` helper that the Rust side can influence*: rejected. The one-runtime rule and the binding architecture want Rust to stay UI-agnostic; font policy is a pure frontend concern.

### Decision 3: Point size 10 pt, not pixel size 13 px

**Chosen:** Specify the default `QFont` in points (10 pt) rather than pixels (13 px) and update the QSS to a compatible size scheme.

**Rationale:** Qt treats point sizes as DPI-aware and scales them correctly on fractional-DPI Windows hosts. Pixel sizes are treated as literal device pixels after Qt's high-DPI scaling, which can produce inconsistent visual sizes on 125 % or 150 % scaled displays. Inter was designed for on-screen rendering and looks correct at 10 pt in the Qt default DPI model. The existing 13 px value roughly corresponds to 10 pt at 96 DPI, so perceived text size on a standard 100 %-scaled monitor is unchanged.

**Alternatives considered:**
- *Keep `font-size: 13px` globally*: rejected for the DPI-scaling reason above.
- *Use `em` units in QSS*: rejected because QSS has limited support for `em` and mixing units complicates review.

### Decision 4: QSS fallback chain `"Inter", "Segoe UI Variable", "Segoe UI", sans-serif`

**Chosen:** The `*` selector in `dark_theme.qss` declares that exact fallback order.

**Rationale:** If Inter registration ever fails (corrupted resource, Qt build issue, forked build), Windows 11 hosts land on Segoe UI Variable (still modern) and Windows 10 hosts land on Segoe UI (current behavior). The generic `sans-serif` at the end protects the unlikely non-Windows Qt build. Browsers and Qt resolve font-family lists left-to-right, so the chain is load-bearing in exactly the order listed.

### Decision 5: Apply the font change to every synchronized QSS copy, not just `src/styles/`

**Chosen:** Update `classic-gui/src/styles/dark_theme.qss` plus `classic-gui/dist/styles/dark_theme.qss` and `classic-gui/install/styles/dark_theme.qss`, and rely on `build_gui.ps1` + CPack to regenerate the package copies under `build/packages/_CPack_Packages/...`. Do not attempt to rearchitect the QSS pipeline as part of this change.

**Rationale:** This is a visual polish change, not a refactor of the asset pipeline. Consolidating the three QSS copies is a separate, larger piece of work with its own risk. Updating every copy in-place matches what the existing pipeline does and is easy to verify. The CPack outputs under `build/packages/_CPack_Packages/win64/ZIP/CLASSIC-1.0.0-win64/styles/dark_theme.qss` are regenerated by a full build, so we only have to check them after running the packaging script.

### Decision 6: Font registration is non-fatal

**Chosen:** If `QFontDatabase::addApplicationFont` returns `-1` for every bundled face, log via the existing startup-logging bridge helpers (`classic::message::log_startup_*`) and continue. Do not `QMessageBox::critical` and exit.

**Rationale:** The GUI already has a well-defined pattern for critical startup failures (missing `CLASSIC Data`, missing `CLASSIC Main.yaml`, missing `CLASSIC_Info.version`). Font registration is not in that category — the app remains fully functional with the QSS fallback chain. Failing hard because a bundled `.ttf` did not load would be a worse user experience than rendering in Segoe UI for that session.

### Decision 7: About-dialog license attribution, not a new `licenses/` tree

**Chosen:** Add an Inter/OFL line to the existing About dialog rather than introducing a new top-level `licenses/` surface.

**Rationale:** The SIL OFL requires the license text to be distributed with the font. Shipping `OFL.txt` in the Qt resource (or alongside the executable) satisfies that. The About dialog already lists CLASSIC's name, version, and can carry a one-line font attribution with a link or reference. A new `licenses/` directory would be disproportionate for a single bundled asset.

## Risks / Trade-offs

- **[Bundle size grows ~400–500 KB]** → Mitigation: acceptable for a desktop GUI; no paging concerns on modern disks. If it ever matters, subset Inter to Latin-only via `fonttools` before embedding.
- **[Users with personal ClearType preferences may prefer the old look]** → Mitigation: none needed for v1. Qt's `PreferAntialias` honors Windows ClearType settings for color balance; the default still respects the OS color profile. If users ask for a toggle later, that is a follow-up.
- **[QSS drift across three copies is the current state of the art]** → Mitigation: this change updates all three copies in the same commit and the spec explicitly requires parity across them. Long-term pipeline consolidation is deliberately out of scope.
- **[Inter ships as five face files but we only bundle four]** → Mitigation: we intentionally skip light/extra-bold weights to hold bundle size down. All widgets currently use Regular and Bold; italics are used rarely. If a future widget needs a missing weight, Qt's font substitution will pick the nearest bundled face and the attribution line still covers the OFL obligation.
- **[Font registration failure could silently degrade the GUI]** → Mitigation: emit a structured warning through `classic::message::log_startup_*` with the failed resource paths so support requests are diagnosable.
- **[`QFontDatabase::addApplicationFont` must be called after `QApplication` is constructed but before widgets are shown]** → Mitigation: we call it right after `QApplication app(argc, argv);` and before `MainWindow window;`, mirroring where `app.setWindowIcon` is already called in `main.cpp`.

## Migration Plan

1. Add the Inter `.ttf` files and `OFL.txt` under `classic-gui/resources/fonts/Inter/`.
2. Extend `classic-gui/resources/resources.qrc` with a new `<qresource prefix="/fonts/Inter">` block referencing the four faces and `OFL.txt`.
3. Introduce a small GUI-local helper (for example `classic-gui/src/app/typography.h` + `.cpp`, or a pair of static functions inside `main.cpp` if we want to avoid a new translation unit) that:
   a. Calls `QFontDatabase::addApplicationFont` for each bundled face and logs failures via `classic::message::log_startup_*`.
   b. Builds the default `QFont("Inter", 10)`, sets `PreferAntialias` and `PreferVerticalHinting`, and calls `QApplication::setFont`.
4. Invoke that helper from `classic-gui/src/main.cpp` immediately after `app.setApplicationName(...)` and before the Rust runtime initialization, so logging correlation ids and window icons still work uniformly.
5. Update `classic-gui/src/styles/dark_theme.qss` global `*` rule to the new fallback chain and the new size (switch to point-based sizing if we adopt 10 pt throughout, or keep pixels on per-widget overrides that already rely on pixel sizing).
6. Mirror the QSS update to `classic-gui/dist/styles/dark_theme.qss` and `classic-gui/install/styles/dark_theme.qss`.
7. If CMake install rules already copy `resources.qrc` contents, no CMake change is needed; otherwise extend `classic-gui/CMakeLists.txt` so the font resource is compiled into the binary (Qt's `qt_add_resources` / `AUTORCC` typically handles this automatically).
8. Add an Inter/OFL attribution line to the About dialog.
9. Run `classic-gui/build_gui.ps1 -Test` (full GUI build + tests) and verify the packaged CPack ZIP under `classic-gui/build/packages/_CPack_Packages/...` contains the updated QSS and either embeds the fonts in the resource binary or ships the `.ttf` files alongside.
10. Manually launch the GUI, confirm visually that Inter is active (take a screenshot comparing primary scan buttons and tabs), and confirm `QFontDatabase::families().contains("Inter")` via a small debug print removed before merge.

**Rollback:** revert commits touching `classic-gui/`. There is no data migration and nothing in Rust, bindings, or the bridge changed, so rollback is a clean `git revert`.

## Open Questions

- **Scope of the About-dialog attribution**: should the attribution link to the Inter upstream project (`https://rsms.me/inter/`) or only mention the name and OFL? The spec permits either; pick during implementation.
- **Size-scheme cleanup**: should per-widget font sizes in `dark_theme.qss` (currently 17 px on primary scan buttons, 18 px on About title, 14 px on section headers) be converted to points for DPI robustness, or kept as pixels for minimal diff? Recommendation is to leave them as pixels for now and revisit in a follow-up if fractional-DPI complaints appear.
- **Package-time verification**: do we want `classic-gui/build_gui.ps1` to add a post-build check that asserts `"Inter"` is present in the packaged resource binary? Low priority; defer unless review asks for it.
