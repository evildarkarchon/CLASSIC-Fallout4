#include "core/guiusersettings.h"
#include "workers/scanrequestbuilder.h"

#include <QTemporaryDir>
#include <QtTest>

#include "classic_cxx_bridge/scanner.h"

#include <cstddef>
#include <string>

namespace {

/// Creates representative accepted GUI settings for tagged request behavior tests.
classic::gui::CrashLogScanLaunchSettings makeSettings()
{
    classic::gui::CrashLogScanLaunchSettings settings;
    settings.game = QStringLiteral("Fallout4");
    settings.gameVersion = QStringLiteral("NextGen");
    settings.formIdValueLookup = true;
    settings.simplifyLogs = true;
    settings.moveUnsolvedLogs = true;
    settings.unsolvedLogsDestination = QStringLiteral("E:/Unsolved");
    settings.maxConcurrentScans = 8;
    settings.customScanDirectory = {};
    settings.formIdDatabasePaths = {QStringLiteral("databases/official.db")};
    return settings;
}

/// Records the tagged source published by Rust discovery and stops before any discovered work is admitted.
class DiscoveryCancellingObserver final : public classic::scanner::ScanRunObserver {
public:
    /// Borrows the run's separate monotonic cancellation control for the execution lifetime.
    explicit DiscoveryCancellingObserver(const classic::scanner::ScanRunCancellation& cancellation) noexcept
        : m_cancellation(cancellation)
    {
    }

    /// Retains the discovery tag and requests cancellation without throwing across CXX.
    void on_scan_run_event(const classic::scanner::ScanRunContractEvent& event) const noexcept override
    {
        if (event.kind != classic::scanner::ScanRunContractEventKind::DiscoveryCompleted) {
            return;
        }
        m_sawDiscovery = true;
        m_source = event.discovery.source;
        classic::scanner::scan_run_cancellation_cancel(m_cancellation);
    }

    /// Returns whether the Rust-owned discovery lifecycle event was observed.
    [[nodiscard]] bool sawDiscovery() const noexcept { return m_sawDiscovery; }

    /// Returns the source tag carried by the completed discovery result.
    [[nodiscard]] classic::scanner::ScanRunContractDiscoverySource source() const noexcept { return m_source; }

private:
    const classic::scanner::ScanRunCancellation& m_cancellation;
    mutable bool m_sawDiscovery = false;
    mutable classic::scanner::ScanRunContractDiscoverySource m_source =
        classic::scanner::ScanRunContractDiscoverySource::Standard;
};

/// Builds and executes one request without an observer so terminal discovery data can be asserted.
classic::scanner::ScanRunContractExecutionResult execute(const QString& yamlRoot, const QString& yamlData,
                                                         const QString& baseDirectory,
                                                         const classic::gui::CrashLogScanLaunchSettings& settings,
                                                         const QStringList& targetedInputs)
{
    const auto request =
        classic::gui::buildScanRunRequest(yamlRoot, yamlData, baseDirectory, settings, {}, targetedInputs);
    const auto cancellation = classic::scanner::scan_run_cancellation_new();
    return classic::scanner::scan_run_contract_execute(*request, *cancellation, nullptr);
}

} // namespace

class ScanRequestBuilderTests : public QObject {
    Q_OBJECT

private slots:
    void no_targeted_inputs_constructs_a_tagged_standard_request();
    void targeted_inputs_construct_a_tagged_targeted_request_with_structured_rejections();
};

void ScanRequestBuilderTests::no_targeted_inputs_constructs_a_tagged_standard_request()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());

    const auto request = classic::gui::buildScanRunRequest(root.path(), root.filePath(QStringLiteral("CLASSIC Data")),
                                                           root.path(), makeSettings(), {}, {});
    const auto cancellation = classic::scanner::scan_run_cancellation_new();
    const DiscoveryCancellingObserver observer(*cancellation);
    const auto execution = classic::scanner::scan_run_contract_execute(*request, *cancellation, &observer);

    QVERIFY2(execution.has_result, "Standard discovery should produce an expected lifecycle result");
    QVERIFY(!execution.has_error);
    QVERIFY(observer.sawDiscovery());
    QCOMPARE(observer.source(), classic::scanner::ScanRunContractDiscoverySource::Standard);
    QVERIFY(execution.result.has_discovery);
    QCOMPARE(execution.result.discovery.source, classic::scanner::ScanRunContractDiscoverySource::Standard);
    QVERIFY(execution.result.status == classic::scanner::ScanRunContractStatus::NoCrashLogsFound ||
            execution.result.status == classic::scanner::ScanRunContractStatus::Cancelled);
}

void ScanRequestBuilderTests::targeted_inputs_construct_a_tagged_targeted_request_with_structured_rejections()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    const QString missingInput = root.filePath(QStringLiteral("missing-crash.log"));

    auto settings = makeSettings();
    // This persisted Standard-run choice must not make movement representable on the Targeted request constructor.
    settings.moveUnsolvedLogs = true;
    settings.unsolvedLogsDestination = root.filePath(QStringLiteral("Unsolved Logs"));

    const auto execution =
        execute(root.path(), root.filePath(QStringLiteral("CLASSIC Data")), root.path(), settings, {missingInput});

    QVERIFY2(execution.has_result, "Rejected Targeted inputs are discovery data, not a run-wide failure");
    QVERIFY(!execution.has_error);
    QCOMPARE(execution.result.status, classic::scanner::ScanRunContractStatus::NoCrashLogsFound);
    QVERIFY(execution.result.has_discovery);
    QCOMPARE(execution.result.discovery.source, classic::scanner::ScanRunContractDiscoverySource::Targeted);
    QCOMPARE(execution.result.discovery.accepted_logs.size(), std::size_t{0});
    QCOMPARE(execution.result.discovery.rejected_inputs.size(), std::size_t{1});
    QCOMPARE(QString::fromStdString(std::string(execution.result.discovery.rejected_inputs[0].path)), missingInput);
    QVERIFY2(!execution.result.discovery.rejected_inputs[0].reason.empty(),
             "Rust discovery must retain the reason for every rejected Targeted input");
}

QTEST_MAIN(ScanRequestBuilderTests)
#include "test_scanrequestbuilder.moc"
