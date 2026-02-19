#include <QFile>
#include <QRegularExpression>
#include <QtTest/QtTest>

class ScanSettingsWiringTests : public QObject {
    Q_OBJECT

private slots:
    void scan_worker_forwards_runtime_flags_to_rust_config();
    void scan_controller_forwards_flags_to_worker();
    void mainwindow_forwards_scan_flags_to_controller();
    void mainwindow_forwards_vr_mode_to_scan_controller();
    void scan_worker_handles_move_unsolved_and_max_concurrent_settings();
    void scan_worker_uses_progress_enabled_batch_api();
    void scan_worker_defaults_to_batch_for_multi_log_scans();
    void mainwindow_does_not_use_deprecated_vr_mode_setting();
};

void ScanSettingsWiringTests::scan_worker_forwards_runtime_flags_to_rust_config()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/workers/scanworker.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());

    const QRegularExpression callRegex(
        QStringLiteral(
            R"(build_full_scan_config\((?:.|\n)*?vrMode,\s*showFormIdValues,\s*fcxMode,\s*simplifyLogs\s*\))"));
    QVERIFY2(callRegex.match(sourceText).hasMatch(),
             "ScanWorker should forward scan flags to build_full_scan_config()");
}

void ScanSettingsWiringTests::scan_controller_forwards_flags_to_worker()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/controllers/scancontroller.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());

    const QRegularExpression lambdaRegex(
        QStringLiteral(
            R"(worker->doScan\((?:.|\n)*?vrMode,\s*showFormIdValues,\s*fcxMode,\s*simplifyLogs,\s*moveUnsolvedLogs,\s*maxConcurrentScans\s*\))"));
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

    const QRegularExpression callRegex(
        QStringLiteral(
            R"(m_scanController->startScan\((?:.|\n)*?m_showFormIdValues,\s*m_fcxMode,\s*m_simplifyLogs\s*,(?:.|\n)*?\))"));
    QVERIFY2(callRegex.match(sourceText).hasMatch(),
             "MainWindow should forward loaded scan settings to ScanController::startScan()");
}

void ScanSettingsWiringTests::mainwindow_forwards_vr_mode_to_scan_controller()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());

    const QRegularExpression callRegex(
        QStringLiteral(
            R"(m_scanController->startScan\((?:.|\n)*?m_scanVrMode,\s*m_showFormIdValues,\s*m_fcxMode,\s*m_simplifyLogs,\s*m_moveUnsolvedLogs,\s*m_maxConcurrentScans\s*,(?:.|\n)*?\))"));
    QVERIFY2(callRegex.match(sourceText).hasMatch(),
             "MainWindow should forward VR mode and all scan settings to ScanController::startScan()");
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
    QVERIFY2(sourceText.contains(QStringLiteral("orchestrator_process_logs_batch_with_progress")),
             "ScanWorker should use the CXX batch API that reports progress");
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

QTEST_MAIN(ScanSettingsWiringTests)
#include "test_scan_settings_wiring.moc"
