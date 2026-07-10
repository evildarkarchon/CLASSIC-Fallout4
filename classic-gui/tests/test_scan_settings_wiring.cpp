#include <QFile>
#include <QRegularExpression>
#include <QtTest/QtTest>

class ScanSettingsWiringTests : public QObject {
    Q_OBJECT

private slots:
    void scan_worker_forwards_runtime_flags_to_rust_config();
    void scan_controller_forwards_flags_to_worker();
    void scan_pipeline_forwards_existing_xse_log_hint();
    void mainwindow_forwards_scan_flags_to_controller();
    void mainwindow_forwards_game_version_to_scan_controller();
    void mainwindow_forwards_game_version_to_game_files_controller();
    void game_files_controller_forwards_game_version_to_worker();
    void game_files_worker_forwards_game_version_to_setup_intake();
    void game_files_worker_marks_required_actions_as_attention();
    void game_files_worker_catches_non_standard_exceptions();
    void scan_worker_handles_move_unsolved_and_max_concurrent_settings();
    void scan_worker_uses_progress_enabled_batch_api();
    void scan_worker_forwards_batch_counts_in_progress_updates();
    void scan_worker_defaults_to_batch_for_multi_log_scans();
    void mainwindow_wires_live_crash_scan_progress_updates();
    void mainwindow_does_not_use_deprecated_vr_mode_setting();
    /// Verifies that MainWindow honors canonical custom-scan reads, writes, and clears.
    void mainwindow_honors_canonical_custom_scan_path();
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
    void scan_controller_uses_exe_dir_and_xse_resolver_for_log_collection();
    void scan_controller_delegates_xse_folder_resolution_to_core();
    void settings_dialog_wires_game_folder_path_controls();
    void settings_dialog_resets_stale_game_exe_path_when_game_folder_changes();
    void settings_dialog_adds_multiple_formid_databases();
    void mainwindow_enables_drag_and_drop();
    void mainwindow_forwards_drops_through_targeted_child_event_filter();
    void mainwindow_forwards_drag_moves_through_targeted_child_event_filter();
    void mainwindow_acknowledges_duplicate_non_local_and_unsupported_drops();
    void mainwindow_reports_wrong_tab_drops();
    void mainwindow_passes_targeted_inputs_to_scan_controller();
    void scan_controller_routes_targeted_inputs_through_bridge_resolver();
    void scan_controller_appends_targeted_resolved_logs_without_filename_filter();
    void mainwindow_has_clear_targeted_inputs_slot();
    void mainwindow_sizes_clear_targeted_button_to_fit_text();
    void mainwindow_refreshes_layout_when_targeted_list_visibility_changes();
    void scan_controller_surfaces_targeted_rejections_to_gui();
    void scan_controller_logs_targeted_rejections_with_reason_fallback();
    void mainwindow_wires_scan_warnings_to_user_feedback();
    void scan_controller_emits_targeted_report_directories();
    void mainwindow_includes_last_scan_report_dirs_in_results_setup();
    void mainwindow_seeds_targeted_report_dirs_before_scan_finishes();
    void mainwindow_deduplicates_report_dirs_before_results_setup();
    void scan_controller_disables_unsolved_relocation_for_targeted_runs();
    void scan_worker_skips_unsolved_relocation_for_targeted_runs();
    void scan_worker_counts_per_log_failures_without_scan_level_error();
};

void ScanSettingsWiringTests::scan_worker_forwards_runtime_flags_to_rust_config()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/workers/scanworker.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("scan_run_execute(")),
             "ScanWorker should call the Rust Crash Log Scan Run seam");
    QVERIFY2(sourceText.contains(QStringLiteral("classic::toRustString(gameVersion)")),
             "ScanWorker should forward gameVersion to scan_run_execute()");
    QVERIFY2(sourceText.contains(QStringLiteral("showFormIdValues")),
             "ScanWorker should forward showFormIdValues to scan_run_execute()");
    QVERIFY2(sourceText.contains(QStringLiteral("fcxMode")),
             "ScanWorker should forward fcxMode to scan_run_execute()");
    QVERIFY2(sourceText.contains(QStringLiteral("simplifyLogs")),
             "ScanWorker should forward simplifyLogs to scan_run_execute()");
    QVERIFY2(sourceText.contains(QStringLiteral("request.setup_xse_log_path = classic::toRustString(setupXseLogPath)")),
             "ScanWorker should forward the setup XSE log path instead of discarding it");
}

void ScanSettingsWiringTests::scan_controller_forwards_flags_to_worker()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/controllers/scancontroller.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());

    const qsizetype callStart = sourceText.indexOf(QStringLiteral("worker->doScan("));
    QVERIFY2(callStart >= 0, "ScanController should call ScanWorker::doScan()");
    const qsizetype callEnd = sourceText.indexOf(QStringLiteral(");"), callStart);
    QVERIFY2(callEnd > callStart, "ScanController should have a complete ScanWorker::doScan() call");
    const QString call = sourceText.mid(callStart, callEnd - callStart);
    for (const QString& expected : {QStringLiteral("gameVersion"), QStringLiteral("showFormIdValues"),
                                    QStringLiteral("fcxMode"), QStringLiteral("simplifyLogs"),
                                    QStringLiteral("moveUnsolvedLogs"), QStringLiteral("unsolvedLogsDestination"),
                                    QStringLiteral("maxConcurrentScans"), QStringLiteral("baseDir"),
                                    QStringLiteral("customFolder"), QStringLiteral("setupGameRoot"),
                                    QStringLiteral("setupDocsRoot"), QStringLiteral("setupGameExePath"),
                                    QStringLiteral("setupXseLogPath"), QStringLiteral("targetedMode"),
                                    QStringLiteral("targetedInputs")}) {
        QVERIFY2(call.contains(expected),
                 qPrintable(QStringLiteral("ScanController should pass %1 to ScanWorker::doScan()").arg(expected)));
    }
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

void ScanSettingsWiringTests::mainwindow_forwards_scan_flags_to_controller()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());

    const QRegularExpression callRegex(QStringLiteral(
        R"(m_scanController->startScan\((?:.|\n)*?m_showFormIdValues,\s*m_fcxMode,\s*m_simplifyLogs\s*,(?:.|\n)*?\))"));
    QVERIFY2(callRegex.match(sourceText).hasMatch(),
             "MainWindow should forward loaded scan settings to ScanController::startScan()");
}

void ScanSettingsWiringTests::mainwindow_forwards_game_version_to_scan_controller()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());

    const QRegularExpression callRegex(QStringLiteral(
        R"(m_scanController->startScan\((?:.|\n)*?m_gameVersion,\s*m_showFormIdValues,\s*m_fcxMode,\s*m_simplifyLogs,\s*m_moveUnsolvedLogs,\s*m_unsolvedLogsDestination,\s*m_maxConcurrentScans\s*,(?:.|\n)*?\))"));
    QVERIFY2(callRegex.match(sourceText).hasMatch(),
             "MainWindow should forward game version and all scan settings to ScanController::startScan()");
}

void ScanSettingsWiringTests::mainwindow_forwards_game_version_to_game_files_controller()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());

    const QRegularExpression callRegex(QStringLiteral(
        R"(m_gameFilesController->startScan\(\s*gameExePath,\s*gameRoot,\s*docsPath,\s*gameName,\s*m_gameVersion\s*\))"));
    QVERIFY2(callRegex.match(sourceText).hasMatch(),
             "MainWindow should forward the saved game version to GameFilesController::startScan()");
}

void ScanSettingsWiringTests::game_files_controller_forwards_game_version_to_worker()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/controllers/gamefilescontroller.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());

    QVERIFY2(sourceText.contains(QStringLiteral("const QString& gameVersion")),
             "GameFilesController::startScan() should receive the selected game version");
    const QRegularExpression workerCallRegex(
        QStringLiteral(R"(worker->doScan\((?:.|\n)*?gameName,\s*gameVersion\s*\))"));
    QVERIFY2(workerCallRegex.match(sourceText).hasMatch(),
             "GameFilesController should pass gameVersion through to GameFilesWorker::doScan()");
}

void ScanSettingsWiringTests::game_files_worker_forwards_game_version_to_setup_intake()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/workers/gamefilesworker.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());

    QVERIFY2(sourceText.contains(QStringLiteral("const QString& gameVersion")),
             "GameFilesWorker::doScan() should receive the selected game version");
    QVERIFY2(!sourceText.contains(QStringLiteral("Q_UNUSED(gameExePath)")),
             "GameFilesWorker should not discard the configured executable path");
    QVERIFY2(sourceText.contains(QStringLiteral("classic::toRustString(gameVersion)")),
             "GameFilesWorker should forward gameVersion to run_game_setup_intake()");
    QVERIFY2(sourceText.contains(QStringLiteral("classic::toRustString(gameExePath)")),
             "GameFilesWorker should forward the configured executable path to setup intake");
    QVERIFY2(!sourceText.contains(QStringLiteral("::rust::Str(\"auto\", 4)")),
             "GameFilesWorker should not force setup intake back to auto detection");
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

void ScanSettingsWiringTests::scan_worker_handles_move_unsolved_and_max_concurrent_settings()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/workers/scanworker.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("moveUnsolvedLogs")),
              "ScanWorker should receive moveUnsolvedLogs setting");
    QVERIFY2(sourceText.contains(QStringLiteral("unsolvedLogsDestination")),
             "ScanWorker should receive the custom Unsolved Logs Destination setting");
    QVERIFY2(sourceText.contains(QStringLiteral("request.unsolved_logs_destination")),
             "ScanWorker should forward the custom Unsolved Logs Destination to Rust");
    QVERIFY2(sourceText.contains(QStringLiteral("maxConcurrentScans")),
              "ScanWorker should receive maxConcurrentScans setting");
}

void ScanSettingsWiringTests::scan_worker_uses_progress_enabled_batch_api()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/workers/scanworker.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("BatchProgressCallback")),
             "ScanWorker should define a CXX batch progress callback adapter");
    QVERIFY2(sourceText.contains(QStringLiteral("BatchProgressEvent")),
             "ScanWorker should consume the richer batch progress event payload");
    QVERIFY2(sourceText.contains(QStringLiteral("scan_run_execute")),
             "ScanWorker should use the CXX Crash Log Scan Run API that reports progress");
}

void ScanSettingsWiringTests::scan_worker_forwards_batch_counts_in_progress_updates()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/workers/scanworker.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("event.completed")),
             "ScanWorker should forward completed-count progress from BatchProgressEvent");
    QVERIFY2(sourceText.contains(QStringLiteral("event.total")),
             "ScanWorker should forward total-count progress from BatchProgressEvent");
    QVERIFY2(sourceText.contains(QStringLiteral("progressDetailed(percent, status, completed, total)")),
             "ScanWorker should emit batch progress updates with structured completed and total counts");
}

void ScanSettingsWiringTests::scan_worker_defaults_to_batch_for_multi_log_scans()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/workers/scanworker.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("scan_run_execute")),
             "ScanWorker should delegate both single-log and multi-log runs to Rust");
    const QRegularExpression batchGateRegex(QStringLiteral(R"(if\s*\(\s*total\s*>\s*1\s*\))"));
    QVERIFY2(!batchGateRegex.match(sourceText).hasMatch(),
             "ScanWorker should not preserve a separate C++ batch-mode branch");
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

void ScanSettingsWiringTests::mainwindow_honors_canonical_custom_scan_path()
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

    const QString loadBody = extractFunctionBody(QStringLiteral("loadSettings()"));
    QVERIFY2(loadBody.contains(QStringLiteral("user_settings_open_crash_log_scan_settings")),
             "MainWindow should load the effective custom path through typed User Settings precedence");
    QVERIFY2(loadBody.contains(QStringLiteral("has_custom_scan_input")) &&
                 loadBody.contains(QStringLiteral("custom_scan_input")),
             "MainWindow should display the effective canonical-or-alias custom scan path");

    const QString saveBody = extractFunctionBody(QStringLiteral("saveSettings()"));
    QVERIFY2(saveBody.contains(QStringLiteral("CLASSIC_Settings.SCAN Custom Path")),
             "MainWindow should persist custom scan edits to the canonical User Settings key");
    QVERIFY2(!saveBody.contains(QStringLiteral("CLASSIC_Settings.Custom Scan Folder")),
             "MainWindow should not leave edits only on the lower-precedence GUI-era alias");

    const QString editedBody = extractFunctionBody(QStringLiteral("onCustomFolderEdited()"));
    QCOMPARE(editedBody.count(QStringLiteral("saveSettings();")), 3);
    QVERIFY2(!editedBody.contains(QStringLiteral("CLASSIC_Settings.Custom Scan Folder")),
             "MainWindow should not clear only the GUI-era alias while a canonical value remains active");
}

void ScanSettingsWiringTests::mainwindow_preserves_legacy_settings_on_failed_migration()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    const QRegularExpression successOnlyRemovalRegex(QStringLiteral(
        R"(if\s*\(moved\s*&&\s*QFile::exists\(settingsPath\)\)\s*\{\s*QFile::remove\(legacySettingsPath\);(?:.|\n)*?return\s+true;\s*\})"));
    QVERIFY2(successOnlyRemovalRegex.match(sourceText).hasMatch(),
             "MainWindow settings bootstrap should only remove the legacy settings file after migration succeeds");
    const QRegularExpression atomicFallbackRegex(QStringLiteral(
        R"(QSaveFile\s+\w+\(settingsPath\);(?:.|\n)*?setDirectWriteFallback\(false\);(?:.|\n)*?commit\(\))"));
    QVERIFY2(atomicFallbackRegex.match(sourceText).hasMatch(),
             "MainWindow settings bootstrap should use QSaveFile for an atomic publish when rename fails");
    QVERIFY2(!sourceText.contains(QStringLiteral("QFile::copy(legacySettingsPath, settingsPath)")),
             "MainWindow settings bootstrap should not use QFile::copy directly for legacy settings migration");
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
    QVERIFY2(!branch.contains(QStringLiteral("Error:")),
             "SettingsDialog must not render not_published as an error");
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
        R"(if\s*\(m_fcxMode\)\s*\{(?:.|\n)*?loadValidatedGameAndDocsPaths\(&setupGameRoot,\s*&setupDocsPath\)(?:.|\n)*?FCX mode requires valid game and INI folder paths(?:.|\n)*?return;)"));
    QVERIFY2(
        guardRegex.match(body).hasMatch(),
        "MainWindow crash-log scan should gate FCX mode on validated paths inside onScanCrashLogs() and return early");
    QVERIFY2(body.contains(
                 QStringLiteral("classic::gui::normalizeGameExecutablePath(setupGameExePath, setupGameRoot)")),
             "MainWindow FCX scan should use the shared executable normalization rule");
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
    QVERIFY2(body.contains(QStringLiteral("classic::gui::normalizeGameExecutablePath(gameExePath, gameRoot)")),
             "MainWindow should use the shared executable normalization rule");
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

void ScanSettingsWiringTests::scan_controller_uses_exe_dir_and_xse_resolver_for_log_collection()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/controllers/scancontroller.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("classic::files::log_collector_new_for_scan")),
             "ScanController should delegate scan-time XSE Folder resolution to Rust file-IO core");
    QVERIFY2(sourceText.contains(QStringLiteral("classic::toRustString(gameVersion)")),
             "ScanController should forward gameVersion to XSE Folder resolution");
    QVERIFY2(sourceText.contains(QStringLiteral("QCoreApplication::applicationDirPath()")),
             "ScanController should collect crash logs relative to the GUI executable directory");
    QVERIFY2(!sourceText.contains(QStringLiteral("QDir::currentPath()")),
             "ScanController should not use the current working directory for crash-log collection");
    QVERIFY2(sourceText.contains(QStringLiteral("classic::toRustString(customFolder)")),
             "ScanController should continue forwarding the custom scan folder separately");
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

void ScanSettingsWiringTests::settings_dialog_wires_game_folder_path_controls()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/settingsdialog.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("CLASSIC_Settings.Game Folder Path")),
             "SettingsDialog should load and persist Game Folder Path");
    QVERIFY2(sourceText.contains(QStringLiteral("onBrowseGameFolder")),
             "SettingsDialog should provide browse wiring for Game Folder Path");
    QVERIFY2(sourceText.contains(QStringLiteral("onResetGameFolder")),
             "SettingsDialog should provide reset wiring for Game Folder Path");
}

void ScanSettingsWiringTests::settings_dialog_resets_stale_game_exe_path_when_game_folder_changes()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/settingsdialog.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    const auto extractFunctionBody = [&](const QString& signature) -> QString {
        const QString marker = signature;
        const qsizetype start = sourceText.indexOf(marker);
        if (start < 0) {
            return {};
        }

        const qsizetype nextFunction =
            sourceText.indexOf(QStringLiteral("\nvoid SettingsDialog::"), start + marker.size());
        const qsizetype end = (nextFunction < 0) ? sourceText.size() : nextFunction;
        return sourceText.mid(start, end - start);
    };

    const QString body = extractFunctionBody(QStringLiteral("bool SettingsDialog::saveSettings()"));
    QVERIFY2(!body.isEmpty(), "SettingsDialog::saveSettings() should exist");
    QVERIFY2(body.contains(QStringLiteral("classic::gui::normalizeGameExecutablePath(exePath, gameText)")),
             "SettingsDialog should use the shared executable normalization rule");
}

void ScanSettingsWiringTests::settings_dialog_adds_multiple_formid_databases()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/settingsdialog.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    const QString marker = QStringLiteral("void SettingsDialog::onAddFormIdDb()");
    const qsizetype start = sourceText.indexOf(marker);
    QVERIFY2(start >= 0, "SettingsDialog::onAddFormIdDb() should exist");

    const qsizetype nextFunction = sourceText.indexOf(QStringLiteral("\nvoid SettingsDialog::"), start + marker.size());
    const qsizetype end = (nextFunction < 0) ? sourceText.size() : nextFunction;
    const QString body = sourceText.mid(start, end - start);

    QVERIFY2(body.contains(QStringLiteral("QFileDialog::getOpenFileNames")),
             "FormID database Add should use a multi-select file dialog");
    QVERIFY2(body.contains(QStringLiteral("Select FormID Databases")),
             "FormID database Add dialog title should be plural");
    QVERIFY2(body.contains(QStringLiteral("const QStringList files")),
             "FormID database Add should retain the returned QStringList");
    QVERIFY2(body.contains(QStringLiteral("for (const QString& file : files)")),
             "FormID database Add should iterate selected files in order");
    QVERIFY2(body.contains(QStringLiteral("m_listFormIdDbs->addItem(file)")),
             "FormID database Add should append each selected file to the list widget");

    const qsizetype seenStart = body.indexOf(QStringLiteral("QSet<QString> seen"));
    const qsizetype guardStart = body.indexOf(QStringLiteral("seen.contains(key)"));
    const qsizetype addStart = body.indexOf(QStringLiteral("m_listFormIdDbs->addItem(file)"));
    const qsizetype insertAfterAdd = body.indexOf(QStringLiteral("seen.insert(key)"), addStart);
    QVERIFY2(seenStart >= 0, "FormID database Add should track normalized paths with QSet<QString>");
    QVERIFY2(guardStart > seenStart && guardStart < addStart,
             "FormID database Add should skip duplicate normalized paths before appending");
    QVERIFY2(insertAfterAdd > addStart, "FormID database Add should remember newly appended paths as seen");
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

void ScanSettingsWiringTests::scan_controller_routes_targeted_inputs_through_bridge_resolver()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/controllers/scancontroller.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("resolve_targeted_inputs")),
             "ScanController should call resolve_targeted_inputs for targeted mode");
    QVERIFY2(sourceText.contains(QStringLiteral("targetedInputs")),
             "ScanController::startScan should accept targetedInputs parameter");
    QVERIFY2(sourceText.contains(QStringLiteral("log_collector_collect_all")),
             "ScanController should still use log_collector_collect_all for default discovery");
}

void ScanSettingsWiringTests::scan_controller_appends_targeted_resolved_logs_without_filename_filter()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/controllers/scancontroller.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    const qsizetype targetedStart = sourceText.indexOf(QStringLiteral("if (targetedMode)"));
    QVERIFY2(targetedStart >= 0, "ScanController should have a targeted-mode branch");

    const qsizetype defaultStart = sourceText.indexOf(QStringLiteral("} else {"), targetedStart);
    QVERIFY2(defaultStart > targetedStart, "ScanController should separate targeted mode from default discovery");

    const QString targetedBranch = sourceText.mid(targetedStart, defaultStart - targetedStart);
    QVERIFY2(targetedBranch.contains(QStringLiteral("resolve_targeted_inputs")),
             "Targeted mode should use the Rust resolver before appending logs");
    QVERIFY2(targetedBranch.contains(QStringLiteral("logPathsList.append(qpath);")),
             "Targeted mode should append every path returned by the Rust resolver");
    QVERIFY2(!targetedBranch.contains(QStringLiteral("isCrashLogPath")),
             "Targeted mode should not reapply the GUI crash-*.log filename filter");
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

void ScanSettingsWiringTests::scan_controller_surfaces_targeted_rejections_to_gui()
{
    const QString headerPath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/controllers/scancontroller.h");
    QFile headerFile(headerPath);
    QVERIFY2(headerFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(headerPath)));

    const QString headerText = QString::fromUtf8(headerFile.readAll());
    QVERIFY2(headerText.contains(QStringLiteral("void scanWarning(const QString& message);")),
             "ScanController should expose a non-fatal scanWarning signal for targeted-input rejections");

    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/controllers/scancontroller.cpp");
    QFile sourceFile(sourcePath);
    QVERIFY2(sourceFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(sourceFile.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("emit scanWarning(")),
             "ScanController should emit scanWarning when targeted inputs are rejected");
}

void ScanSettingsWiringTests::scan_controller_logs_targeted_rejections_with_reason_fallback()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/controllers/scancontroller.cpp");
    QFile sourceFile(sourcePath);
    QVERIFY2(sourceFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(sourceFile.readAll());
    const QRegularExpression warningLoopRegex(QString::fromLatin1(
        R"REGEX(for\s*\(size_t i = 0; i < resolution\.rejected_paths\.size\(\); \+\+i\)\s*\{(?:.|\n)*?const QString reason = i < resolution\.rejected_reasons\.size\(\)\s*\?\s*classic::toQString\(resolution\.rejected_reasons\[i\]\)\s*:\s*QStringLiteral\("unknown reason"\);(?:.|\n)*?qWarning\("Targeted input rejected: %s \(%s\)",(?:.|\n)*?qPrintable\(reason\)\);(?:.|\n)*?\})REGEX"));
    QVERIFY2(warningLoopRegex.match(sourceText).hasMatch(),
             "ScanController should guard targeted rejection logging against missing rejection reasons");
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

void ScanSettingsWiringTests::scan_controller_emits_targeted_report_directories()
{
    const QString headerPath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/controllers/scancontroller.h");
    QFile headerFile(headerPath);
    QVERIFY2(headerFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(headerPath)));

    const QString headerText = QString::fromUtf8(headerFile.readAll());
    QVERIFY2(headerText.contains(QStringLiteral("void scanReportDirectoriesResolved(const QStringList& reportDirs);")),
             "ScanController should expose resolved report directories for the current scan");

    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/controllers/scancontroller.cpp");
    QFile sourceFile(sourcePath);
    QVERIFY2(sourceFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(sourceFile.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("emit scanReportDirectoriesResolved(")),
             "ScanController should emit resolved report directories for targeted scans");
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

void ScanSettingsWiringTests::scan_controller_disables_unsolved_relocation_for_targeted_runs()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/controllers/scancontroller.cpp");
    QFile sourceFile(sourcePath);
    QVERIFY2(sourceFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(sourceFile.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("const bool targetedMode = !targetedInputs.isEmpty();")),
             "ScanController should detect targeted mode before dispatching work to ScanWorker");

    const qsizetype callStart = sourceText.indexOf(QStringLiteral("worker->doScan("));
    QVERIFY2(callStart >= 0, "ScanController should call ScanWorker::doScan()");
    const qsizetype callEnd = sourceText.indexOf(QStringLiteral(");"), callStart);
    QVERIFY2(callEnd > callStart, "ScanController should have a complete ScanWorker::doScan() call");
    const QString call = sourceText.mid(callStart, callEnd - callStart);
    QVERIFY2(call.contains(QStringLiteral("targetedMode")),
             "ScanController should pass targetedMode to ScanWorker::doScan()");
    QVERIFY2(call.contains(QStringLiteral("targetedInputs")),
             "ScanController should pass targeted inputs to ScanWorker::doScan()");
}

void ScanSettingsWiringTests::scan_worker_skips_unsolved_relocation_for_targeted_runs()
{
    const QString headerPath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/workers/scanworker.h");
    QFile headerFile(headerPath);
    QVERIFY2(headerFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(headerPath)));

    const QString headerText = QString::fromUtf8(headerFile.readAll());
    QVERIFY2(headerText.contains(QStringLiteral("bool targetedMode")),
             "ScanWorker::doScan should receive targetedMode so it can avoid moving targeted inputs");

    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/workers/scanworker.cpp");
    QFile sourceFile(sourcePath);
    QVERIFY2(sourceFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(sourceFile.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("request.move_unsolved_logs = moveUnsolvedLogs")),
              "ScanWorker should pass the unsolved relocation setting to Rust");
    QVERIFY2(sourceText.contains(QStringLiteral("request.unsolved_logs_destination = classic::toRustString(unsolvedLogsDestination)")),
             "ScanWorker should pass the destination setting to Rust without constructing the canonical path");
    QVERIFY2(sourceText.contains(QStringLiteral("request.targeted_mode = targetedMode")),
             "ScanWorker should pass targetedMode to Rust");
    const QRegularExpression scanRunCallRegex(QStringLiteral(
        R"(scan_run_execute\(\s*request,\s*progress_callback,\s*\*m_cancellationToken\s*\))"));
    QVERIFY2(scanRunCallRegex.match(sourceText).hasMatch(),
             "ScanWorker should pass the scan request and cancellation token to Rust");
    QVERIFY2(sourceText.contains(QStringLiteral("scan_cancellation_token_cancel(*m_cancellationToken)")),
             "ScanWorker::requestCancel should propagate cancellation to the Rust scan-run token");
    QVERIFY2(!sourceText.contains(QStringLiteral("move_unsolved_artifacts")),
             "ScanWorker should not own Unsolved Logs movement after scan_run migration");
}

void ScanSettingsWiringTests::scan_worker_counts_per_log_failures_without_scan_level_error()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/workers/scanworker.cpp");
    QFile sourceFile(sourcePath);
    QVERIFY2(sourceFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(sourceFile.readAll());
    const QRegularExpression resultLoopRegex(QStringLiteral(
        R"(for\s*\(\s*const\s+auto&\s+result\s*:\s*results\s*\)(?:.|\n)*?if\s*\(\s*result\.success\s*\)(?:.|\n)*?\+\+successCount;(?:.|\n)*?else(?:.|\n)*?\+\+errorCount;(?:.|\n)*?emit\s+logScanned\(resultIndex,\s*result\.success)"));
    QVERIFY2(resultLoopRegex.match(sourceText).hasMatch(),
             "ScanWorker should treat Rust scan_run per-log outcomes as per-log success/failure signals");

    const qsizetype outerCatchStart = sourceText.indexOf(QStringLiteral("} catch (const rust::Error& e) {"));
    QVERIFY2(outerCatchStart > 0, "ScanWorker should have an outer rust::Error handler for setup failures");
    const qsizetype outerCatchEnd = sourceText.indexOf(QStringLiteral("} catch (const std::exception& e)"),
                                                       outerCatchStart);
    const QString outerCatchBlock = sourceText.mid(outerCatchStart, outerCatchEnd - outerCatchStart);
    QVERIFY2(outerCatchBlock.contains(QStringLiteral("emit error(")),
             "ScanWorker should reserve scan-level error emission for setup failures outside per-log work");
    QVERIFY2(!outerCatchBlock.contains(QStringLiteral("logScanned")),
             "ScanWorker outer error handler should not masquerade as a completed per-log result");
    QVERIFY2(sourceText.contains(QStringLiteral("emit finished(total, successCount, errorCount);")),
             "ScanWorker should finish targeted scans with failed counts instead of aborting the whole scan");
}

QTEST_MAIN(ScanSettingsWiringTests)
#include "test_scan_settings_wiring.moc"
