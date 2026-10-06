#include <QDir>
#include <QFile>
#include <QRegularExpression>
#include <QSignalSpy>
#include <QTemporaryDir>
#include <QtTest/QtTest>

#include "workers/scanworker.h"

/// Behaviour of `ScanWorker` launching real runs through Crash Log Scan Launch.
///
/// What a launch builds is Rust's and is pinned by the `crash-log-scan-launch` conformance family
/// and the GUI's `gui.scan-launch` consumer obligation. These cases cover only what the worker does
/// with it: where a button-press scan looks, that FCX Mode never refuses before the run, and that
/// launch diagnostics reach the user.
class ScanWorkerLaunchTests : public QObject {
    Q_OBJECT

private slots:
    /// Verifies a Standard scan finds Crash Logs under the Installation Root, not the executable folder.
    void standard_scan_discovers_crash_logs_under_the_installation_root();
    /// Verifies FCX Mode with missing saved folders runs and carries a Crash Log Scan Setup Result.
    void fcx_scan_with_missing_setup_folders_runs_and_reports_the_setup_result();
    /// Verifies launch diagnostics are published as a warning while the run goes ahead.
    void launch_diagnostics_are_published_as_a_warning();

private:
    /// Stages YAML Data and one Crash Log in `<root>/Crash Logs`, returning false on any I/O failure.
    static bool stageInstallation(const QTemporaryDir& root);
    /// Writes `document` as the root's User Settings, returning false on any I/O failure.
    static bool writeSettings(const QTemporaryDir& root, const QByteArray& document);
    /// Returns the saved-settings line naming `path` as the documents folder.
    static QByteArray documentsFolderLine(const QString& path);
};

bool ScanWorkerLaunchTests::stageInstallation(const QTemporaryDir& root)
{
    const QDir fixture(QStringLiteral(QT_TESTCASE_SOURCEDIR "/../../tests/fixtures/crash_log_scan_run"));
    const QString databases = root.filePath(QStringLiteral("CLASSIC Data/databases"));
    const QString crashLogs = root.filePath(QStringLiteral("Crash Logs"));
    return QDir().mkpath(databases) && QDir().mkpath(crashLogs) &&
           QFile::copy(fixture.filePath(QStringLiteral("CLASSIC Data/databases/CLASSIC Main.yaml")),
                       QDir(databases).filePath(QStringLiteral("CLASSIC Main.yaml"))) &&
           QFile::copy(fixture.filePath(QStringLiteral("CLASSIC Data/databases/CLASSIC Fallout4.yaml")),
                       QDir(databases).filePath(QStringLiteral("CLASSIC Fallout4.yaml"))) &&
           QFile::copy(fixture.filePath(QStringLiteral("valid-crash.log")),
                       QDir(crashLogs).filePath(QStringLiteral("crash-launch.log")));
}

bool ScanWorkerLaunchTests::writeSettings(const QTemporaryDir& root, const QByteArray& document)
{
    QFile file(root.filePath(QStringLiteral("CLASSIC Settings.yaml")));
    return file.open(QIODevice::WriteOnly | QIODevice::Truncate) && file.write(document) == document.size();
}

QByteArray ScanWorkerLaunchTests::documentsFolderLine(const QString& path)
{
    return QByteArray("  Documents Folder Path: '") + path.toUtf8() + QByteArray("'\n");
}

void ScanWorkerLaunchTests::standard_scan_discovers_crash_logs_under_the_installation_root()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    QVERIFY(stageInstallation(root));
    // Without a saved documents folder, Standard discovery would also collect this machine's real
    // XSE crash logs; an empty one keeps the run to the Crash Log staged here.
    const QString documents = root.filePath(QStringLiteral("Documents"));
    QVERIFY(QDir().mkpath(documents));
    QVERIFY(writeSettings(root, QByteArray("schema_version: \"1.0\"\nCLASSIC_Settings:\n  Managed Game: Fallout 4\n") +
                                    documentsFolderLine(documents)));

    ScanWorker worker;
    QSignalSpy discoverySpy(&worker, &ScanWorker::discoveryCompleted);
    QSignalSpy finishedSpy(&worker, &ScanWorker::finished);
    QSignalSpy errorSpy(&worker, &ScanWorker::error);

    worker.doScan(root.path(), {});

    QCOMPARE(errorSpy.count(), 0);
    QCOMPARE(discoverySpy.count(), 1);
    QCOMPARE(discoverySpy.at(0).at(0).toInt(), 1);
    const QStringList reportDirectories = discoverySpy.at(0).at(2).toStringList();
    QCOMPARE(reportDirectories.size(), 1);
    QCOMPARE(QDir::cleanPath(reportDirectories.at(0)).toLower(),
             QDir::cleanPath(root.filePath(QStringLiteral("Crash Logs"))).toLower());
    QCOMPARE(finishedSpy.count(), 1);
}

void ScanWorkerLaunchTests::fcx_scan_with_missing_setup_folders_runs_and_reports_the_setup_result()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    QVERIFY(stageInstallation(root));
    // Both saved folders are absent. The GUI used to refuse to start here; now the scan runs and
    // Rust's FCX setup validation reports on them in the run's Crash Log Scan Setup Result.
    const QByteArray settings = QByteArray("schema_version: \"1.0\"\n"
                                           "CLASSIC_Settings:\n"
                                           "  Managed Game: Fallout 4\n"
                                           "  FCX Mode: true\n"
                                           "  Game Folder Path: '") +
                                root.filePath(QStringLiteral("Missing Game")).toUtf8() + QByteArray("'\n") +
                                documentsFolderLine(root.filePath(QStringLiteral("Missing Documents")));
    QVERIFY(writeSettings(root, settings));

    ScanWorker worker;
    QSignalSpy discoverySpy(&worker, &ScanWorker::discoveryCompleted);
    QSignalSpy errorSpy(&worker, &ScanWorker::error);
    QSignalSpy finishedSpy(&worker, &ScanWorker::finished);
    // The worker logs every run's Crash Log Scan Setup Result. Requiring that line proves the run
    // carried one, whatever it concluded: setup validation may still find the game through
    // platform discovery on a machine that has it installed, so whether it ends `SetupFailed`
    // (shown in the error dialog, setup block included) or completes depends on the machine.
    QTest::ignoreMessage(QtInfoMsg, QRegularExpression(QStringLiteral("^FCX setup: ")));

    worker.doScan(root.path(), {});

    QCOMPARE(discoverySpy.count(), 1);
    QCOMPARE(finishedSpy.count() + errorSpy.count(), 1);
    if (errorSpy.count() == 1) {
        QVERIFY2(errorSpy.at(0).at(0).toString().contains(QStringLiteral("FCX setup:")),
                 qPrintable(errorSpy.at(0).at(0).toString()));
    }
}

void ScanWorkerLaunchTests::launch_diagnostics_are_published_as_a_warning()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    QVERIFY(stageInstallation(root));
    QVERIFY(writeSettings(root, QByteArray("schema_version: \"1.0\"\nCLASSIC_Settings:\n  Broken: [one, two\n")));

    ScanWorker worker;
    QSignalSpy warningSpy(&worker, &ScanWorker::launchWarning);
    QSignalSpy finishedSpy(&worker, &ScanWorker::finished);

    // Targeted, so the run touches only the staged Crash Log and never this machine's own.
    worker.doScan(root.path(), {root.filePath(QStringLiteral("Crash Logs/crash-launch.log"))});

    QCOMPARE(warningSpy.count(), 1);
    QVERIFY(!warningSpy.at(0).at(0).toString().isEmpty());
    // A degraded document still launches from defaults, so the run itself goes ahead.
    QCOMPARE(finishedSpy.count(), 1);
}

QTEST_MAIN(ScanWorkerLaunchTests)
#include "test_scanworker_launch.moc"
