#include <QFile>
#include <QRegularExpression>
#include <QtTest/QtTest>

class MainWindowGeometryTests : public QObject {
    Q_OBJECT

private slots:
    void main_tab_minimum_geometry_constant_matches_default_layout();
    /// GUI production code never constructs or writes raw first-party geometry paths.
    void gui_production_has_no_raw_user_settings_geometry_paths();
    void tab_bar_configuration_is_responsive_for_narrow_windows();
    void custom_folder_handlers_refresh_results_directories();
    void entering_results_tab_forces_report_reload();
    void crash_scan_status_bar_tracks_scan_statistics();
    void first_run_path_detection_treats_invalid_directories_as_unresolved();
    void first_run_bootstraps_and_updates_local_yaml();
    void manual_path_dialog_validates_before_accepting();
};

void MainWindowGeometryTests::main_tab_minimum_geometry_constant_matches_default_layout()
{
    const QString headerPath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.h");
    QFile file(headerPath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(headerPath)));

    const QString headerText = QString::fromUtf8(file.readAll());
    const QRegularExpression entryRegex(QStringLiteral(R"(\{\s*(\d+)\s*,\s*(\d+)\s*\},\s*//\s*Main Options)"));
    const QRegularExpressionMatch match = entryRegex.match(headerText);
    QVERIFY2(match.hasMatch(), "Main Options tab minimum geometry entry not found");

    QCOMPARE(match.captured(1).toInt(), 640);
    QCOMPARE(match.captured(2).toInt(), 500);
}

void MainWindowGeometryTests::gui_production_has_no_raw_user_settings_geometry_paths()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());
    QVERIFY2(!sourceText.contains(QStringLiteral("UI.window_geometry.")),
             "GUI production code must not construct raw first-party geometry paths");
    QVERIFY2(!sourceText.contains(QStringLiteral("yaml_ops_set_bool_setting")) &&
                 !sourceText.contains(QStringLiteral("yaml_ops_set_integer_setting")) &&
                 !sourceText.contains(QStringLiteral("yaml_ops_save_file")),
             "GUI production code must not mutate first-party User Settings through generic YAML operations");
}

void MainWindowGeometryTests::tab_bar_configuration_is_responsive_for_narrow_windows()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());

    QVERIFY2(sourceText.contains(QStringLiteral("setElideMode(Qt::ElideRight)")),
             "Expected tab bar elide mode configuration was not found");
    QVERIFY2(sourceText.contains(QStringLiteral("setExpanding(true)")),
             "Expected tab bar expanding configuration was not found");
}

void MainWindowGeometryTests::custom_folder_handlers_refresh_results_directories()
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

    const QString browseBody = extractFunctionBody(QStringLiteral("onBrowseCustom()"));
    QVERIFY2(!browseBody.isEmpty(), "Could not locate MainWindow::onBrowseCustom()");
    QVERIFY2(browseBody.contains(QStringLiteral("initResultsReportDir();")),
             "onBrowseCustom should refresh Results report directories after updating custom path");

    const QString editedBody = extractFunctionBody(QStringLiteral("onCustomFolderEdited()"));
    QVERIFY2(!editedBody.isEmpty(), "Could not locate MainWindow::onCustomFolderEdited()");
    QVERIFY2(editedBody.contains(QStringLiteral("initResultsReportDir();")),
             "onCustomFolderEdited should refresh Results report directories after updating custom path");
}

void MainWindowGeometryTests::entering_results_tab_forces_report_reload()
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

    const QString body = extractFunctionBody(QStringLiteral("onTabChanged(int index)"));
    QVERIFY2(!body.isEmpty(), "Could not locate MainWindow::onTabChanged(int index)");
    QVERIFY2(body.contains(QStringLiteral("index == (TAB_COUNT - 1)")),
             "onTabChanged should gate forced refresh on the Results tab index");
    QVERIFY2(body.contains(QStringLiteral("m_resultsController->refreshReports();")),
             "onTabChanged should force a Results report reload when entering the Results tab");
}

void MainWindowGeometryTests::crash_scan_status_bar_tracks_scan_statistics()
{
    const QString headerPath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.h");
    QFile headerFile(headerPath);
    QVERIFY2(headerFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(headerPath)));

    const QString headerText = QString::fromUtf8(headerFile.readAll());
    QVERIFY2(headerText.contains(QStringLiteral("QElapsedTimer m_crashScanTimer")),
             "MainWindow should keep a crash-scan elapsed timer for status updates");
    QVERIFY2(headerText.contains(QStringLiteral("int m_crashScanLogsCompleted")),
             "MainWindow should track completed crash-log count for status updates");
    QVERIFY2(headerText.contains(QStringLiteral("int m_crashScanTotalLogs")),
             "MainWindow should track total crash-log count for status updates");

    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile sourceFile(sourcePath);
    QVERIFY2(sourceFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(sourceFile.readAll());
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

    const QString crashScanProgressBody = extractFunctionBody(
        QStringLiteral("onCrashScanProgress(float percent, const QString& status, int completed, int total)"));
    QVERIFY2(!crashScanProgressBody.isEmpty(), "Could not locate MainWindow::onCrashScanProgress(float percent, const "
                                               "QString& status, int completed, int total)");

    const QString scanProgressBody =
        extractFunctionBody(QStringLiteral("onScanProgress(float percent, const QString& status)"));
    QVERIFY2(!scanProgressBody.isEmpty(),
             "Could not locate MainWindow::onScanProgress(float percent, const QString& status)");

    QVERIFY2(sourceText.contains(QStringLiteral("logs scanned")),
             "Crash scan status text should include scanned-log statistics");
    QVERIFY2(sourceText.contains(QStringLiteral("elapsed")),
             "Crash scan status text should include elapsed time statistics");
    QVERIFY2(sourceText.contains(QStringLiteral("onCrashScanProgress")),
             "Crash scan status should update scanned-log stats during live progress events");
    QVERIFY2(sourceText.contains(QStringLiteral("completed, int total")),
             "Crash scan progress updates should carry structured completed and total counts");
    QVERIFY2(crashScanProgressBody.contains(
                 QStringLiteral("m_crashScanLogsCompleted = qMax(m_crashScanLogsCompleted, qMin(completed, total));")),
             "Crash scan progress updates should keep completed-log counts monotonic when total is known");
    QVERIFY2(crashScanProgressBody.contains(
                 QStringLiteral("m_crashScanLogsCompleted = qMax(m_crashScanLogsCompleted, completed);")),
             "Crash scan progress updates should keep completed-log counts monotonic when total is unknown");
    QVERIFY2(scanProgressBody.contains(QStringLiteral("m_crashScanLogsCompleted")),
             "Crash scan status formatting should read tracked completed-log counts");
    QVERIFY2(!crashScanProgressBody.contains(QStringLiteral("progressCompletedEstimate")),
             "Crash scan progress handling should not infer completed-log counts from percent progress");
}

void MainWindowGeometryTests::first_run_path_detection_treats_invalid_directories_as_unresolved()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile sourceFile(sourcePath);
    QVERIFY2(sourceFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(sourceFile.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("QDir(gamePath).exists()")),
             "First-run path detection should treat non-existing game directories as unresolved");
    QVERIFY2(sourceText.contains(QStringLiteral("QDir(docsPath).exists()")),
             "First-run path detection should treat non-existing docs directories as unresolved");
}

void MainWindowGeometryTests::first_run_bootstraps_and_updates_local_yaml()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile sourceFile(sourcePath);
    QVERIFY2(sourceFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(sourceFile.readAll());
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

    QVERIFY2(sourceText.contains(QStringLiteral("classic::config::save_local_yaml_paths")),
             "Local YAML sync should delegate file creation and persistence to the Rust config bridge");

    const QString firstRunBody = extractFunctionBody(QStringLiteral("checkFirstRunPaths()"));
    QVERIFY2(!firstRunBody.isEmpty(), "Could not locate MainWindow::checkFirstRunPaths()");

    const qsizetype intakeRun = firstRunBody.indexOf(QStringLiteral("GameSetupUserSettings::runIntake"));
    const qsizetype acceptedCommit = firstRunBody.indexOf(QStringLiteral("commitSelectedPaths"));
    const qsizetype firstLocalYamlSync = firstRunBody.indexOf(QStringLiteral("saveLocalYamlPaths"));

    QVERIFY2(firstLocalYamlSync >= 0,
             "First-run path detection should persist the Fallout 4 Local YAML after successful path resolution");
    QVERIFY2(intakeRun >= 0 && acceptedCommit > intakeRun && firstLocalYamlSync > acceptedCommit,
             "First-run setup should run typed intake and commit accepted paths before syncing Local YAML");
    QVERIFY2(firstRunBody.contains(QStringLiteral("if (choice != QMessageBox::Yes)")),
             "Rejecting detected paths should return before either User Settings or Local YAML is written");
    QVERIFY2(firstRunBody.contains(QStringLiteral("if (hasAcceptedChanges)")) &&
                 firstRunBody.contains(QStringLiteral("if (!commitChanges(changes))")),
             "Accepted detected and manual paths should enter one final atomic commit");
    QVERIFY2(firstRunBody.contains(QStringLiteral("m_guiSettings = classic::gui::GuiUserSettings::open(m_dataRoot)")),
             "A successful startup-path commit should refresh the same-session GUI snapshot");
    QVERIFY2(!firstRunBody.contains(QStringLiteral("CLASSIC_Settings.")),
             "First-run setup should not interpret raw User Settings keys");
}

void MainWindowGeometryTests::manual_path_dialog_validates_before_accepting()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/pathdialog.cpp");
    QFile sourceFile(sourcePath);
    QVERIFY2(sourceFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(sourceFile.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("validateAndAccept")),
             "ManualPathDialog should route OK through validation before accepting");
    QVERIFY2(sourceText.contains(QStringLiteral("check_restricted_path")),
             "ManualPathDialog should reject restricted game paths");
    QVERIFY2(sourceText.contains(QStringLiteral("QMessageBox::warning")),
             "ManualPathDialog should show validation feedback when path checks fail");
}

QTEST_MAIN(MainWindowGeometryTests)
#include "test_mainwindow_geometry.moc"
