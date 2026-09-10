#include <QSignalSpy>
#include <QThread>
#include <QtTest/QtTest>

#include "controllers/scancontroller.h"
#include "recoverypromptfixture.h"

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

    QCOMPARE(prompt(classic::gui::test::recoveryPresentation()), Choice::Cancel);
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

    classic::gui::ScanRunLocalIgnoreRecoveryPresentation seen;
    controller.setLocalIgnoreRecoveryPrompt(
        [&seen, choiceValue](const classic::gui::ScanRunLocalIgnoreRecoveryPresentation& recovery) {
            seen = recovery;
            return static_cast<Choice>(choiceValue);
        });

    const auto prompt = controller.makeLocalIgnoreRecoveryPrompt();
    const auto choice = prompt(classic::gui::test::recoveryPresentation(false));

    QCOMPARE(static_cast<int>(choice), choiceValue);
    QCOMPARE(seen.message, QStringLiteral("Local Ignore YAML Data is malformed."));
    // The controller marshals the run's question; it must not substitute one of its own. Every
    // decision arrives, and the availability on each is the run's answer rather than the
    // controller's.
    QCOMPARE(seen.decisions.size(), 2);
    QVERIFY(seen.decisions[0].available);
    QCOMPARE(seen.decisions[1].decision, classic::scanner::ScanRunLocalIgnoreRecoveryDecision::ResetToDefault);
    QVERIFY(!seen.decisions[1].available);
}

void ScanControllerRecoveryTests::worker_thread_request_is_answered_on_the_gui_thread()
{
    // SignalHub is a singleton and ThreadManager is only touched by startScan, which these tests do
    // not reach; ScanController null-checks both, so nullptr keeps the cases independent.
    ScanController controller(nullptr, nullptr);

    QThread* promptThread = nullptr;
    classic::gui::ScanRunLocalIgnoreRecoveryPresentation seen;
    controller.setLocalIgnoreRecoveryPrompt(
        [&promptThread, &seen](const classic::gui::ScanRunLocalIgnoreRecoveryPresentation& recovery) {
            promptThread = QThread::currentThread();
            seen = recovery;
            return Choice::ResetToDefault;
        });

    const auto prompt = controller.makeLocalIgnoreRecoveryPrompt();
    QThread* callerThread = nullptr;
    const Choice choice = runOffGuiThread([&prompt, &callerThread]() {
        callerThread = QThread::currentThread();
        return prompt(classic::gui::test::recoveryPresentation(false));
    });

    QCOMPARE(choice, Choice::ResetToDefault);
    QVERIFY2(callerThread != nullptr && callerThread != QThread::currentThread(),
             "the prompt must have been requested from a worker thread");
    QCOMPARE(promptThread, QThread::currentThread());
    // The whole presentation is captured by value into the queued lambda, so every described
    // decision — and the availability attached to each — has to survive the hop to the GUI thread
    // intact. A dialog that offered the withheld decision here would be offering it on a run that
    // already reported it cannot succeed.
    QCOMPARE(seen.decisions.size(), 2);
    QVERIFY(!seen.decisions[1].available);
    QCOMPARE(seen.decisions[1].description, QStringLiteral("what resetting does"));
}

void ScanControllerRecoveryTests::destroyed_controller_resolves_to_cancel()
{
    classic::gui::ScanRunLocalIgnoreRecoveryPrompt prompt;
    {
        ScanController controller(nullptr, nullptr);
        controller.setLocalIgnoreRecoveryPrompt(
            [](const classic::gui::ScanRunLocalIgnoreRecoveryPresentation&) { return Choice::ResetToDefault; });
        prompt = controller.makeLocalIgnoreRecoveryPrompt();
    }

    // The QPointer capture goes null with the controller, so a late worker request cannot reach a
    // dangling object and cannot answer with the destructive decision the prompt used to return.
    QCOMPARE(prompt(classic::gui::test::recoveryPresentation()), Choice::Cancel);
}

QTEST_MAIN(ScanControllerRecoveryTests)
#include "test_scancontroller_recovery.moc"
