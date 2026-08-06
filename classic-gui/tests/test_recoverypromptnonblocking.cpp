#include <QAbstractButton>
#include <QApplication>
#include <QDir>
#include <QEventLoop>
#include <QFile>
#include <QMessageBox>
#include <QSignalSpy>
#include <QTemporaryDir>
#include <QThread>
#include <QTimer>
#include <QWidget>
#include <QtTest/QtTest>

#include "app/localignorerecoveryprompt.h"
#include "controllers/scancontroller.h"
#include "workers/scanworker.h"

#include <functional>

namespace {

using Choice = classic::gui::ScanRunLocalIgnoreRecoveryChoice;

/// Where the breadcrumb trail is written, relative to the test's CTest working directory.
///
/// Named for the test rather than for the exercise that produced it, because whoever finds this in a
/// build directory later needs to know which target wrote it.
constexpr const char* TRACE_FILE_NAME = "recovery-prompt-nonblocking-trace.log";

/// Appends one flushed breadcrumb to the trace file.
///
/// This exists because the two failure modes this test has to tell apart look identical from the
/// outside. CTest does not surface a test binary's captured stdout in this repo, and QTest's own
/// output is stdio-buffered, so an abort inside a Qt assertion and a deadlocked event loop both
/// arrive as a bare non-zero exit code. A flushed file survives both.
void trace(const QString& line)
{
    QFile log(QString::fromLatin1(TRACE_FILE_NAME));
    if (!log.open(QIODevice::Append | QIODevice::Text)) {
        return;
    }
    log.write(line.toUtf8());
    log.write("\n");
    log.flush();
}

/// Number of 5 ms polls to wait for the modal before giving up, so a broken prompt fails instead of
/// hanging the suite until CTest's timeout.
constexpr int PROMPT_POLL_ATTEMPTS = 400;

/// Heartbeat ticks that must land *while the modal is up* before the harness answers it.
///
/// This is the whole measurement. The heartbeat is an ordinary `QTimer` owned by the GUI thread, so
/// it advances only when that thread services its own event queue. If `QMessageBox::exec()` parked
/// the GUI thread instead of starting a nested loop, this count would stay at zero and the harness
/// would trip its failsafe rather than pass.
constexpr int LIVENESS_TICKS = 25;

/// Hard stop for one exchange. A hung prompt must fail this test, not park it for CTest's 600 s.
constexpr int FAILSAFE_MS = 15000;

/// Returns the modal recovery dialog once its nested event loop has shown it, or nullptr.
QMessageBox* findRecoveryDialog()
{
    for (QWidget* widget : QApplication::topLevelWidgets()) {
        auto* box = qobject_cast<QMessageBox*>(widget);
        if (box != nullptr && box->windowTitle() == QStringLiteral("Local Ignore Recovery Required")) {
            return box;
        }
    }
    return nullptr;
}

/// Returns the dialog button whose visible text contains `label`, ignoring Qt's mnemonic escapes.
QAbstractButton* buttonContaining(QMessageBox* box, const QString& label)
{
    for (QAbstractButton* button : box->buttons()) {
        if (button->text().remove(QLatin1Char('&')).contains(label)) {
            return button;
        }
    }
    return nullptr;
}

/// Stands in for the main window and records the event delivery it receives.
///
/// Paint and mouse events reach a widget only through the GUI thread's event dispatch, so counting
/// them separates two things that are easy to conflate: whether the loop is still turning at all,
/// and whether application modality is refusing input to windows other than the prompt.
class ResponsivenessProbe : public QWidget {
public:
    [[nodiscard]] int paints() const { return m_paints; }
    [[nodiscard]] int mousePresses() const { return m_mousePresses; }

protected:
    void paintEvent(QPaintEvent* event) override
    {
        Q_UNUSED(event);
        ++m_paints;
    }

    void mousePressEvent(QMouseEvent* event) override
    {
        ++m_mousePresses;
        QWidget::mousePressEvent(event);
    }

private:
    int m_paints = 0;
    int m_mousePresses = 0;
};

/// Everything one worker-thread-to-GUI-thread recovery exchange revealed.
struct RecoveryExchange {
    Choice choice = Choice::Cancel;
    bool dialogAppeared = false;
    bool failsafeFired = false;
    /// The thread the injected prompt callable was invoked on, i.e. the worker side of the seam.
    QThread* callerThread = nullptr;
    /// The thread the dialog was actually constructed and executed on.
    QThread* promptThread = nullptr;
    /// GUI-thread timer ticks that landed between the dialog appearing and the harness answering it.
    int heartbeatsDuringDialog = 0;
    /// Repaints the sibling window took while the modal was up.
    int repaintsDuringDialog = 0;
    /// Whether a queued call posted from inside the nested loop was delivered before the answer.
    bool queuedCallDelivered = false;
    /// Synthesized clicks the sibling window accepted while the modal was up.
    int clicksDeliveredDuringDialog = 0;
};

/// Owns the GUI-thread probes for one exchange and answers the dialog once liveness is proven.
///
/// The caller supplies the worker side; this supplies the measurement. Every timer here belongs to
/// the GUI thread, so each callback that runs is itself evidence the loop kept turning while
/// `QMessageBox::exec()` sat on that thread's stack. Nothing pumps events by hand — that is the
/// difference between this and the existing `test_scancontroller_recovery.cpp` harness, which calls
/// `QCoreApplication::processEvents` in a loop and would therefore mask the freeze being looked for.
class LivenessHarness {
public:
    /// Arms the probes and the poll timer that answers the dialog with `act`.
    void arm(const std::function<void(QMessageBox*)>& act)
    {
        window.resize(240, 120);
        window.show();

        // Coarse timers on Windows round to the ~15 ms tick, which would make the liveness budget
        // take most of a second to spend. Precise keeps the measurement cheap without weakening it.
        m_heartbeat.setTimerType(Qt::PreciseTimer);
        m_heartbeat.setInterval(1);
        QObject::connect(&m_heartbeat, &QTimer::timeout, &m_heartbeat, [this]() { ++m_heartbeats; });
        m_heartbeat.start();

        m_poll.setInterval(5);
        QObject::connect(&m_poll, &QTimer::timeout, &m_poll, [this, &act]() { onPoll(act); });
        m_poll.start();

        m_failsafe.setSingleShot(true);
        m_failsafe.setInterval(FAILSAFE_MS);
        QObject::connect(&m_failsafe, &QTimer::timeout, &m_failsafe, [this]() {
            exchange.failsafeFired = true;
            // Closing resolves to Cancel, which unblocks the worker so the harness reports a failure
            // instead of deadlocking the suite.
            if (QMessageBox* box = findRecoveryDialog()) {
                box->close();
            }
        });
        m_failsafe.start();
    }

    RecoveryExchange exchange;
    /// Parent for the prompt and target of the repaint and input probes.
    ResponsivenessProbe window;

private:
    void onPoll(const std::function<void(QMessageBox*)>& act)
    {
        QMessageBox* box = findRecoveryDialog();
        if (box == nullptr) {
            if (++m_waitAttempts >= PROMPT_POLL_ATTEMPTS) {
                m_poll.stop();
            }
            return;
        }

        if (!exchange.dialogAppeared) {
            trace(QStringLiteral("poll: dialog found"));
            exchange.dialogAppeared = true;
            m_heartbeatsAtDialog = m_heartbeats;
            m_repaintsAtDialog = window.paints();
            m_clicksAtDialog = window.mousePresses();
            // Posted from inside the nested loop to a receiver on the same thread. Only a loop that
            // is still draining the GUI thread's posted-event queue will ever run it.
            QMetaObject::invokeMethod(
                &window, [this]() { exchange.queuedCallDelivered = true; }, Qt::QueuedConnection);
            return;
        }

        exchange.heartbeatsDuringDialog = m_heartbeats - m_heartbeatsAtDialog;
        exchange.repaintsDuringDialog = window.paints() - m_repaintsAtDialog;
        exchange.clicksDeliveredDuringDialog = window.mousePresses() - m_clicksAtDialog;
        if (exchange.heartbeatsDuringDialog < LIVENESS_TICKS && ++m_waitAttempts < PROMPT_POLL_ATTEMPTS) {
            // Keep asking the sibling window to redraw and keep clicking it, so both probes get a
            // fair chance to be serviced while the prompt owns the screen.
            window.update();
            QTest::mouseClick(&window, Qt::LeftButton);
            return;
        }

        trace(QStringLiteral("poll: answering, heartbeats=%1 repaints=%2 clicks=%3")
                  .arg(exchange.heartbeatsDuringDialog)
                  .arg(exchange.repaintsDuringDialog)
                  .arg(exchange.clicksDeliveredDuringDialog));
        m_poll.stop();
        act(box);
    }

    QTimer m_heartbeat;
    QTimer m_poll;
    QTimer m_failsafe;
    int m_heartbeats = 0;
    int m_waitAttempts = 0;
    /// Probe readings taken the moment the dialog was first seen, so the counts above are deltas
    /// measured across the modal rather than across the whole test.
    int m_heartbeatsAtDialog = 0;
    int m_repaintsAtDialog = 0;
    int m_clicksAtDialog = 0;
};

/// Drives one recovery exchange across the controller seam, with the real dialog answering it.
///
/// This isolates the seam: a bare `QThread` stands in for the scan worker, so the exchange is
/// exactly the marshalling plus the modal, with no scan run underneath. `driveThroughScanWorker`
/// below covers the same seam with the real worker on top of a real run.
RecoveryExchange driveAcrossControllerSeam(bool resetAvailable, const std::function<void(QMessageBox*)>& act)
{
    trace(QStringLiteral("seam: entered, resetAvailable=%1").arg(resetAvailable));
    LivenessHarness harness;

    // SignalHub is a singleton and ThreadManager is only touched by startScan, which this harness
    // does not reach; ScanController null-checks both, so nullptr keeps the exchange self-contained.
    ScanController controller(nullptr, nullptr);
    controller.setLocalIgnoreRecoveryPrompt([&harness](const QString& message, bool available) {
        harness.exchange.promptThread = QThread::currentThread();
        // Parented to the probe, matching MainWindow::initializeControllers, so the dialog is the
        // application-modal child of a real window rather than an unparented top level.
        return classic::gui::promptLocalIgnoreRecoveryChoice(&harness.window, message, available);
    });

    const auto prompt = controller.makeLocalIgnoreRecoveryPrompt();

    QThread worker;
    QObject workerContext;
    workerContext.moveToThread(&worker);
    QObject::connect(&worker, &QThread::started, &workerContext, [&harness, &prompt, &worker, resetAvailable]() {
        harness.exchange.callerThread = QThread::currentThread();
        harness.exchange.choice = prompt(QStringLiteral("Local Ignore YAML Data is malformed."), resetAvailable);
        worker.quit();
    });

    harness.arm(act);

    QEventLoop loop;
    QObject::connect(&worker, &QThread::finished, &loop, &QEventLoop::quit);
    worker.start();
    loop.exec();
    worker.wait();
    trace(QStringLiteral("seam: done, choice=%1 dialog=%2 failsafe=%3")
              .arg(static_cast<int>(harness.exchange.choice))
              .arg(harness.exchange.dialogAppeared)
              .arg(harness.exchange.failsafeFired));

    return harness.exchange;
}

/// The terminal signals a real `ScanWorker` emitted, alongside the exchange it went through.
struct ScanWorkerRun {
    RecoveryExchange exchange;
    int finished = 0;
    int cancelled = 0;
    int error = 0;
    /// What the run itself reported about Reset To Default, as it reached the prompt.
    bool offeredReset = false;
};

/// Builds an installation root whose Local Ignore YAML Data is malformed, so a real run pauses.
///
/// Mirrors the fixture `test_scanworker_cancellation.cpp` uses, because the pause this spike needs
/// to answer only happens against genuinely unparseable Local Ignore content.
bool buildMalformedIgnoreRoot(const QTemporaryDir& root, QString* crashLogOut)
{
    const QDir fixture(QStringLiteral(QT_TESTCASE_SOURCEDIR "/../../tests/fixtures/crash_log_scan_run"));
    const QString databases = root.filePath(QStringLiteral("CLASSIC Data/databases"));
    if (!QDir().mkpath(databases)) {
        return false;
    }
    if (!QFile::copy(fixture.filePath(QStringLiteral("CLASSIC Data/databases/CLASSIC Main.yaml")),
                     QDir(databases).filePath(QStringLiteral("CLASSIC Main.yaml"))) ||
        !QFile::copy(fixture.filePath(QStringLiteral("CLASSIC Data/databases/CLASSIC Fallout4.yaml")),
                     QDir(databases).filePath(QStringLiteral("CLASSIC Fallout4.yaml")))) {
        return false;
    }

    const QByteArray malformedIgnore("CLASSIC_Ignore_Fallout4: [unterminated");
    QFile ignoreFile(root.filePath(QStringLiteral("CLASSIC Data/CLASSIC Ignore.yaml")));
    if (!ignoreFile.open(QIODevice::WriteOnly | QIODevice::Truncate) ||
        ignoreFile.write(malformedIgnore) != static_cast<qint64>(malformedIgnore.size())) {
        return false;
    }
    ignoreFile.close();

    *crashLogOut = root.filePath(QStringLiteral("crash-nonblocking-recovery.log"));
    return QFile::copy(fixture.filePath(QStringLiteral("valid-crash.log")), *crashLogOut);
}

/// Drives a real `ScanWorker` on a real thread through a real paused run, answered by the real dialog.
///
/// This is the shipped path end to end and the reason this test exists: `doScan` takes the one-shot
/// continuation off the execution *before* it calls the prompt, and calls
/// `scan_run_continuation_resume` — a `block_on` across the bridge — *after* the prompt returns. Both
/// of those legs run on the worker thread while the GUI thread owns the modal, and only running them
/// shows they do not interact badly with the `BlockingQueuedConnection` between the two.
ScanWorkerRun driveThroughScanWorker(const QString& installationRoot, const QString& crashLog,
                                     const std::function<void(QMessageBox*)>& act)
{
    trace(QStringLiteral("worker: entered"));
    ScanWorkerRun run;
    LivenessHarness harness;

    ScanController controller(nullptr, nullptr);
    controller.setLocalIgnoreRecoveryPrompt([&harness, &run](const QString& message, bool available) {
        harness.exchange.promptThread = QThread::currentThread();
        run.offeredReset = available;
        harness.exchange.choice = classic::gui::promptLocalIgnoreRecoveryChoice(&harness.window, message, available);
        return harness.exchange.choice;
    });

    // Wrapping the controller's marshalling callable is the only way to observe which thread the
    // worker asked from; ScanWorker offers no hook of its own, and the answer is the point.
    const auto marshalling = controller.makeLocalIgnoreRecoveryPrompt();
    ScanWorker worker([&harness, marshalling](const QString& message, bool available) {
        harness.exchange.callerThread = QThread::currentThread();
        return marshalling(message, available);
    });

    QSignalSpy finishedSpy(&worker, &ScanWorker::finished);
    QSignalSpy cancelledSpy(&worker, &ScanWorker::cancelled);
    QSignalSpy errorSpy(&worker, &ScanWorker::error);

    classic::gui::CrashLogScanLaunchSettings settings;
    settings.game = QStringLiteral("Fallout4");
    settings.gameVersion = QStringLiteral("auto");

    QThread thread;
    worker.moveToThread(&thread);
    QObject::connect(&thread, &QThread::started, &worker,
                     [&worker, &thread, installationRoot, settings, crashLog]() {
                         worker.doScan(installationRoot, settings, installationRoot, {}, {crashLog});
                         thread.quit();
                     });

    harness.arm(act);

    QEventLoop loop;
    QObject::connect(&thread, &QThread::finished, &loop, &QEventLoop::quit);
    thread.start();
    loop.exec();
    thread.wait();

    run.exchange = harness.exchange;
    run.finished = finishedSpy.count();
    run.cancelled = cancelledSpy.count();
    run.error = errorSpy.count();
    trace(QStringLiteral("worker: done, choice=%1 finished=%2 cancelled=%3 error=%4")
              .arg(static_cast<int>(run.exchange.choice))
              .arg(run.finished)
              .arg(run.cancelled)
              .arg(run.error));

    return run;
}

/// Asserts the facts that must hold for every exchange, whatever decision ended it.
#define VERIFY_EVENT_LOOP_STAYED_LIVE(exchange)                                                                        \
    do {                                                                                                               \
        QVERIFY2(!(exchange).failsafeFired, "the recovery exchange never completed on its own");                        \
        QVERIFY2((exchange).dialogAppeared, "the recovery prompt never presented a dialog");                            \
        QVERIFY2((exchange).callerThread != nullptr && (exchange).callerThread != QThread::currentThread(),             \
                 "the prompt must have been requested from the scan worker thread");                                   \
        QCOMPARE((exchange).promptThread, QThread::currentThread());                                                    \
        QVERIFY2((exchange).heartbeatsDuringDialog >= LIVENESS_TICKS,                                                   \
                 "the GUI thread stopped servicing timers while the prompt was up");                                    \
        QVERIFY2((exchange).queuedCallDelivered,                                                                        \
                 "a call queued while the prompt was up was never delivered by the event loop");                        \
        QVERIFY2((exchange).repaintsDuringDialog > 0, "the GUI thread stopped repainting while the prompt was up");     \
    } while (false)

} // namespace

class RecoveryPromptNonBlockingTests : public QObject {
    Q_OBJECT

private slots:
    void initTestCase();
    /// Verifies choosing a decision answers the worker thread without ever parking the GUI thread.
    void choosing_a_decision_keeps_the_event_loop_running();
    /// Verifies abandoning the prompt does the same and still resolves to the non-mutating outcome.
    void abandoning_the_prompt_keeps_the_event_loop_running();
    /// Verifies a run that cannot honor a reset still answers responsively with the reset withheld.
    void withheld_reset_keeps_the_event_loop_running();
    /// Verifies input events keep being dispatched to another window while the prompt is up.
    void input_dispatch_continues_while_the_prompt_is_up();
    /// Verifies the whole shipped path stays responsive: real worker, real run, real dialog.
    void real_scan_worker_recovery_keeps_the_event_loop_running();
    /// Verifies abandoning that same shipped path leaves the run cancelled rather than failed.
    void real_scan_worker_abandonment_keeps_the_event_loop_running();
};

void RecoveryPromptNonBlockingTests::initTestCase()
{
    // Start each run from an empty trail so a hang is read from this run, not the previous one.
    QFile::remove(QString::fromLatin1(TRACE_FILE_NAME));
}

void RecoveryPromptNonBlockingTests::choosing_a_decision_keeps_the_event_loop_running()
{
    bool clicked = false;
    const auto exchange = driveAcrossControllerSeam(true, [&clicked](QMessageBox* box) {
        QAbstractButton* button = buttonContaining(box, QStringLiteral("Continue Without Ignore"));
        if (button == nullptr) {
            box->close();
            return;
        }
        clicked = true;
        button->click();
    });

    VERIFY_EVENT_LOOP_STAYED_LIVE(exchange);
    QVERIFY2(clicked, "Continue Without Ignore was not present in the prompt");
    QCOMPARE(exchange.choice, Choice::ProceedWithoutIgnore);
}

void RecoveryPromptNonBlockingTests::abandoning_the_prompt_keeps_the_event_loop_running()
{
    // Escape is the abandonment route the dialog binds to Cancel, and Cancel is what the worker
    // projects by cancelling the run before it resumes the retained continuation.
    const auto escaped =
        driveAcrossControllerSeam(true, [](QMessageBox* box) { QTest::keyClick(box, Qt::Key_Escape); });
    VERIFY_EVENT_LOOP_STAYED_LIVE(escaped);
    QCOMPARE(escaped.choice, Choice::Cancel);

    // Closing the window is the other way to walk away from the decision.
    const auto closed = driveAcrossControllerSeam(true, [](QMessageBox* box) { box->close(); });
    VERIFY_EVENT_LOOP_STAYED_LIVE(closed);
    QCOMPARE(closed.choice, Choice::Cancel);
}

void RecoveryPromptNonBlockingTests::withheld_reset_keeps_the_event_loop_running()
{
    QStringList offered;
    const auto exchange = driveAcrossControllerSeam(false, [&offered](QMessageBox* box) {
        for (QAbstractButton* button : box->buttons()) {
            offered.append(button->text().remove(QLatin1Char('&')));
        }
        QAbstractButton* button = buttonContaining(box, QStringLiteral("Continue Without Ignore"));
        if (button == nullptr) {
            box->close();
            return;
        }
        button->click();
    });

    VERIFY_EVENT_LOOP_STAYED_LIVE(exchange);
    // Two half-proofs already exist and neither covers this join: test_scancontroller_recovery.cpp
    // shows the availability bool survives the thread hop but answers with a stub, and
    // test_localignorerecoveryprompt.cpp shows the dialog withholds the button but is called
    // directly on the GUI thread. Asserting it here is what shows the responsive path does not
    // quietly restore an option the run reported cannot succeed.
    QVERIFY2(offered.filter(QStringLiteral("Reset to Default")).isEmpty(),
             "Reset To Default must not be offered when the run reported it cannot succeed");
    QCOMPARE(exchange.choice, Choice::ProceedWithoutIgnore);
}

void RecoveryPromptNonBlockingTests::input_dispatch_continues_while_the_prompt_is_up()
{
    // The strongest liveness signal available, because input dispatch is the first thing a genuinely
    // frozen GUI thread loses: the harness clicks the sibling window on every poll tick while the
    // prompt is up, and those clicks are delivered.
    //
    // What this deliberately does not claim is anything about modality. `QTest::mouseClick`
    // synthesizes at the platform layer, and under the headless plugin these tests run on it reaches
    // the sibling window rather than being refused the way a real user's click on an
    // application-modal parent would be. Whether the main window *accepts* input while the prompt is
    // open is a modality question and a Display Layout choice; whether the GUI thread is still
    // dispatching at all is the non-blocking question, and that is what is asserted here.
    const auto exchange =
        driveAcrossControllerSeam(true, [](QMessageBox* box) { QTest::keyClick(box, Qt::Key_Escape); });

    VERIFY_EVENT_LOOP_STAYED_LIVE(exchange);
    QVERIFY2(exchange.clicksDeliveredDuringDialog > 0,
             "the GUI thread stopped dispatching input events while the prompt was up");
    QCOMPARE(exchange.choice, Choice::Cancel);
}

void RecoveryPromptNonBlockingTests::real_scan_worker_recovery_keeps_the_event_loop_running()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    QString crashLog;
    QVERIFY2(buildMalformedIgnoreRoot(root, &crashLog), "could not build a malformed Local Ignore fixture");

    bool clicked = false;
    const auto run = driveThroughScanWorker(root.path(), crashLog, [&clicked](QMessageBox* box) {
        QAbstractButton* button = buttonContaining(box, QStringLiteral("Continue Without Ignore"));
        if (button == nullptr) {
            box->close();
            return;
        }
        clicked = true;
        button->click();
    });

    VERIFY_EVENT_LOOP_STAYED_LIVE(run.exchange);
    QVERIFY2(clicked, "Continue Without Ignore was not present in the prompt");
    QCOMPARE(run.exchange.choice, Choice::ProceedWithoutIgnore);
    // This fixture's Main YAML Data retains a usable default, so the run really can honor a reset;
    // the availability fact reaching the prompt intact is what makes the withheld case meaningful.
    QVERIFY(run.offeredReset);
    // The run resumed and completed after the answer, which is what shows the post-prompt
    // `scan_run_continuation_resume` ran to completion on the worker thread rather than deadlocking
    // against the GUI thread that had just been holding the modal.
    QCOMPARE(run.error, 0);
    QCOMPARE(run.cancelled, 0);
    QCOMPARE(run.finished, 1);
}

void RecoveryPromptNonBlockingTests::real_scan_worker_abandonment_keeps_the_event_loop_running()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    QString crashLog;
    QVERIFY2(buildMalformedIgnoreRoot(root, &crashLog), "could not build a malformed Local Ignore fixture");

    const auto run =
        driveThroughScanWorker(root.path(), crashLog, [](QMessageBox* box) { QTest::keyClick(box, Qt::Key_Escape); });

    VERIFY_EVENT_LOOP_STAYED_LIVE(run.exchange);
    QCOMPARE(run.exchange.choice, Choice::Cancel);
    // Abandoning cancels the run and resumes with a decision it never acts on, so the terminal state
    // is the ordinary cancelled one and nothing was scanned.
    QCOMPARE(run.error, 0);
    QCOMPARE(run.finished, 0);
    QCOMPARE(run.cancelled, 1);
}

QTEST_MAIN(RecoveryPromptNonBlockingTests)
#include "test_recoverypromptnonblocking.moc"
