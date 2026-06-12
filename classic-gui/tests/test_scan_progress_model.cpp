#include <QtTest/QtTest>

#include "workers/scanprogressmodel.h"

namespace {
classic::scanner::BatchProgressEvent makeEvent(classic::scanner::BatchProgressEventKind eventKind,
                                               classic::scanner::BatchProgressPhase phase, std::uint32_t inputIndex,
                                               std::uint32_t total, bool success = false, const char* path = "test.log")
{
    classic::scanner::BatchProgressEvent event{};
    event.completed = 0;
    event.total = total;
    event.input_index = inputIndex;
    event.log_path = path;
    event.event_kind = eventKind;
    event.phase = phase;
    event.success = success;
    return event;
}
} // namespace

class ScanProgressModelTests : public QObject {
    Q_OBJECT

private slots:
    void percent_stays_monotonic_for_single_log_lifecycle();
    void mixed_batch_progress_advances_before_terminal_completion();
    void late_phase_regressions_are_ignored_after_terminal_state();
};

void ScanProgressModelTests::percent_stays_monotonic_for_single_log_lifecycle()
{
    BatchProgressModel model(1);

    const QList<classic::scanner::BatchProgressEvent> events = {
        makeEvent(classic::scanner::BatchProgressEventKind::Queued, classic::scanner::BatchProgressPhase::Setup, 0, 1),
        makeEvent(classic::scanner::BatchProgressEventKind::Started, classic::scanner::BatchProgressPhase::Setup, 0, 1),
        makeEvent(classic::scanner::BatchProgressEventKind::Phase, classic::scanner::BatchProgressPhase::Setup, 0, 1),
        makeEvent(classic::scanner::BatchProgressEventKind::Phase, classic::scanner::BatchProgressPhase::Parse, 0, 1),
        makeEvent(classic::scanner::BatchProgressEventKind::Phase, classic::scanner::BatchProgressPhase::Analyze, 0, 1),
        makeEvent(classic::scanner::BatchProgressEventKind::Phase, classic::scanner::BatchProgressPhase::Finalize, 0,
                  1),
        makeEvent(classic::scanner::BatchProgressEventKind::Completed, classic::scanner::BatchProgressPhase::Finalize,
                  0, 1, true),
    };

    float previous = -1.0f;
    for (const auto& event : events) {
        const float next = model.update(event);
        QVERIFY2(next >= previous, "Progress percent should never decrease");
        previous = next;
    }

    QCOMPARE(model.percent(), 100.0f);
}

void ScanProgressModelTests::mixed_batch_progress_advances_before_terminal_completion()
{
    BatchProgressModel model(3);

    const float queued = model.update(
        makeEvent(classic::scanner::BatchProgressEventKind::Queued, classic::scanner::BatchProgressPhase::Setup, 0, 3));
    QCOMPARE(queued, 0.0f);

    const float parseProgress = model.update(
        makeEvent(classic::scanner::BatchProgressEventKind::Phase, classic::scanner::BatchProgressPhase::Parse, 1, 3));
    QVERIFY2(parseProgress > 0.0f, "In-flight phase updates should advance visible batch progress");

    const float analyzeProgress = model.update(makeEvent(classic::scanner::BatchProgressEventKind::Phase,
                                                         classic::scanner::BatchProgressPhase::Analyze, 1, 3));
    QVERIFY2(analyzeProgress > parseProgress, "Later phases should contribute more progress for heavy logs");
}

void ScanProgressModelTests::late_phase_regressions_are_ignored_after_terminal_state()
{
    BatchProgressModel model(1);

    const float completed = model.update(makeEvent(classic::scanner::BatchProgressEventKind::Completed,
                                                   classic::scanner::BatchProgressPhase::Finalize, 0, 1, true));
    const float regressed = model.update(
        makeEvent(classic::scanner::BatchProgressEventKind::Phase, classic::scanner::BatchProgressPhase::Parse, 0, 1));

    QCOMPARE(completed, 100.0f);
    QCOMPARE(regressed, completed);
}

QTEST_MAIN(ScanProgressModelTests)
#include "test_scan_progress_model.moc"
