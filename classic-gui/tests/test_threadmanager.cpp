#include <QPointer>
#include <QThread>
#include <QtTest/QtTest>

#include "core/threadmanager.h"

class ThreadManagerTests : public QObject {
    Q_OBJECT

private slots:
    void start_and_stop_worker_updates_running_state();
    void stopWorker_deletes_worker_after_thread_shutdown();
    void stopAll_stops_all_registered_workers();
    void stopWorker_on_missing_name_is_noop();
};

void ThreadManagerTests::start_and_stop_worker_updates_running_state()
{
    ThreadManager manager;

    manager.startWorker(QStringLiteral("scan"), new QThread(), new QObject());
    QTRY_VERIFY_WITH_TIMEOUT(manager.isRunning(QStringLiteral("scan")), 2000);

    manager.stopWorker(QStringLiteral("scan"));
    QVERIFY(!manager.isRunning(QStringLiteral("scan")));
}

void ThreadManagerTests::stopWorker_deletes_worker_after_thread_shutdown()
{
    ThreadManager manager;
    auto* worker = new QObject();
    QPointer<QObject> workerGuard(worker);

    manager.startWorker(QStringLiteral("scan"), new QThread(), worker);
    QTRY_VERIFY_WITH_TIMEOUT(manager.isRunning(QStringLiteral("scan")), 2000);

    manager.stopWorker(QStringLiteral("scan"));

    QVERIFY(!manager.isRunning(QStringLiteral("scan")));
    QTRY_VERIFY_WITH_TIMEOUT(workerGuard.isNull(), 2000);
}

void ThreadManagerTests::stopAll_stops_all_registered_workers()
{
    ThreadManager manager;

    manager.startWorker(QStringLiteral("scan"), new QThread(), new QObject());
    manager.startWorker(QStringLiteral("update"), new QThread(), new QObject());

    QTRY_VERIFY_WITH_TIMEOUT(manager.isRunning(QStringLiteral("scan")), 2000);
    QTRY_VERIFY_WITH_TIMEOUT(manager.isRunning(QStringLiteral("update")), 2000);

    manager.stopAll();

    QVERIFY(!manager.isRunning(QStringLiteral("scan")));
    QVERIFY(!manager.isRunning(QStringLiteral("update")));
}

void ThreadManagerTests::stopWorker_on_missing_name_is_noop()
{
    ThreadManager manager;
    manager.stopWorker(QStringLiteral("missing"));
    QVERIFY(!manager.isRunning(QStringLiteral("missing")));
}

QTEST_GUILESS_MAIN(ThreadManagerTests)
#include "test_threadmanager.moc"
