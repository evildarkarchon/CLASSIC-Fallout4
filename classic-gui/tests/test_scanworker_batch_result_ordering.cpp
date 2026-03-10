#include <QSignalSpy>
#include <QtTest/QtTest>

#include "workers/scanworker.h"
#include "workers/scanworker_execution.h"

namespace {
QVector<classic::gui::scanworker_execution::BatchScanResult> g_fakeBatchResults;
}

namespace classic::gui::scanworker_execution {
SingleScanResult executeSingleScan(const ScanExecutionConfig&, const QString&) {
    return {};
}

QVector<BatchScanResult> executeBatchScan(const ScanExecutionConfig&,
                                          const QStringList&,
                                          int,
                                          const BatchProgressCallback&) {
    return g_fakeBatchResults;
}

void writeAutoscanReport(const QString&, const std::string&) {}
}

class ScanWorkerBatchResultOrderingTests : public QObject {
    Q_OBJECT

private slots:
    void multi_log_results_keep_completion_order_and_original_row_identity();
};

void ScanWorkerBatchResultOrderingTests::multi_log_results_keep_completion_order_and_original_row_identity()
{
    ScanWorker worker;
    const QStringList logPaths = {
        QStringLiteral("C:/logs/original-row-0.log"),
        QStringLiteral("C:/logs/original-row-1.log"),
        QStringLiteral("C:/logs/original-row-2.log"),
    };

    g_fakeBatchResults = {
        {2, QStringLiteral("C:/reports/completed-first.log"), true, {}},
        {0, QString(), false, {}},
        {1, QStringLiteral("C:/reports/completed-third.log"), true, {}},
    };

    QSignalSpy logScannedSpy(&worker, &ScanWorker::logScanned);

    worker.doScan(
        logPaths,
        QStringLiteral("unused-root"),
        QStringLiteral("unused-data"),
        QStringLiteral("Fallout4"),
        QStringLiteral("auto"),
        false,
        false,
        false,
        false,
        7
    );

    QCOMPARE(logScannedSpy.count(), 3);

    const QList<QVariant> firstSignal = logScannedSpy.at(0);
    QCOMPARE(firstSignal.at(0).toInt(), 2);
    QCOMPARE(firstSignal.at(1).toBool(), true);
    QCOMPARE(firstSignal.at(2).toString(), QStringLiteral("C:/reports/completed-first.log"));

    const QList<QVariant> secondSignal = logScannedSpy.at(1);
    QCOMPARE(secondSignal.at(0).toInt(), 0);
    QCOMPARE(secondSignal.at(1).toBool(), false);
    QCOMPARE(secondSignal.at(2).toString(), logPaths.at(0));

    const QList<QVariant> thirdSignal = logScannedSpy.at(2);
    QCOMPARE(thirdSignal.at(0).toInt(), 1);
    QCOMPARE(thirdSignal.at(1).toBool(), true);
    QCOMPARE(thirdSignal.at(2).toString(), QStringLiteral("C:/reports/completed-third.log"));
}

QTEST_GUILESS_MAIN(ScanWorkerBatchResultOrderingTests)
#include "test_scanworker_batch_result_ordering.moc"
