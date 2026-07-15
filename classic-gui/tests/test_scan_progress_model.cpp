#include <QtTest/QtTest>

#include "workers/scanprogressmodel.h"

#include <cstddef>
#include <initializer_list>

namespace {

/// Creates the serialized event that initializes GUI run totals from Rust discovery.
classic::scanner::ScanRunContractEvent makeDiscoveryEvent(std::initializer_list<const char*> acceptedLogs)
{
    classic::scanner::ScanRunContractEvent event{};
    event.kind = classic::scanner::ScanRunContractEventKind::DiscoveryCompleted;
    event.discovery.source = classic::scanner::ScanRunContractDiscoverySource::Targeted;
    for (const char* path : acceptedLogs) {
        event.discovery.accepted_logs.push_back(path);
    }
    return event;
}

/// Creates the serialized event that publishes Rust-selected effective concurrency.
classic::scanner::ScanRunContractEvent makeConcurrencyEvent(std::size_t effectiveConcurrency)
{
    classic::scanner::ScanRunContractEvent event{};
    event.kind = classic::scanner::ScanRunContractEventKind::EffectiveConcurrencySelected;
    event.effective_concurrency = effectiveConcurrency;
    return event;
}

/// Creates one per-log lifecycle event with its discovery correlation and aggregate counts.
classic::scanner::ScanRunContractEvent makeLogEvent(classic::scanner::ScanRunContractEventKind kind,
                                                    classic::scanner::BatchProgressPhase phase,
                                                    std::size_t discoveryIndex, std::size_t completed,
                                                    std::size_t total,
                                                    classic::scanner::ScanRunContractLogDisposition disposition =
                                                        classic::scanner::ScanRunContractLogDisposition::Succeeded)
{
    classic::scanner::ScanRunContractEvent event{};
    event.kind = kind;
    event.phase = phase;
    event.discovery_index = discoveryIndex;
    event.completed = completed;
    event.total = total;
    event.crash_log = "C:/Crash Logs/test.log";
    event.disposition = disposition;
    return event;
}

} // namespace

class ScanProgressModelTests : public QObject {
    Q_OBJECT

private slots:
    void discovery_and_effective_concurrency_initialize_run_state();
    void percent_stays_monotonic_for_one_serialized_log_lifecycle();
    void interleaved_log_events_advance_before_terminal_completion();
    void late_phase_regressions_are_ignored_after_terminal_state();
    void failed_log_finished_event_contributes_complete_work();
};

void ScanProgressModelTests::discovery_and_effective_concurrency_initialize_run_state()
{
    BatchProgressModel model;

    QCOMPARE(model.update(makeDiscoveryEvent({"C:/logs/one.log", "C:/logs/two.log", "C:/logs/three.log"})), 0.0f);
    QCOMPARE(model.totalLogs(), 3);
    QCOMPARE(model.effectiveConcurrency(), 0);

    QCOMPARE(model.update(makeConcurrencyEvent(2)), 0.0f);
    QCOMPARE(model.totalLogs(), 3);
    QCOMPARE(model.effectiveConcurrency(), 2);
}

void ScanProgressModelTests::percent_stays_monotonic_for_one_serialized_log_lifecycle()
{
    BatchProgressModel model;
    model.update(makeDiscoveryEvent({"C:/logs/one.log"}));

    const QList<classic::scanner::ScanRunContractEvent> events = {
        makeLogEvent(classic::scanner::ScanRunContractEventKind::LogQueued, classic::scanner::BatchProgressPhase::Setup,
                     0, 0, 1),
        makeLogEvent(classic::scanner::ScanRunContractEventKind::LogStarted,
                     classic::scanner::BatchProgressPhase::Setup, 0, 0, 1),
        makeLogEvent(classic::scanner::ScanRunContractEventKind::LogPhase, classic::scanner::BatchProgressPhase::Setup,
                     0, 0, 1),
        makeLogEvent(classic::scanner::ScanRunContractEventKind::LogPhase, classic::scanner::BatchProgressPhase::Parse,
                     0, 0, 1),
        makeLogEvent(classic::scanner::ScanRunContractEventKind::LogPhase,
                     classic::scanner::BatchProgressPhase::Analyze, 0, 0, 1),
        makeLogEvent(classic::scanner::ScanRunContractEventKind::LogPhase,
                     classic::scanner::BatchProgressPhase::Finalize, 0, 0, 1),
        makeLogEvent(classic::scanner::ScanRunContractEventKind::LogFinished,
                     classic::scanner::BatchProgressPhase::Finalize, 0, 1, 1),
    };

    float previous = -1.0f;
    for (const auto& event : events) {
        const float next = model.update(event);
        QVERIFY2(next >= previous, "Serialized Crash Log Scan Run events must never decrease visible progress");
        previous = next;
    }

    QCOMPARE(model.percent(), 100.0f);
}

void ScanProgressModelTests::interleaved_log_events_advance_before_terminal_completion()
{
    BatchProgressModel model;
    model.update(makeDiscoveryEvent({"C:/logs/one.log", "C:/logs/two.log", "C:/logs/three.log"}));

    const float queued = model.update(makeLogEvent(classic::scanner::ScanRunContractEventKind::LogQueued,
                                                   classic::scanner::BatchProgressPhase::Setup, 0, 0, 3));
    QCOMPARE(queued, 0.0f);

    const float parseProgress = model.update(makeLogEvent(classic::scanner::ScanRunContractEventKind::LogPhase,
                                                          classic::scanner::BatchProgressPhase::Parse, 1, 0, 3));
    QVERIFY2(parseProgress > 0.0f, "An in-flight phase must advance visible run progress");

    const float analyzeProgress = model.update(makeLogEvent(classic::scanner::ScanRunContractEventKind::LogPhase,
                                                            classic::scanner::BatchProgressPhase::Analyze, 1, 0, 3));
    QVERIFY2(analyzeProgress > parseProgress, "A later phase must contribute more progress for the same Crash Log");
}

void ScanProgressModelTests::late_phase_regressions_are_ignored_after_terminal_state()
{
    BatchProgressModel model;
    model.update(makeDiscoveryEvent({"C:/logs/one.log"}));

    const float completed = model.update(makeLogEvent(classic::scanner::ScanRunContractEventKind::LogFinished,
                                                      classic::scanner::BatchProgressPhase::Finalize, 0, 1, 1));
    const float regressed = model.update(makeLogEvent(classic::scanner::ScanRunContractEventKind::LogPhase,
                                                      classic::scanner::BatchProgressPhase::Parse, 0, 0, 1));

    QCOMPARE(completed, 100.0f);
    QCOMPARE(regressed, completed);
}

void ScanProgressModelTests::failed_log_finished_event_contributes_complete_work()
{
    BatchProgressModel model;
    model.update(makeDiscoveryEvent({"C:/logs/one.log"}));

    const float completed = model.update(makeLogEvent(classic::scanner::ScanRunContractEventKind::LogFinished,
                                                      classic::scanner::BatchProgressPhase::Finalize, 0, 1, 1,
                                                      classic::scanner::ScanRunContractLogDisposition::Failed));

    QCOMPARE(completed, 100.0f);
}

QTEST_MAIN(ScanProgressModelTests)
#include "test_scan_progress_model.moc"
