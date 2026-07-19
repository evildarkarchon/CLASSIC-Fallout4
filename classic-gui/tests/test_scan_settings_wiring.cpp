#include <QFile>
#include <QRegularExpression>
#include <QtTest/QtTest>

class ScanSettingsWiringTests : public QObject {
    Q_OBJECT

private slots:
    void mainwindow_sources_initial_policy_from_rust_defaults();
    void typed_scan_settings_reach_controller();
    void scan_pipeline_forwards_existing_xse_log_hint();
    void mainwindow_forwards_game_version_to_game_files_controller();
    void game_files_controller_forwards_game_version_to_worker();
    void game_files_worker_forwards_game_version_to_setup_intake();
    void game_files_worker_marks_required_actions_as_attention();
    void game_files_worker_catches_non_standard_exceptions();
    void mainwindow_wires_live_crash_scan_progress_updates();
    void mainwindow_does_not_use_deprecated_vr_mode_setting();
    /// Verifies that explicit remembered-path saves can create a previously declined settings document.
    void mainwindow_bootstraps_missing_settings_when_saving_remembered_paths();
    /// Verifies that detected and manual paths reach one final consent-gated commit.
    void mainwindow_defers_setup_commit_until_manual_completion();
    void mainwindow_preserves_legacy_settings_on_failed_migration();
    void update_worker_declares_not_published_classification();
    void mainwindow_handles_not_published_without_error_dialog();
    void mainwindow_shows_error_details_for_explicit_update_failures();
    void settings_dialog_handles_not_published_as_benign();
    void mainwindow_blocks_game_files_scan_when_paths_unresolved();
    void mainwindow_blocks_crash_logs_scan_when_fcx_enabled_and_paths_unresolved();
    void mainwindow_uses_exe_relative_crash_logs_dir();
    void mainwindow_resets_stale_game_exe_path_outside_selected_root();
    void controllers_emit_global_scan_started_signal_on_scan_start();
    void scan_controller_delegates_xse_folder_resolution_to_core();
    void mainwindow_enables_drag_and_drop();
    void mainwindow_forwards_drops_through_targeted_child_event_filter();
    void mainwindow_forwards_drag_moves_through_targeted_child_event_filter();
    void mainwindow_acknowledges_duplicate_non_local_and_unsupported_drops();
    void mainwindow_reports_wrong_tab_drops();
    void mainwindow_passes_targeted_inputs_to_scan_controller();
    void mainwindow_has_clear_targeted_inputs_slot();
    void mainwindow_sizes_clear_targeted_button_to_fit_text();
    void mainwindow_refreshes_layout_when_targeted_list_visibility_changes();
    void mainwindow_wires_scan_warnings_to_user_feedback();
    void mainwindow_includes_last_scan_report_dirs_in_results_setup();
    void mainwindow_seeds_targeted_report_dirs_before_scan_finishes();
    void mainwindow_deduplicates_report_dirs_before_results_setup();
    /// Pins the worker continuation, GUI-thread prompt, and explicit three-choice recovery wiring.
    void local_ignore_recovery_is_prompted_and_resumed_across_gui_layers();
    void installed_yaml_data_propagates_from_worker_to_user_visible_terminal_status();
};

void ScanSettingsWiringTests::mainwindow_sources_initial_policy_from_rust_defaults()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    const QRegularExpression loadRegex(QStringLiteral(
        R"(void MainWindow::loadSettings\(\)\s*\{\s*m_guiSettings = classic::gui::GuiUserSettings::publishedDefaults\(\);\s*m_updateCheckOnStartup = m_guiSettings\.update\.updateCheck;\s*m_autoSwitchToResultsAfterScan = m_guiSettings\.frontend\.autoSwitchAfterScan;)"));
    QVERIFY2(loadRegex.match(sourceText).hasMatch(),
             "MainWindow should derive no-root policy from the Rust-owned published-default snapshot");
}

void ScanSettingsWiringTests::typed_scan_settings_reach_controller()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    const QRegularExpression callRegex(QStringLiteral(
        R"(m_scanController->startScan\(m_dataRoot,\s*launchSettings,\s*setupXseLogPath,\s*m_targetedInputPaths\))"));
    QVERIFY2(callRegex.match(sourceText).hasMatch(),
             "MainWindow should pass the accepted typed scan settings to ScanController");
}

void ScanSettingsWiringTests::scan_pipeline_forwards_existing_xse_log_hint()
{
    const QString mainWindowPath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile mainWindowFile(mainWindowPath);
    QVERIFY2(mainWindowFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(mainWindowPath)));
    const QString mainWindowSource = QString::fromUtf8(mainWindowFile.readAll());

    QVERIFY2(mainWindowSource.contains(QStringLiteral("classic::xse::resolve_xse_folder_for_scan")),
             "MainWindow should use the shared XSE folder resolver for the setup hint");
    QVERIFY2(mainWindowSource.contains(QStringLiteral("QFileInfo(logPath).isFile()")),
             "MainWindow should forward only an XSE log that actually exists");
    QVERIFY2(mainWindowSource.contains(QStringLiteral("f4se.log")) &&
                 mainWindowSource.contains(QStringLiteral("f4sevr.log")),
             "MainWindow should support Fallout 4 and Fallout 4 VR XSE log conventions");

    const qsizetype callStart = mainWindowSource.indexOf(QStringLiteral("m_scanController->startScan("));
    QVERIFY2(callStart >= 0, "MainWindow should call ScanController::startScan()");
    const qsizetype callEnd = mainWindowSource.indexOf(QStringLiteral(");"), callStart);
    QVERIFY2(callEnd > callStart, "MainWindow should have a complete ScanController::startScan() call");
    const QString call = mainWindowSource.mid(callStart, callEnd - callStart);
    QVERIFY2(call.contains(QStringLiteral("setupXseLogPath")),
             "MainWindow should pass the resolved XSE log hint to ScanController");
}

void ScanSettingsWiringTests::mainwindow_forwards_game_version_to_game_files_controller()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());

    const QRegularExpression callRegex(
        QStringLiteral(R"(m_gameFilesController->startScan\(\s*m_dataRoot,\s*xseLogPath\s*\))"));
    QVERIFY2(callRegex.match(sourceText).hasMatch(),
             "MainWindow should let Rust reopen the cohesive typed Game Setup group for game-file intake");
}

void ScanSettingsWiringTests::game_files_controller_forwards_game_version_to_worker()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/controllers/gamefilescontroller.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());

    QVERIFY2(sourceText.contains(QStringLiteral("const QString& classicRoot")),
             "GameFilesController::startScan() should receive the CLASSIC root for typed settings open");
    const QRegularExpression workerCallRegex(QStringLiteral(R"(worker->doScan\(classicRoot,\s*xseLogPath\))"));
    QVERIFY2(workerCallRegex.match(sourceText).hasMatch(),
             "GameFilesController should pass the typed-open root and detection hint to its worker");
}

void ScanSettingsWiringTests::game_files_worker_forwards_game_version_to_setup_intake()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/workers/gamefilesworker.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());

    QVERIFY2(sourceText.contains(QStringLiteral("run_game_setup_intake_from_user_settings")),
             "GameFilesWorker should invoke the cohesive typed User Settings intake adapter");
    QVERIFY2(sourceText.contains(QStringLiteral("classic::toRustString(classicRoot)")),
             "GameFilesWorker should let Rust open User Settings at the selected CLASSIC root");
    QVERIFY2(!sourceText.contains(QStringLiteral("run_game_setup_intake(")),
             "GameFilesWorker should not rebuild Game Setup facts from positional GUI strings");
}

void ScanSettingsWiringTests::game_files_worker_marks_required_actions_as_attention()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/workers/gamefilesworker.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());

    QVERIFY2(sourceText.contains(QStringLiteral("result.has_errors")),
             "GameFilesWorker should preserve failed-check status from setup intake");
    QVERIFY2(sourceText.contains(QStringLiteral("result.status")),
             "GameFilesWorker should inspect setup intake status before reporting success");
    QVERIFY2(sourceText.contains(QStringLiteral("result.action_count > 0")),
             "GameFilesWorker should treat required setup actions as needing user attention");
    QVERIFY2(sourceText.contains(QStringLiteral("requiresAttention")),
             "GameFilesWorker should forward the combined attention state to the GUI");
}

void ScanSettingsWiringTests::game_files_worker_catches_non_standard_exceptions()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/workers/gamefilesworker.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("catch (...)")),
             "GameFilesWorker should surface non-standard worker exceptions");
    QVERIFY2(sourceText.contains(QStringLiteral("emit error(QStringLiteral(\"unknown error\"))")),
             "GameFilesWorker should report a stable fallback error message");
}

void ScanSettingsWiringTests::mainwindow_wires_live_crash_scan_progress_updates()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    const QRegularExpression slotRegex(QStringLiteral(
        R"(onCrashScanProgress\s*\(\s*float\s+percent,\s*const\s+QString&\s+status,\s*int\s+completed,\s*int\s+total\s*\))"));
    QVERIFY2(sourceText.contains(QStringLiteral("&ScanController::scanProgress")),
             "MainWindow should connect crash-scan progress updates from ScanController");
    QVERIFY2(sourceText.contains(QStringLiteral("&MainWindow::onCrashScanProgress")),
             "MainWindow should route crash-scan progress through a dedicated live progress slot");
    QVERIFY2(slotRegex.match(sourceText).hasMatch(),
             "MainWindow should receive structured completed and total counts in the live crash-scan progress slot");
}

void ScanSettingsWiringTests::mainwindow_does_not_use_deprecated_vr_mode_setting()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(!sourceText.contains(QStringLiteral("CLASSIC_Settings.VR Mode")),
             "MainWindow should not read deprecated CLASSIC_Settings.VR Mode");
}

void ScanSettingsWiringTests::mainwindow_bootstraps_missing_settings_when_saving_remembered_paths()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString source = QString::fromUtf8(file.readAll());
    const qsizetype start = source.indexOf(QStringLiteral("void MainWindow::saveRememberedPath"));
    const qsizetype end = source.indexOf(QStringLiteral("\nvoid MainWindow::initResultsReportDir"), start);
    QVERIFY2(start >= 0 && end > start, "saveRememberedPath should be readable as one function body");
    const QString body = source.mid(start, end - start);

    QVERIFY2(body.contains(QStringLiteral("m_guiSettings.revision == QStringLiteral(\"missing\")")) &&
                 body.contains(QStringLiteral("bootstrapWithSelectedPaths")) &&
                 body.contains(QStringLiteral("commitSelectedPaths")),
             "Remembered-path saves should bootstrap missing settings and update existing settings");
}

void ScanSettingsWiringTests::mainwindow_defers_setup_commit_until_manual_completion()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString source = QString::fromUtf8(file.readAll());
    const qsizetype start = source.indexOf(QStringLiteral("void MainWindow::checkFirstRunPaths()"));
    const qsizetype end = source.indexOf(QStringLiteral("\nQString MainWindow::findDataRoot()"), start);
    QVERIFY2(start >= 0 && end > start, "checkFirstRunPaths should be readable as one function body");
    const QString body = source.mid(start, end - start);

    QCOMPARE(body.count(QStringLiteral("commitChanges(changes)")), 1);
    const qsizetype manualDialog = body.indexOf(QStringLiteral("ManualPathDialog dialog"));
    const qsizetype finalCommit = body.indexOf(QStringLiteral("commitChanges(changes)"));
    QVERIFY2(manualDialog >= 0 && finalCommit > manualDialog,
             "Accepted detected paths must wait for manual completion before the single commit");
    QVERIFY2(body.contains(QStringLiteral("bootstrapWithSelectedPaths")) &&
                 body.contains(QStringLiteral("commitSelectedPaths")),
             "Missing and existing documents should use distinct explicitly named commit operations");
}

void ScanSettingsWiringTests::mainwindow_preserves_legacy_settings_on_failed_migration()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("user_settings_plan_migration")) &&
                 sourceText.contains(QStringLiteral("QMessageBox::question")),
             "MainWindow should present a pure migration plan before any migration write");
    QVERIFY2(sourceText.contains(QStringLiteral("user_settings_apply_migration")) &&
                 sourceText.contains(QStringLiteral("receipt.backup_revision")),
             "MainWindow should apply migration through the verified backup receipt contract");
    QVERIFY2(sourceText.contains(QStringLiteral("user_settings_restore_migration")),
             "MainWindow should offer explicit restoration through the retained migration receipt");
    QVERIFY2(!sourceText.contains(QStringLiteral("QFile::rename")) && !sourceText.contains(QStringLiteral("QSaveFile")),
             "MainWindow should not implement migration publication itself");
}

void ScanSettingsWiringTests::update_worker_declares_not_published_classification()
{
    const QString headerPath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/workers/updateworker.h");
    QFile file(headerPath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(headerPath)));

    const QString headerText = QString::fromUtf8(file.readAll());
    QVERIFY2(headerText.contains(QStringLiteral("kClassificationNotPublished")),
             "UpdateWorker should declare the not_published classification constant");
    QVERIFY2(headerText.contains(QStringLiteral("\"not_published\"")),
             "UpdateWorker constant should match the CXX bridge classification label");
}

void ScanSettingsWiringTests::mainwindow_handles_not_published_without_error_dialog()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    const qsizetype branchStart = sourceText.indexOf(QStringLiteral("kClassificationNotPublished"));
    QVERIFY2(branchStart >= 0, "MainWindow should branch on the not_published classification");

    const qsizetype nextBranch = sourceText.indexOf(QStringLiteral("} else if (explicitCheck)"), branchStart);
    QVERIFY2(nextBranch > branchStart, "not_published should be handled before the generic explicit-check branch");

    const QString branch = sourceText.mid(branchStart, nextBranch - branchStart);
    QVERIFY2(branch.contains(QStringLiteral("if (explicitCheck)")),
             "not_published should stay silent for startup/background checks");
    QVERIFY2(branch.contains(QStringLiteral("QMessageBox::information")),
             "explicit not_published checks should show an informational dialog");
    QVERIFY2(!branch.contains(QStringLiteral("QMessageBox::warning")),
             "not_published must not reach the warning/error dialog path");
}

void ScanSettingsWiringTests::mainwindow_shows_error_details_for_explicit_update_failures()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    const qsizetype branchStart = sourceText.indexOf(QStringLiteral("kClassificationError"));
    QVERIFY2(branchStart >= 0, "MainWindow should branch on the error classification");

    const qsizetype nextBranch = sourceText.indexOf(QStringLiteral("} else if"), branchStart);
    QVERIFY2(nextBranch > branchStart, "error classification should be handled in its own branch");

    const QString branch = sourceText.mid(branchStart, nextBranch - branchStart);
    QVERIFY2(branch.contains(QStringLiteral("logUpdateCheckFailure(errorMessage)")),
             "update-check failures should still be logged");
    QVERIFY2(branch.contains(QStringLiteral("if (explicitCheck)")),
             "manual update-check failures should be separated from background checks");
    QVERIFY2(branch.contains(QStringLiteral("QMessageBox::warning")),
             "manual update-check failures should show a warning dialog");
    QVERIFY2(branch.contains(QStringLiteral("errorMessage.isEmpty()")),
             "manual update-check failures should include the detailed error when available");
    QVERIFY2(branch.contains(QStringLiteral("Update check failed: ")),
             "manual update-check failures should show the same failure context as the log");
}

void ScanSettingsWiringTests::settings_dialog_handles_not_published_as_benign()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/settingsdialog.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    const qsizetype branchStart = sourceText.indexOf(QStringLiteral("classification == \"not_published\""));
    QVERIFY2(branchStart >= 0, "SettingsDialog should handle not_published separately");

    const qsizetype nextBranch = sourceText.indexOf(QStringLiteral("} else {"), branchStart);
    QVERIFY2(nextBranch > branchStart, "not_published should be handled before the generic fallback branch");

    const QString branch = sourceText.mid(branchStart, nextBranch - branchStart);
    QVERIFY2(branch.contains(QStringLiteral("No update information available.")),
             "SettingsDialog should show a benign not_published message");
    QVERIFY2(!branch.contains(QStringLiteral("Error:")), "SettingsDialog must not render not_published as an error");
}

void ScanSettingsWiringTests::mainwindow_blocks_game_files_scan_when_paths_unresolved()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    const auto extractFunctionBody = [&](const QString& signature) -> QString {
        const QString marker = QStringLiteral("void MainWindow::") + signature;
        const qsizetype start = sourceText.indexOf(marker);
        if (start < 0) {
            return {};
        }

        const qsizetype nextFunction = sourceText.indexOf(QStringLiteral("\nvoid MainWindow::"), start + marker.size());
        const qsizetype end = (nextFunction < 0) ? sourceText.size() : nextFunction;
        return sourceText.mid(start, end - start);
    };

    const QString body = extractFunctionBody(QStringLiteral("onScanGameFiles()"));
    QVERIFY2(!body.isEmpty(), "MainWindow game file scan slot should exist");

    const QRegularExpression guardRegex(QStringLiteral(
        R"(loadValidatedGameAndDocsPaths\(&gameRoot,\s*&docsPath\)\)\s*\{(?:.|\n)*?QMessageBox::warning(?:.|\n)*?Game folder and INI folder paths are required(?:.|\n)*?return;)"));
    QVERIFY2(guardRegex.match(body).hasMatch(),
             "MainWindow game-file scan should guard on unresolved paths inside onScanGameFiles() and return early");
}

void ScanSettingsWiringTests::mainwindow_blocks_crash_logs_scan_when_fcx_enabled_and_paths_unresolved()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    const auto extractFunctionBody = [&](const QString& signature) -> QString {
        const QString marker = QStringLiteral("void MainWindow::") + signature;
        const qsizetype start = sourceText.indexOf(marker);
        if (start < 0) {
            return {};
        }

        const qsizetype nextFunction = sourceText.indexOf(QStringLiteral("\nvoid MainWindow::"), start + marker.size());
        const qsizetype end = (nextFunction < 0) ? sourceText.size() : nextFunction;
        return sourceText.mid(start, end - start);
    };

    const QString body = extractFunctionBody(QStringLiteral("onScanCrashLogs()"));
    QVERIFY2(!body.isEmpty(), "MainWindow crash-log scan slot should exist");

    const QRegularExpression guardRegex(QStringLiteral(
        R"(if\s*\(launchSettings\.fcxMode\)\s*\{(?:.|\n)*?loadValidatedGameAndDocsPaths\(&setupGameRoot,\s*&setupDocsPath\)(?:.|\n)*?FCX mode requires valid game and INI folder paths(?:.|\n)*?return;)"));
    QVERIFY2(
        guardRegex.match(body).hasMatch(),
        "MainWindow crash-log scan should gate FCX mode on validated paths inside onScanCrashLogs() and return early");
    QVERIFY2(body.contains(QStringLiteral("resolve_fallout4_exe_name(launchSettings.gameVersion.toStdString())")) &&
                 body.contains(QStringLiteral("classic::gui::normalizeGameExecutablePath(")),
             "MainWindow FCX scan should use the selected version and shared executable normalization rule");
}

void ScanSettingsWiringTests::mainwindow_resets_stale_game_exe_path_outside_selected_root()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    const auto extractFunctionBody = [&](const QString& signature) -> QString {
        const QString marker = QStringLiteral("void MainWindow::") + signature;
        const qsizetype start = sourceText.indexOf(marker);
        if (start < 0) {
            return {};
        }

        const qsizetype nextFunction = sourceText.indexOf(QStringLiteral("\nvoid MainWindow::"), start + marker.size());
        const qsizetype end = (nextFunction < 0) ? sourceText.size() : nextFunction;
        return sourceText.mid(start, end - start);
    };

    const QString body = extractFunctionBody(QStringLiteral("onScanGameFiles()"));
    QVERIFY2(!body.isEmpty(), "MainWindow game-file scan slot should exist");
    QVERIFY2(body.contains(QStringLiteral("GameSetupUserSettings::open")) &&
                 body.contains(QStringLiteral("startScan(m_dataRoot, xseLogPath)")),
             "MainWindow should delegate executable and path interpretation to typed Rust intake");
    QVERIFY2(!body.contains(QStringLiteral("yaml_ops")) && !body.contains(QStringLiteral("CLASSIC_Settings.")),
             "MainWindow game-file scan should not reinterpret raw setup settings");
}

void ScanSettingsWiringTests::mainwindow_uses_exe_relative_crash_logs_dir()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    const auto extractFunctionBody = [&](const QString& signature) -> QString {
        const QString marker = QStringLiteral("QString MainWindow::") + signature;
        const qsizetype start = sourceText.indexOf(marker);
        if (start < 0) {
            return {};
        }

        const qsizetype nextFunction = sourceText.indexOf(QStringLiteral("\nbool MainWindow::"), start + marker.size());
        const qsizetype end = (nextFunction < 0) ? sourceText.size() : nextFunction;
        return sourceText.mid(start, end - start);
    };

    const QString body = extractFunctionBody(QStringLiteral("readCrashLogsDir() const"));
    QVERIFY2(!body.isEmpty(), "MainWindow::readCrashLogsDir() should exist");
    QVERIFY2(body.contains(QStringLiteral("QCoreApplication::applicationDirPath()")),
             "MainWindow should resolve Crash Logs relative to the GUI executable directory");
    QVERIFY2(!body.contains(QStringLiteral("CLASSIC_Settings.Crash Logs Folder")),
             "MainWindow should not load a separate Crash Logs Folder setting");
    QVERIFY2(!body.contains(QStringLiteral("QDir::current().filePath(QStringLiteral(\"Crash Logs\"))")),
             "MainWindow should not fall back to the current working directory for Crash Logs");
}

void ScanSettingsWiringTests::controllers_emit_global_scan_started_signal_on_scan_start()
{
    const QString scanControllerPath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/controllers/scancontroller.cpp");
    QFile scanControllerFile(scanControllerPath);
    QVERIFY2(scanControllerFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(scanControllerPath)));
    const QString scanControllerSource = QString::fromUtf8(scanControllerFile.readAll());
    QVERIFY2(scanControllerSource.contains(QStringLiteral("emit m_signalHub->scanStarted();")),
             "ScanController should emit SignalHub::scanStarted() when a crash scan begins");

    const QString gameFilesControllerPath =
        QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/controllers/gamefilescontroller.cpp");
    QFile gameFilesControllerFile(gameFilesControllerPath);
    QVERIFY2(gameFilesControllerFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(gameFilesControllerPath)));
    const QString gameFilesControllerSource = QString::fromUtf8(gameFilesControllerFile.readAll());
    QVERIFY2(gameFilesControllerSource.contains(QStringLiteral("emit m_signalHub->scanStarted();")),
             "GameFilesController should emit SignalHub::scanStarted() when a game-files scan begins");
}

void ScanSettingsWiringTests::scan_controller_delegates_xse_folder_resolution_to_core()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/controllers/scancontroller.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(!sourceText.contains(QStringLiteral("Game_Info.Docs_Folder_XSE")),
             "ScanController should not parse Docs_Folder_XSE itself");
    QVERIFY2(!sourceText.contains(QStringLiteral("Game_Info.Root_Folder_Docs")),
             "ScanController should not parse Root_Folder_Docs itself");
    QVERIFY2(!sourceText.contains(QStringLiteral("classic::settings::yaml_ops")),
             "ScanController should not load Local.yaml through settings helpers");
}

void ScanSettingsWiringTests::mainwindow_enables_drag_and_drop()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("setAcceptDrops(true)")),
             "MainWindow should enable drag-and-drop via setAcceptDrops(true)");
    QVERIFY2(sourceText.contains(QStringLiteral("handleTargetedDrop")),
             "MainWindow should route drop handling through a shared targeted-drop helper");
    QVERIFY2(sourceText.contains(QStringLiteral("handleTargetedDragEnter")),
             "MainWindow should route drag-enter handling through a shared targeted-drop helper");
    QVERIFY2(sourceText.contains(QStringLiteral("currentIndex() == 0")),
             "Drag-and-drop should be restricted to the Main Options tab (index 0)");
}

void ScanSettingsWiringTests::mainwindow_forwards_drops_through_targeted_child_event_filter()
{
    const QString headerPath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.h");
    QFile headerFile(headerPath);
    QVERIFY2(headerFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(headerPath)));

    const QString headerText = QString::fromUtf8(headerFile.readAll());
    QVERIFY2(headerText.contains(QStringLiteral("bool eventFilter(QObject* watched, QEvent* event) override;")),
             "MainWindow should override eventFilter to forward targeted-area drops from child widgets");

    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile sourceFile(sourcePath);
    QVERIFY2(sourceFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(sourceFile.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("installTargetedDropForwarding")),
             "MainWindow should install targeted drop forwarding after creating the drop zone");
    QVERIFY2(sourceText.contains(QStringLiteral("m_targetedInputContainer->installEventFilter(this)")) ||
                 sourceText.contains(QStringLiteral("installEventFilter(this)")),
             "MainWindow should install itself as the event filter for targeted drop widgets");
    QVERIFY2(sourceText.contains(QStringLiteral("m_targetedInputLabel")) &&
                 sourceText.contains(QStringLiteral("m_targetedInputList")) &&
                 sourceText.contains(QStringLiteral("m_btnClearTargeted")),
             "MainWindow should forward drops from all visible targeted-input child widgets");
    QVERIFY2(sourceText.contains(QStringLiteral("m_targetedInputList ? m_targetedInputList->viewport() : nullptr")) &&
                 sourceText.contains(QStringLiteral("watched == m_targetedInputList->viewport()")),
             "MainWindow should forward drops that land on the QListWidget viewport");
}

void ScanSettingsWiringTests::mainwindow_forwards_drag_moves_through_targeted_child_event_filter()
{
    const QString headerPath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.h");
    QFile headerFile(headerPath);
    QVERIFY2(headerFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(headerPath)));

    const QString headerText = QString::fromUtf8(headerFile.readAll());
    QVERIFY2(headerText.contains(QStringLiteral("bool handleTargetedDragMove(QDragMoveEvent* event)")),
             "MainWindow should expose a shared targeted drag-move helper");
    QVERIFY2(headerText.contains(QStringLiteral("void dragMoveEvent(QDragMoveEvent* event) override")),
             "MainWindow should override dragMoveEvent for top-level targeted drags");

    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile sourceFile(sourcePath);
    QVERIFY2(sourceFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(sourceFile.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("case QEvent::DragMove:")),
             "MainWindow eventFilter should handle DragMove on targeted drop surfaces");
    QVERIFY2(sourceText.contains(QStringLiteral("handleTargetedDragMove")),
             "MainWindow should route drag-move handling through a shared targeted-drop helper");
}

void ScanSettingsWiringTests::mainwindow_acknowledges_duplicate_non_local_and_unsupported_drops()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("acknowledgeTargetedDrop")),
             "MainWindow should acknowledge targeted drops that do not add new paths");
    QVERIFY2(sourceText.contains(QStringLiteral("duplicateCount")),
             "MainWindow should track duplicate targeted drops for user acknowledgement");
    QVERIFY2(sourceText.contains(QStringLiteral("nonLocalCount")),
             "MainWindow should track non-local URL drops for user acknowledgement");
    QVERIFY2(sourceText.contains(QStringLiteral("unsupportedPayload")),
             "MainWindow should acknowledge unsupported drop payloads");
    QVERIFY2(sourceText.contains(QStringLiteral("Skipped %1 duplicate path%2 already in the list.")),
             "MainWindow should surface duplicate-drop acknowledgement in the status bar");
    QVERIFY2(sourceText.contains(QStringLiteral("Skipped %1 non-local URL%2; only local files are supported.")),
             "MainWindow should surface non-local URL acknowledgement in the status bar");
}

void ScanSettingsWiringTests::mainwindow_reports_wrong_tab_drops()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("Switch to the Main Options tab to add targeted scan inputs.")),
             "MainWindow should tell users to switch tabs when dropping on a non-main tab");
}

void ScanSettingsWiringTests::mainwindow_passes_targeted_inputs_to_scan_controller()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("m_targetedInputPaths")),
             "MainWindow should pass m_targetedInputPaths to ScanController");
}

void ScanSettingsWiringTests::mainwindow_has_clear_targeted_inputs_slot()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("onClearTargetedInputs")),
             "MainWindow should have an onClearTargetedInputs slot");
    QVERIFY2(sourceText.contains(QStringLiteral("m_targetedInputPaths.clear()")),
             "onClearTargetedInputs should clear the targeted input paths list");
}

void ScanSettingsWiringTests::mainwindow_sizes_clear_targeted_button_to_fit_text()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(!sourceText.contains(QStringLiteral("m_btnClearTargeted->setFixedWidth(60)")),
             "The targeted input Clear button should not be locked to a clipping-prone 60px width");
    QVERIFY2(sourceText.contains(QStringLiteral("m_btnClearTargeted->setMinimumWidth(")),
             "The targeted input Clear button should use a minimum width that can grow with text metrics");
    QVERIFY2(sourceText.contains(QStringLiteral("m_btnClearTargeted->setSizePolicy(QSizePolicy::Minimum")),
             "The targeted input Clear button should keep a button-sized minimum while allowing theme/font growth");
}

void ScanSettingsWiringTests::mainwindow_refreshes_layout_when_targeted_list_visibility_changes()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    const QString marker = QStringLiteral("void MainWindow::updateTargetedInputUi()");
    const qsizetype start = sourceText.indexOf(marker);
    QVERIFY2(start >= 0, "Could not locate MainWindow::updateTargetedInputUi()");

    const qsizetype nextFunction = sourceText.indexOf(QStringLiteral("\nvoid MainWindow::"), start + marker.size());
    const qsizetype end = (nextFunction < 0) ? sourceText.size() : nextFunction;
    const QString body = sourceText.mid(start, end - start);

    QVERIFY2(body.contains(QStringLiteral("updateGeometry()")),
             "updateTargetedInputUi should notify layouts after the file list visibility changes");
    QVERIFY2(body.contains(QStringLiteral("layout()->activate()")),
             "updateTargetedInputUi should force the main layout to react when the file list is populated");
    QVERIFY2(body.contains(QStringLiteral("sizeHint()")),
             "updateTargetedInputUi should resize the window upward when visible targeted inputs need more room");
}

void ScanSettingsWiringTests::mainwindow_wires_scan_warnings_to_user_feedback()
{
    const QString headerPath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.h");
    QFile headerFile(headerPath);
    QVERIFY2(headerFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(headerPath)));

    const QString headerText = QString::fromUtf8(headerFile.readAll());
    QVERIFY2(headerText.contains(QStringLiteral("void onScanWarning(const QString& message);")),
             "MainWindow should define a slot for non-fatal scan warnings");

    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile sourceFile(sourcePath);
    QVERIFY2(sourceFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(sourceFile.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("&ScanController::scanWarning")),
             "MainWindow should connect ScanController::scanWarning to user-visible feedback");
    QVERIFY2(sourceText.contains(QStringLiteral("QMessageBox::warning(this, QStringLiteral(\"Scan Warning\")")),
             "MainWindow should surface scan warnings through a warning dialog");
}

void ScanSettingsWiringTests::mainwindow_includes_last_scan_report_dirs_in_results_setup()
{
    const QString headerPath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.h");
    QFile headerFile(headerPath);
    QVERIFY2(headerFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(headerPath)));

    const QString headerText = QString::fromUtf8(headerFile.readAll());
    QVERIFY2(headerText.contains(QStringLiteral("QStringList m_lastScanReportDirs;")),
             "MainWindow should retain report directories resolved for the active or last scan");
    QVERIFY2(
        headerText.contains(QStringLiteral("void onScanReportDirectoriesResolved(const QStringList& reportDirs);")),
        "MainWindow should define a slot to receive resolved report directories from ScanController");

    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile sourceFile(sourcePath);
    QVERIFY2(sourceFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(sourceFile.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("&ScanController::scanReportDirectoriesResolved")),
             "MainWindow should listen for resolved report directories from ScanController");
    QVERIFY2(sourceText.contains(QStringLiteral("m_lastScanReportDirs")),
             "MainWindow::initResultsReportDir should include last scan report directories");
}

void ScanSettingsWiringTests::mainwindow_seeds_targeted_report_dirs_before_scan_finishes()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile sourceFile(sourcePath);
    QVERIFY2(sourceFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(sourceFile.readAll());
    const QRegularExpression slotRegex(QStringLiteral(
        R"(void MainWindow::onScanReportDirectoriesResolved\(const QStringList& reportDirs\)\s*\{(?<body>(?:.|\n)*?)\n\})"));
    const QRegularExpressionMatch match = slotRegex.match(sourceText);
    QVERIFY2(match.hasMatch(), "MainWindow::onScanReportDirectoriesResolved() should exist");

    const QString body = match.captured(QStringLiteral("body"));
    QVERIFY2(body.contains(QStringLiteral("m_lastScanReportDirs = reportDirs;")),
             "MainWindow should retain targeted report directories");
    QVERIFY2(body.contains(QStringLiteral("initResultsReportDir();")),
             "MainWindow should seed targeted report directory baselines before scan completion");
}

void ScanSettingsWiringTests::mainwindow_deduplicates_report_dirs_before_results_setup()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile sourceFile(sourcePath);
    QVERIFY2(sourceFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(sourceFile.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("QSet<QString> seenReportDirs;")),
             "MainWindow should deduplicate report directories before updating ResultsController");
    QVERIFY2(sourceText.contains(QStringLiteral("seenReportDirs.insert(key);")),
             "MainWindow should track report directories case-insensitively before appending them");
}

void ScanSettingsWiringTests::local_ignore_recovery_is_prompted_and_resumed_across_gui_layers()
{
    const QString workerPath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/workers/scanworker.cpp");
    QFile workerFile(workerPath);
    QVERIFY2(workerFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(workerPath)));
    const QString workerText = QString::fromUtf8(workerFile.readAll());
    QVERIFY2(workerText.contains(QStringLiteral("scan_run_contract_execution_take_continuation")) &&
                 workerText.contains(QStringLiteral("scan_run_continuation_resume")),
             "ScanWorker should consume and resume Rust's retained recovery continuation");

    const QString controllerPath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/controllers/scancontroller.cpp");
    QFile controllerFile(controllerPath);
    QVERIFY2(controllerFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(controllerPath)));
    const QString controllerText = QString::fromUtf8(controllerFile.readAll());
    QVERIFY2(controllerText.contains(QStringLiteral("Qt::BlockingQueuedConnection")) &&
                 controllerText.contains(QStringLiteral("requestLocalIgnoreRecoveryChoice")),
             "ScanController should obtain the recovery decision on the GUI thread while the worker remains paused");

    const QString mainWindowPath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile mainWindowFile(mainWindowPath);
    QVERIFY2(mainWindowFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(mainWindowPath)));
    const QString mainWindowText = QString::fromUtf8(mainWindowFile.readAll());
    QVERIFY2(mainWindowText.contains(QStringLiteral("setLocalIgnoreRecoveryPrompt")) &&
                 mainWindowText.contains(QStringLiteral("Back Up && Reset to Default")) &&
                 mainWindowText.contains(QStringLiteral("Continue Without Ignore")) &&
                 mainWindowText.contains(QStringLiteral("QMessageBox::Cancel")),
             "MainWindow should present reset, non-mutating continuation, and cancellation choices");
}

void ScanSettingsWiringTests::installed_yaml_data_propagates_from_worker_to_user_visible_terminal_status()
{
    const QString workerHeaderPath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/workers/scanworker.h");
    QFile workerHeader(workerHeaderPath);
    QVERIFY2(workerHeader.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(workerHeaderPath)));
    const QString workerHeaderText = QString::fromUtf8(workerHeader.readAll());
    QVERIFY2(workerHeaderText.contains(QStringLiteral("installedYamlDataResolved")),
             "ScanWorker should publish the Qt-owned Installed YAML Data projection");

    const QString controllerPath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/controllers/scancontroller.cpp");
    QFile controllerFile(controllerPath);
    QVERIFY2(controllerFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(controllerPath)));
    const QString controllerText = QString::fromUtf8(controllerFile.readAll());
    QVERIFY2(controllerText.contains(QStringLiteral("&ScanWorker::installedYamlDataResolved")) &&
                 controllerText.contains(QStringLiteral("&ScanController::scanInstalledYamlDataResolved")),
             "ScanController should relay Installed YAML Data across the worker-thread boundary");

    const QString mainWindowPath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile mainWindowFile(mainWindowPath);
    QVERIFY2(mainWindowFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(mainWindowPath)));
    const QString mainWindowText = QString::fromUtf8(mainWindowFile.readAll());
    QVERIFY2(mainWindowText.contains(QStringLiteral("&ScanController::scanInstalledYamlDataResolved")),
             "MainWindow should receive the exact Installed YAML Data selected for the run");
    QVERIFY2(mainWindowText.contains(QStringLiteral("m_lastInstalledYamlData = installedYamlData;")),
             "MainWindow should retain Installed YAML Data after the worker result is destroyed");
    QVERIFY2(mainWindowText.contains(QStringLiteral("installedYamlDataStatusSuffix()")),
             "MainWindow should include selected YAML Data metadata in user-visible terminal status");
}

QTEST_MAIN(ScanSettingsWiringTests)
#include "test_scan_settings_wiring.moc"
