#include <QSignalSpy>
#include <QtTest/QtTest>

#include "workers/scanworker.h"

class ScanWorkerCancellationTests : public QObject {
    Q_OBJECT

private slots:
    void requestCancel_before_scan_does_not_crash();
    void requestCancel_is_idempotent();
    void requestCancel_alone_emits_no_signals();
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

    // requestCancel() only sets the flag; signals are emitted by doScan().
    QCOMPARE(errorSpy.count(), 0);
    QCOMPARE(finishedSpy.count(), 0);
}

QTEST_MAIN(ScanWorkerCancellationTests)
#include "test_scanworker_cancellation.moc"
