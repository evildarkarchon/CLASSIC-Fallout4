## Context

The Qt desktop frontend owns the Results tab and its `Open Folder` action. That action is emitted from `classic-gui/src/widgets/reportlistwidget.cpp` and resolved in `classic-gui/src/controllers/resultscontroller.cpp`, which already owns report discovery, report selection, deletion, and viewer refresh behavior. The bug report here is not about report discovery itself; it is about what the GUI does once the user has already selected a report and asks to open its location.

The confusing behavior comes from fallback ordering. If the controller treats `Open Folder` as a generic "open the reports area" action instead of a selection-aware action, users can be sent to the primary crash-log directory (`Documents/My Games/.../Crash Logs`) even though the selected report actually lives in a different configured report directory. That makes the button feel broken for custom report directories and makes it harder to manage or share the specific report the user was reviewing.

This is a frontend-only change. No Rust business logic, bridge code, parity surface, or binding contract should move. The scope stays inside `classic-gui/`, primarily `ResultsController` and its tests.

## Goals / Non-Goals

**Goals:**
- Make `Open Folder` selection-aware so the selected Results entry is the first thing the GUI tries to reveal.
- Keep all path resolution and browser-launch behavior centralized in `ResultsController`.
- Define an explicit fallback order so the GUI only opens the primary report directory when there is no usable selected report.
- Cover the behavior with controller-level tests that exercise custom directories, no selection, and missing selected files.

**Non-Goals:**
- Changing how reports are discovered, sorted, or rendered in the Results tab.
- Renaming the button, adding new context-menu actions, or changing tab layout.
- Introducing Rust-side file-browser helpers or any new cross-language API surface.
- Guaranteeing identical "reveal file" UX on every desktop OS; Windows-specific Explorer selection is the priority, with reasonable folder-open fallback elsewhere.

## Decisions

### Decision 1: Keep the `Open Folder` policy in `ResultsController`

**Chosen:** `ReportListWidget` continues to emit the current report path, and `ResultsController::onOpenFolder()` remains the single place that decides whether to reveal a file or open a directory.

**Rationale:** The controller already owns other Results-tab actions and already knows the configured report directories and primary report directory. Keeping the policy there avoids duplicating path logic in the widget and keeps test seams in one place.

**Alternatives considered:**
- *Handle the logic directly in `ReportListWidget`*: rejected because the widget should stay a thin view layer and does not own report-directory fallback state.
- *Move the behavior into Rust*: rejected because opening Explorer or desktop folders is GUI/platform integration, not business logic.

### Decision 2: Selected file reveal comes before directory fallback

**Chosen:** When `Open Folder` is triggered, the controller first checks whether the selected report path is non-empty, exists, and points to a file. If so, it first tries to reveal that file in the platform file browser; if reveal is unsupported or fails, it opens the file's containing directory.

**Rationale:** The user's intent is anchored to the selected report, not to the report root in general. Revealing the exact file is the most precise interpretation of the action and removes ambiguity when multiple report directories are configured.

**Alternatives considered:**
- *Always open the primary report directory*: rejected because it recreates the bug for reports outside the default directory.
- *Always open the containing folder without trying file selection*: rejected because Windows Explorer can highlight the exact file, which is a better user experience when available.

### Decision 3: Use explicit fallback ordering for stale or missing selections

**Chosen:** If there is no usable selected report file, fall back in this order: primary report directory, then the first configured report directory, then no action if no directories are configured.

**Rationale:** This preserves the existing idea that the Results tab still has a useful default location while preventing a stale selection from hijacking the action. Explicit ordering also makes the behavior easy to test.

**Alternatives considered:**
- *Do nothing unless a file is selected*: rejected because `Open Folder` is still useful as a "take me to reports" action when nothing is selected.
- *Guess a directory from the last viewed markdown content*: rejected because it is indirect and harder to reason about than using the controller's existing directory state.

### Decision 4: Test via controller seams instead of launching the real browser

**Chosen:** Keep browser-launch helpers (`revealFileInFileBrowser()` and `openFolderInFileBrowser()`) overridable and verify call counts/paths through a test double in `classic-gui/tests/test_resultscontroller.cpp`.

**Rationale:** Real Explorer launches are slow, flaky, and unsuitable for automated CI. The controller already exposes a clean seam for verifying the exact path and fallback order.

**Alternatives considered:**
- *Manual-only verification*: rejected because the path-selection bug is precise and easy to regress.
- *Mock Qt or `QProcess` globally*: rejected because subclassing the controller is simpler and already matches the current unit-test style.

## Risks / Trade-offs

- **[Stale selected paths can still appear after a file is deleted externally]** -> Mitigation: require the selected path to exist and be a file before attempting reveal; otherwise fall back deterministically.
- **[Explorer-specific file selection is Windows-only]** -> Mitigation: keep the Windows path behind `revealFileInFileBrowser()` and fall back to opening the containing folder on non-Windows platforms.
- **[Spaces or native path formatting can break Explorer invocation]** -> Mitigation: pass the `/select,<path>` argument through `QProcess::startDetached()` with argument separation and use `QDir::toNativeSeparators()`.
- **[Button behavior may still surprise users when nothing is selected]** -> Mitigation: preserve a useful fallback to the primary report directory rather than silently doing nothing.

## Migration Plan

1. Keep `ReportListWidget` emitting the current report path for `openFolderRequested`.
2. Update `ResultsController::onOpenFolder()` so it treats the selected report file as the primary target and only falls back to directories when the selected file is unusable.
3. If needed, keep or introduce helper methods for revealing a file and opening a directory so tests can intercept both paths.
4. Add or update controller tests for:
   a. Selected report in a non-primary/custom report directory.
   b. No selection.
   c. Selected report missing at click time.
5. Run the GUI test target and manually verify that clicking `Open Folder` on Windows highlights the selected report in Explorer.

**Rollback:** revert the `classic-gui` controller/test changes. No data migration or cross-language compatibility work is involved.

## Open Questions

- Should the button label stay `Open Folder`, or should a future follow-up rename it to `Show in Folder` / `Reveal in Folder` to better match the new behavior? Recommendation: keep the current label for this change.
- If a selection exists but the platform cannot reveal files, should the GUI show feedback before opening the containing folder instead? Recommendation: no extra UI for now; quiet fallback is sufficient.
