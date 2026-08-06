#include <QSignalSpy>
#include <QThread>
#include <QtTest/QtTest>

#include "controllers/scancontroller.h"

#include <functional>

namespace {

using Choice = classic::gui::ScanRunLocalIgnoreRecoveryChoice;

/// Runs one callable on a separate thread and returns its result.
///
/// The recovery prompt is invoked from the scan worker thread while Rust still owns the retained
/// continuation, so the marshalling behavior only exists off the GUI thread.
template <typename Callable> auto runOffGuiThread(Callable callable) -> decltype(callable())
{
    using Result = decltype(callable());
    Result result{};
    QThread worker;
    QObject context;
    context.moveToThread(&worker);
    QObject::connect(&worker, &QThread::started, &context, [&callable, &result, &worker]() {
        result = callable();
        worker.quit();
    });
    worker.start();
    // The GUI thread must keep pumping events; the prompt marshals back into it and blocks.
    while (!worker.wait(10)) {
        QCoreApplication::processEvents(QEventLoop::AllEvents, 10);
    }
    return result;
}

} // namespace

class ScanControllerRecoveryTests : public QObject {
    Q_OBJECT

private slots:
    /// Verifies an unconfigured controller answers with the outcome that mutates nothing.
    void missing_prompt_resolves_to_cancel();
    /// Verifies the configured GUI prompt receives the message and returns its typed decision.
    void configured_prompt_returns_each_typed_decision_data();
    void configured_prompt_returns_each_typed_decision();
    /// Verifies a worker-thread request runs the prompt on the controller's thread and blocks for it.
    void worker_thread_request_is_answered_on_the_gui_thread();
    /// Verifies a destroyed controller cannot strand the worker or authorize a mutation.
    void destroyed_controller_resolves_to_cancel();
};

void ScanControllerRecoveryTests::missing_prompt_resolves_to_cancel()
{
    // SignalHub is a singleton and ThreadManager is only touched by startScan, which these tests do
    // not reach; ScanController null-checks both, so nullptr keeps the cases independent.
    ScanController controller(nullptr, nullptr);

    const auto prompt = controller.makeLocalIgnoreRecoveryPrompt();

    QCOMPARE(prompt(QStringLiteral("malformed"), true), Choice::Cancel);
}

void ScanControllerRecoveryTests::configured_prompt_returns_each_typed_decision_data()
{
    QTest::addColumn<int>("choiceValue");
    QTest::newRow("reset-to-default") << static_cast<int>(Choice::ResetToDefault);
    QTest::newRow("proceed-without-ignore") << static_cast<int>(Choice::ProceedWithoutIgnore);
    QTest::newRow("cancel") << static_cast<int>(Choice::Cancel);
}

void ScanControllerRecoveryTests::configured_prompt_returns_each_typed_decision()
{
    QFETCH(int, choiceValue);

    // SignalHub is a singleton and ThreadManager is only touched by startScan, which these tests do
    // not reach; ScanController null-checks both, so nullptr keeps the cases independent.
    ScanController controller(nullptr, nullptr);

    QString seenMessage;
    bool seenResetAvailable = true;
    controller.setLocalIgnoreRecoveryPrompt(
        [&seenMessage, &seenResetAvailable, choiceValue](const QString& message, bool resetAvailable) {
            seenMessage = message;
            seenResetAvailable = resetAvailable;
            return static_cast<Choice>(choiceValue);
        });

    const auto prompt = controller.makeLocalIgnoreRecoveryPrompt();
    const auto choice = prompt(QStringLiteral("Local Ignore YAML Data is malformed."), false);

    QCOMPARE(static_cast<int>(choice), choiceValue);
    QCOMPARE(seenMessage, QStringLiteral("Local Ignore YAML Data is malformed."));
    // The controller marshals the run's answer; it must not substitute one of its own.
    QCOMPARE(seenResetAvailable, false);
}

void ScanControllerRecoveryTests::worker_thread_request_is_answered_on_the_gui_thread()
{
    // SignalHub is a singleton and ThreadManager is only touched by startScan, which these tests do
    // not reach; ScanController null-checks both, so nullptr keeps the cases independent.
    ScanController controller(nullptr, nullptr);

    QThread* promptThread = nullptr;
    bool seenResetAvailable = true;
    controller.setLocalIgnoreRecoveryPrompt([&promptThread, &seenResetAvailable](const QString&, bool resetAvailable) {
        promptThread = QThread::currentThread();
        seenResetAvailable = resetAvailable;
        return Choice::ResetToDefault;
    });

    const auto prompt = controller.makeLocalIgnoreRecoveryPrompt();
    QThread* callerThread = nullptr;
    const Choice choice = runOffGuiThread([&prompt, &callerThread]() {
        callerThread = QThread::currentThread();
        return prompt(QStringLiteral("malformed"), false);
    });

    QCOMPARE(choice, Choice::ResetToDefault);
    QVERIFY2(callerThread != nullptr && callerThread != QThread::currentThread(),
             "the prompt must have been requested from a worker thread");
    QCOMPARE(promptThread, QThread::currentThread());
    // Availability is captured by value into the queued lambda, so it has to survive the hop to the
    // GUI thread intact. A frontend that offered the decision here would be offering it on a run
    // that already reported it cannot succeed.
    QCOMPARE(seenResetAvailable, false);
}

void ScanControllerRecoveryTests::destroyed_controller_resolves_to_cancel()
{
    classic::gui::ScanRunLocalIgnoreRecoveryPrompt prompt;
    {
        ScanController controller(nullptr, nullptr);
        controller.setLocalIgnoreRecoveryPrompt([](const QString&, bool) { return Choice::ResetToDefault; });
        prompt = controller.makeLocalIgnoreRecoveryPrompt();
    }

    // The QPointer capture goes null with the controller, so a late worker request cannot reach a
    // dangling object and cannot answer with the destructive decision the prompt used to return.
    QCOMPARE(prompt(QStringLiteral("malformed"), true), Choice::Cancel);
}

QTEST_MAIN(ScanControllerRecoveryTests)
#include "test_scancontroller_recovery.moc"
