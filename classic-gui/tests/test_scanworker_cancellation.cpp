#include <QFile>
#include <QSignalSpy>
#include <QTemporaryDir>
#include <QtTest/QtTest>

#include "workers/scanworker.h"

class ScanWorkerCancellationTests : public QObject {
    Q_OBJECT

private slots:
    void requestCancel_before_scan_does_not_crash();
    void requestCancel_is_idempotent();
    void requestCancel_alone_emits_no_signals();
    void requestCancel_before_execution_reaches_the_rust_lifecycle();
};

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

    worker.doScan(root.path(), root.path(), settings, root.path(), {}, {crashLog});

    QCOMPARE(cancelledSpy.count(), 1);
    QVERIFY(cancelledSpy.at(0).at(0).toString().contains(QStringLiteral("before discovery")));
    QCOMPARE(errorSpy.count(), 0);
    QCOMPARE(finishedSpy.count(), 0);
}

QTEST_MAIN(ScanWorkerCancellationTests)
#include "test_scanworker_cancellation.moc"
