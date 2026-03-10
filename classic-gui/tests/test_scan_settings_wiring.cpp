#include <QFile>
#include <QRegularExpression>
#include <QtTest/QtTest>

class ScanSettingsWiringTests : public QObject {
    Q_OBJECT

private slots:
    void scan_worker_forwards_runtime_flags_to_rust_config();
    void scan_controller_forwards_flags_to_worker();
    void mainwindow_forwards_scan_flags_to_controller();
    void mainwindow_forwards_game_version_to_scan_controller();
    void scan_worker_handles_move_unsolved_and_max_concurrent_settings();
    void scan_worker_uses_progress_enabled_batch_api();
    void scan_worker_forwards_batch_counts_in_progress_updates();
    void scan_worker_defaults_to_batch_for_multi_log_scans();
    void mainwindow_wires_live_crash_scan_progress_updates();
    void mainwindow_does_not_use_deprecated_vr_mode_setting();
    void mainwindow_blocks_game_files_scan_when_paths_unresolved();
    void mainwindow_blocks_crash_logs_scan_when_fcx_enabled_and_paths_unresolved();
    void mainwindow_uses_exe_relative_crash_logs_dir();
    void mainwindow_resets_stale_game_exe_path_outside_selected_root();
    void controllers_emit_global_scan_started_signal_on_scan_start();
    void scan_controller_uses_exe_dir_and_docs_fallback_for_log_collection();
    void settings_dialog_wires_game_folder_path_controls();
    void settings_dialog_resets_stale_game_exe_path_when_game_folder_changes();
};

void ScanSettingsWiringTests::scan_worker_forwards_runtime_flags_to_rust_config()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/workers/scanworker.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("build_full_scan_config(")),
             "ScanWorker should call build_full_scan_config()");
    QVERIFY2(sourceText.contains(QStringLiteral("classic::toRustString(gameVersion)")),
             "ScanWorker should forward gameVersion to build_full_scan_config()");
    QVERIFY2(sourceText.contains(QStringLiteral("showFormIdValues")),
             "ScanWorker should forward showFormIdValues to build_full_scan_config()");
    QVERIFY2(sourceText.contains(QStringLiteral("fcxMode")),
             "ScanWorker should forward fcxMode to build_full_scan_config()");
    QVERIFY2(sourceText.contains(QStringLiteral("simplifyLogs")),
             "ScanWorker should forward simplifyLogs to build_full_scan_config()");
}

void ScanSettingsWiringTests::scan_controller_forwards_flags_to_worker()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/controllers/scancontroller.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());

    const QRegularExpression lambdaRegex(QStringLiteral(
        R"(worker->doScan\((?:.|\n)*?gameVersion,\s*showFormIdValues,\s*fcxMode,\s*simplifyLogs,\s*moveUnsolvedLogs,\s*maxConcurrentScans\s*\))"));
    QVERIFY2(lambdaRegex.match(sourceText).hasMatch(),
             "ScanController should pass scan settings through to ScanWorker::doScan()");
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
        R"(m_scanController->startScan\((?:.|\n)*?m_gameVersion,\s*m_showFormIdValues,\s*m_fcxMode,\s*m_simplifyLogs,\s*m_moveUnsolvedLogs,\s*m_maxConcurrentScans\s*,(?:.|\n)*?\))"));
    QVERIFY2(callRegex.match(sourceText).hasMatch(),
             "MainWindow should forward game version and all scan settings to ScanController::startScan()");
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
    QVERIFY2(sourceText.contains(QStringLiteral("orchestrator_process_logs_batch_with_progress")),
             "ScanWorker should use the CXX batch API that reports progress");
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
    const QRegularExpression batchGateRegex(QStringLiteral(R"(if\s*\(\s*total\s*>\s*1\s*\))"));
    QVERIFY2(batchGateRegex.match(sourceText).hasMatch(),
             "ScanWorker should default to batch mode whenever there is more than one log");
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
        R"(if\s*\(m_fcxMode\)\s*\{(?:.|\n)*?loadValidatedGameAndDocsPaths\(&gamePath,\s*&docsPath\)(?:.|\n)*?FCX mode requires valid game and INI folder paths(?:.|\n)*?return;)"));
    QVERIFY2(
        guardRegex.match(body).hasMatch(),
        "MainWindow crash-log scan should gate FCX mode on validated paths inside onScanCrashLogs() and return early");
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
    QVERIFY2(body.contains(QStringLiteral("QFileInfo")),
             "MainWindow should inspect executable parent folder to detect stale game executable paths");
    QVERIFY2(body.contains(QStringLiteral("Qt::CaseInsensitive")),
             "MainWindow should compare executable and root paths case-insensitively on Windows");
    QVERIFY2(body.contains(QStringLiteral("gameExePath.clear()")),
             "MainWindow should clear stale executable paths outside the selected game root");
    QVERIFY2(body.contains(QStringLiteral("gameRoot + QStringLiteral(\"/Fallout4.exe\")")),
             "MainWindow should fall back to selected game root executable after stale path reset");
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

void ScanSettingsWiringTests::scan_controller_uses_exe_dir_and_docs_fallback_for_log_collection()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/controllers/scancontroller.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("Game_Info.Root_Folder_Docs")),
             "ScanController should fall back to Root_Folder_Docs when Docs_Folder_XSE is unavailable");
    QVERIFY2(sourceText.contains(QStringLiteral("filePath(QStringLiteral(\"F4SE\"))")),
             "ScanController should derive the F4SE folder from the docs root when needed");
    QVERIFY2(sourceText.contains(QStringLiteral("QCoreApplication::applicationDirPath()")),
             "ScanController should collect crash logs relative to the GUI executable directory");
    QVERIFY2(!sourceText.contains(QStringLiteral("QDir::currentPath()")),
             "ScanController should not use the current working directory for crash-log collection");
    QVERIFY2(sourceText.contains(QStringLiteral("classic::toRustString(customFolder)")),
             "ScanController should continue forwarding the custom scan folder separately");
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

    const QString body = extractFunctionBody(QStringLiteral("void SettingsDialog::saveSettings()"));
    QVERIFY2(!body.isEmpty(), "SettingsDialog::saveSettings() should exist");
    QVERIFY2(body.contains(QStringLiteral("QFileInfo")),
             "SettingsDialog should inspect existing game executable path location when saving");
    QVERIFY2(body.contains(QStringLiteral("QFile::exists")),
             "SettingsDialog should reset stale game executable paths when the stored executable no longer exists");
    QVERIFY2(body.contains(QStringLiteral("Qt::CaseInsensitive")),
             "SettingsDialog should compare executable parent and selected game folder case-insensitively");
}

QTEST_MAIN(ScanSettingsWiringTests)
#include "test_scan_settings_wiring.moc"
