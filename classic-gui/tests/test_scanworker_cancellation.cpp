#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QSignalSpy>
#include <QTemporaryDir>
#include <QtTest/QtTest>

#include <optional>
#include <stdexcept>

#include "workers/scanworker.h"

class ScanWorkerCancellationTests : public QObject {
    Q_OBJECT

private slots:
    void requestCancel_before_scan_does_not_crash();
    void requestCancel_is_idempotent();
    void requestCancel_alone_emits_no_signals();
    void requestCancel_before_execution_reaches_the_rust_lifecycle();
    void completed_run_publishes_installed_yaml_data_beyond_terminal_projection();
    /// Supplies all explicit GUI recovery choices and their expected terminal Local Ignore states.
    void malformed_local_ignore_recovery_resumes_or_cancels_retained_scan_run_data();
    /// Verifies every GUI choice consumes the retained continuation with the promised mutation semantics.
    void malformed_local_ignore_recovery_resumes_or_cancels_retained_scan_run();
    /// Verifies a worker with no configured prompt reports the invariant instead of choosing for the user.
    void recovery_without_a_configured_prompt_reports_the_invariant_without_mutating();
    /// Verifies a prompt that throws cannot leave the run resumable or mutate Local Ignore.
    void a_throwing_prompt_fails_the_run_without_mutating();

private:
    /// Builds an installation root whose Local Ignore YAML Data is malformed, returning its path.
    QString buildMalformedIgnoreRoot(const QTemporaryDir& root, const QByteArray& malformedIgnore,
                                     QString* crashLogOut) const;
};

QString ScanWorkerCancellationTests::buildMalformedIgnoreRoot(const QTemporaryDir& root,
                                                              const QByteArray& malformedIgnore,
                                                              QString* crashLogOut) const
{
    const QDir fixture(QStringLiteral(QT_TESTCASE_SOURCEDIR "/../../tests/fixtures/crash_log_scan_run"));
    const QString databases = root.filePath(QStringLiteral("CLASSIC Data/databases"));
    if (!QDir().mkpath(databases)) {
        return {};
    }
    if (!QFile::copy(fixture.filePath(QStringLiteral("CLASSIC Data/databases/CLASSIC Main.yaml")),
                     QDir(databases).filePath(QStringLiteral("CLASSIC Main.yaml"))) ||
        !QFile::copy(fixture.filePath(QStringLiteral("CLASSIC Data/databases/CLASSIC Fallout4.yaml")),
                     QDir(databases).filePath(QStringLiteral("CLASSIC Fallout4.yaml")))) {
        return {};
    }

    const QString ignorePath = root.filePath(QStringLiteral("CLASSIC Data/CLASSIC Ignore.yaml"));
    QFile ignoreFile(ignorePath);
    if (!ignoreFile.open(QIODevice::WriteOnly | QIODevice::Truncate) ||
        ignoreFile.write(malformedIgnore) != static_cast<qint64>(malformedIgnore.size())) {
        return {};
    }
    ignoreFile.close();

    if (crashLogOut != nullptr) {
        *crashLogOut = root.filePath(QStringLiteral("crash-worker-guard.log"));
        if (!QFile::copy(fixture.filePath(QStringLiteral("valid-crash.log")), *crashLogOut)) {
            return {};
        }
    }
    return ignorePath;
}

void ScanWorkerCancellationTests::requestCancel_before_scan_does_not_crash()
{
    ScanWorker worker;
    worker.requestCancel();
    // Reaching here without crash/assert is the pass condition.
    QVERIFY(true);
}

void ScanWorkerCancellationTests::requestCancel_is_idempotent()
{
    ScanWorker worker;
    worker.requestCancel();
    worker.requestCancel();
    worker.requestCancel();
    QVERIFY(true);
}

void ScanWorkerCancellationTests::requestCancel_alone_emits_no_signals()
{
    ScanWorker worker;
    QSignalSpy errorSpy(&worker, &ScanWorker::error);
    QSignalSpy finishedSpy(&worker, &ScanWorker::finished);

    worker.requestCancel();

    // requestCancel() only records cancellation; signals are emitted by doScan().
    QCOMPARE(errorSpy.count(), 0);
    QCOMPARE(finishedSpy.count(), 0);
}

void ScanWorkerCancellationTests::requestCancel_before_execution_reaches_the_rust_lifecycle()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    const QString crashLog = root.filePath(QStringLiteral("crash-prestart.log"));
    QFile file(crashLog);
    QVERIFY(file.open(QIODevice::WriteOnly));
    file.write("cancel before discovery");
    file.close();

    classic::gui::CrashLogScanLaunchSettings settings;
    settings.game = QStringLiteral("Fallout4");
    settings.gameVersion = QStringLiteral("auto");

    ScanWorker worker;
    QSignalSpy cancelledSpy(&worker, &ScanWorker::cancelled);
    QSignalSpy errorSpy(&worker, &ScanWorker::error);
    QSignalSpy finishedSpy(&worker, &ScanWorker::finished);
    worker.requestCancel();

    worker.doScan(root.path(), settings, root.path(), {}, {crashLog});

    QCOMPARE(cancelledSpy.count(), 1);
    QVERIFY(cancelledSpy.at(0).at(0).toString().contains(QStringLiteral("before discovery")));
    QCOMPARE(errorSpy.count(), 0);
    QCOMPARE(finishedSpy.count(), 0);
}

void ScanWorkerCancellationTests::completed_run_publishes_installed_yaml_data_beyond_terminal_projection()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());

    const QDir fixture(QStringLiteral(QT_TESTCASE_SOURCEDIR "/../../tests/fixtures/crash_log_scan_run"));
    const QString databases = root.filePath(QStringLiteral("CLASSIC Data/databases"));
    QVERIFY(QDir().mkpath(databases));
    QVERIFY(QFile::copy(fixture.filePath(QStringLiteral("CLASSIC Data/databases/CLASSIC Main.yaml")),
                        QDir(databases).filePath(QStringLiteral("CLASSIC Main.yaml"))));
    QVERIFY(QFile::copy(fixture.filePath(QStringLiteral("CLASSIC Data/databases/CLASSIC Fallout4.yaml")),
                        QDir(databases).filePath(QStringLiteral("CLASSIC Fallout4.yaml"))));
    QVERIFY(QFile::copy(fixture.filePath(QStringLiteral("CLASSIC Data/CLASSIC Ignore.yaml")),
                        root.filePath(QStringLiteral("CLASSIC Data/CLASSIC Ignore.yaml"))));
    const QString crashLog = root.filePath(QStringLiteral("crash-worker-propagation.log"));
    QVERIFY(QFile::copy(fixture.filePath(QStringLiteral("valid-crash.log")), crashLog));

    classic::gui::CrashLogScanLaunchSettings settings;
    settings.game = QStringLiteral("Fallout4");
    settings.gameVersion = QStringLiteral("auto");

    ScanWorker worker;
    std::optional<classic::gui::ScanRunInstalledYamlDataPresentation> published;
    connect(
        &worker, &ScanWorker::installedYamlDataResolved, this,
        [&published](const classic::gui::ScanRunInstalledYamlDataPresentation& installed) { published = installed; });

    worker.doScan(root.path(), settings, root.path(), {}, {crashLog});

    QVERIFY(published.has_value());
    QCOMPARE(published->main.role, classic::scanner::ScanRunInstalledYamlDataRole::Main);
    QCOMPARE(published->gameFile.role, classic::scanner::ScanRunInstalledYamlDataRole::Game);
    QCOMPARE(published->localIgnoreState, classic::scanner::ScanRunLocalIgnoreYamlDataState::Existing);
    QVERIFY(!published->main.sha256.isEmpty());
    QVERIFY(!published->gameFile.sha256.isEmpty());
    QVERIFY(!published->localIgnoreIdentity.sha256.isEmpty());
}

void ScanWorkerCancellationTests::malformed_local_ignore_recovery_resumes_or_cancels_retained_scan_run_data()
{
    using Choice = classic::gui::ScanRunLocalIgnoreRecoveryChoice;
    using State = classic::scanner::ScanRunLocalIgnoreYamlDataState;
    QTest::addColumn<int>("choiceValue");
    QTest::addColumn<int>("expectedStateValue");
    QTest::addColumn<bool>("expectsFinished");
    QTest::addColumn<bool>("expectsCancelled");
    QTest::addColumn<bool>("expectsReset");

    QTest::newRow("reset-to-default") << static_cast<int>(Choice::ResetToDefault)
                                       << static_cast<int>(State::ResetToDefault) << true << false << true;
    QTest::newRow("proceed-without-ignore") << static_cast<int>(Choice::ProceedWithoutIgnore)
                                             << static_cast<int>(State::ProceedWithoutIgnore) << true << false
                                             << false;
    QTest::newRow("cancel") << static_cast<int>(Choice::Cancel) << static_cast<int>(State::RecoveryRequired) << false
                             << true << false;
}

void ScanWorkerCancellationTests::malformed_local_ignore_recovery_resumes_or_cancels_retained_scan_run()
{
    QFETCH(int, choiceValue);
    QFETCH(int, expectedStateValue);
    QFETCH(bool, expectsFinished);
    QFETCH(bool, expectsCancelled);
    QFETCH(bool, expectsReset);

    QTemporaryDir root;
    QVERIFY(root.isValid());

    const QDir fixture(QStringLiteral(QT_TESTCASE_SOURCEDIR "/../../tests/fixtures/crash_log_scan_run"));
    const QString databases = root.filePath(QStringLiteral("CLASSIC Data/databases"));
    QVERIFY(QDir().mkpath(databases));
    QVERIFY(QFile::copy(fixture.filePath(QStringLiteral("CLASSIC Data/databases/CLASSIC Main.yaml")),
                        QDir(databases).filePath(QStringLiteral("CLASSIC Main.yaml"))));
    QVERIFY(QFile::copy(fixture.filePath(QStringLiteral("CLASSIC Data/databases/CLASSIC Fallout4.yaml")),
                        QDir(databases).filePath(QStringLiteral("CLASSIC Fallout4.yaml"))));
    const QByteArray malformedIgnore("CLASSIC_Ignore_Fallout4: [unterminated");
    const QString ignorePath = root.filePath(QStringLiteral("CLASSIC Data/CLASSIC Ignore.yaml"));
    QFile ignoreFile(ignorePath);
    QVERIFY(ignoreFile.open(QIODevice::WriteOnly | QIODevice::Truncate));
    QCOMPARE(ignoreFile.write(malformedIgnore), static_cast<qint64>(malformedIgnore.size()));
    ignoreFile.close();
    const QString crashLog = root.filePath(QStringLiteral("crash-worker-recovery.log"));
    QVERIFY(QFile::copy(fixture.filePath(QStringLiteral("valid-crash.log")), crashLog));

    classic::gui::CrashLogScanLaunchSettings settings;
    settings.game = QStringLiteral("Fallout4");
    settings.gameVersion = QStringLiteral("auto");

    bool promptCalled = false;
    bool offeredReset = false;
    ScanWorker worker([&promptCalled, &offeredReset, choiceValue](const QString&, bool resetAvailable) {
        promptCalled = true;
        offeredReset = resetAvailable;
        return static_cast<classic::gui::ScanRunLocalIgnoreRecoveryChoice>(choiceValue);
    });
    QSignalSpy errorSpy(&worker, &ScanWorker::error);
    QSignalSpy finishedSpy(&worker, &ScanWorker::finished);
    QSignalSpy cancelledSpy(&worker, &ScanWorker::cancelled);
    QSignalSpy logSpy(&worker, &ScanWorker::logScanned);
    QVector<classic::gui::ScanRunInstalledYamlDataPresentation> published;
    connect(&worker, &ScanWorker::installedYamlDataResolved, this,
            [&published](const classic::gui::ScanRunInstalledYamlDataPresentation& installed) {
                published.append(installed);
            });

    worker.doScan(root.path(), settings, root.path(), {}, {crashLog});

    QVERIFY(promptCalled);
    // This fixture's Main YAML Data does retain a usable default, and the reset case below actually
    // performs one, so the run really can honor Reset To Default. Asserting it here is what proves
    // the availability fact survives Rust, the bridge DTO, and the Qt projection in a real run —
    // rather than the worker withholding a decision that would have worked.
    QVERIFY(offeredReset);
    QCOMPARE(errorSpy.count(), 0);
    QCOMPARE(cancelledSpy.count(), expectsCancelled ? 1 : 0);
    QCOMPARE(finishedSpy.count(), expectsFinished ? 1 : 0);
    QCOMPARE(logSpy.count(), expectsFinished ? 1 : 0);
    QVERIFY(published.size() >= (expectsFinished ? 2 : 1));
    QCOMPARE(published.first().localIgnoreState,
             classic::scanner::ScanRunLocalIgnoreYamlDataState::RecoveryRequired);
    QVERIFY(published.first().localIgnoreResetAvailable);
    const auto& resumed = published.last();
    QCOMPARE(static_cast<int>(resumed.localIgnoreState), expectedStateValue);
    QFile repairedFile(ignorePath);
    QVERIFY(repairedFile.open(QIODevice::ReadOnly));
    const QByteArray authoritativeIgnore = repairedFile.readAll();

    // The run-level warning must not restate a Local Ignore problem the user just answered in the
    // recovery dialog. A reset still warns, because its durable backup location is new information.
    const QString warning = classic::gui::formatInstalledYamlDataWarning(resumed);
    if (expectsFinished && !expectsReset) {
        QVERIFY2(warning.isEmpty(),
                 qPrintable(QStringLiteral("Proceed Without Ignore should not re-warn, got: %1").arg(warning)));
    }
    if (expectsReset) {
        // A reset still warns, because the durable backup location is information the dialog could
        // not have given, but it must not restate the parse failure the user already answered.
        QVERIFY(!warning.isEmpty());
        QVERIFY(warning.contains(resumed.localIgnoreReset.backupPath));
        QVERIFY2(!warning.contains(QStringLiteral("could not be parsed")),
                 qPrintable(QStringLiteral("reset should not restate the answered parse failure, got: %1")
                                .arg(warning)));
    }

    if (expectsReset) {
        QVERIFY(resumed.hasLocalIgnoreReset);
        QVERIFY(QFileInfo::exists(resumed.localIgnoreReset.backupPath));
        QFile backupFile(resumed.localIgnoreReset.backupPath);
        QVERIFY(backupFile.open(QIODevice::ReadOnly));
        QCOMPARE(backupFile.readAll(), malformedIgnore);
        QVERIFY(authoritativeIgnore != malformedIgnore);
    } else {
        QVERIFY(!resumed.hasLocalIgnoreReset);
        QCOMPARE(authoritativeIgnore, malformedIgnore);
        const QDir backupDirectory(
            root.filePath(QStringLiteral("CLASSIC Backup/YAML Data/Local Ignore")));
        QVERIFY(!backupDirectory.exists() ||
                backupDirectory.entryList(QDir::Files | QDir::NoDotAndDotDot).isEmpty());
    }
}

void ScanWorkerCancellationTests::recovery_without_a_configured_prompt_reports_the_invariant_without_mutating()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    const QByteArray malformedIgnore("CLASSIC_Ignore_Fallout4: [unterminated");
    QString crashLog;
    const QString ignorePath = buildMalformedIgnoreRoot(root, malformedIgnore, &crashLog);
    QVERIFY(!ignorePath.isEmpty());

    classic::gui::CrashLogScanLaunchSettings settings;
    settings.game = QStringLiteral("Fallout4");
    settings.gameVersion = QStringLiteral("auto");

    // The default-constructed worker has no prompt, which is what a non-interactive caller looks
    // like. It must refuse to decide rather than silently proceeding or resetting.
    ScanWorker worker;
    QSignalSpy errorSpy(&worker, &ScanWorker::error);
    QSignalSpy finishedSpy(&worker, &ScanWorker::finished);
    QSignalSpy cancelledSpy(&worker, &ScanWorker::cancelled);

    worker.doScan(root.path(), settings, root.path(), {}, {crashLog});

    QCOMPARE(errorSpy.count(), 1);
    QVERIFY(errorSpy.at(0).at(0).toString().contains(QStringLiteral("recovery prompt")));
    QCOMPARE(finishedSpy.count(), 0);
    QCOMPARE(cancelledSpy.count(), 0);

    QFile ignoreFile(ignorePath);
    QVERIFY(ignoreFile.open(QIODevice::ReadOnly));
    QCOMPARE(ignoreFile.readAll(), malformedIgnore);
    const QDir backupDirectory(root.filePath(QStringLiteral("CLASSIC Backup/YAML Data/Local Ignore")));
    QVERIFY(!backupDirectory.exists() || backupDirectory.entryList(QDir::Files | QDir::NoDotAndDotDot).isEmpty());
}

void ScanWorkerCancellationTests::a_throwing_prompt_fails_the_run_without_mutating()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    const QByteArray malformedIgnore("CLASSIC_Ignore_Fallout4: [unterminated");
    QString crashLog;
    const QString ignorePath = buildMalformedIgnoreRoot(root, malformedIgnore, &crashLog);
    QVERIFY(!ignorePath.isEmpty());

    classic::gui::CrashLogScanLaunchSettings settings;
    settings.game = QStringLiteral("Fallout4");
    settings.gameVersion = QStringLiteral("auto");

    // The worker takes the continuation before asking, so an exception from the prompt drops it and
    // the run can never be resumed with an answer the user never gave.
    ScanWorker worker([](const QString&, bool) -> classic::gui::ScanRunLocalIgnoreRecoveryChoice {
        throw std::runtime_error("recovery prompt failed");
    });
    QSignalSpy errorSpy(&worker, &ScanWorker::error);
    QSignalSpy finishedSpy(&worker, &ScanWorker::finished);

    worker.doScan(root.path(), settings, root.path(), {}, {crashLog});

    QCOMPARE(errorSpy.count(), 1);
    QVERIFY(errorSpy.at(0).at(0).toString().contains(QStringLiteral("recovery prompt failed")));
    QCOMPARE(finishedSpy.count(), 0);

    QFile ignoreFile(ignorePath);
    QVERIFY(ignoreFile.open(QIODevice::ReadOnly));
    QCOMPARE(ignoreFile.readAll(), malformedIgnore);
    const QDir backupDirectory(root.filePath(QStringLiteral("CLASSIC Backup/YAML Data/Local Ignore")));
    QVERIFY(!backupDirectory.exists() || backupDirectory.entryList(QDir::Files | QDir::NoDotAndDotDot).isEmpty());
}

QTEST_MAIN(ScanWorkerCancellationTests)
#include "test_scanworker_cancellation.moc"
