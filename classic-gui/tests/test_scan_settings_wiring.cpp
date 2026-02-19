#include <QFile>
#include <QRegularExpression>
#include <QtTest/QtTest>

class ScanSettingsWiringTests : public QObject {
    Q_OBJECT

private slots:
    void scan_worker_forwards_runtime_flags_to_rust_config();
    void scan_controller_forwards_flags_to_worker();
    void mainwindow_forwards_scan_flags_to_controller();
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
            R"(worker->doScan\((?:.|\n)*?vrMode,\s*showFormIdValues,\s*fcxMode,\s*simplifyLogs\s*\))"));
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

QTEST_MAIN(ScanSettingsWiringTests)
#include "test_scan_settings_wiring.moc"
