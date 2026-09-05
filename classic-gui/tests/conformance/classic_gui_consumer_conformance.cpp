#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonParseError>
#include <QRegularExpression>
#include <QSaveFile>
#include <QThread>

#include "controllers/scancontroller.h"
#include "workers/scanprogressmodel.h"
#include "workers/scanrunpresentation.h"

#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>

namespace {

namespace scanner = classic::scanner;

constexpr int SKIP_RETURN_CODE = 125;
constexpr auto RUN_PLAN_ENV = "CLASSIC_CONSUMER_CONFORMANCE_RUN_PLAN";
constexpr auto OUTPUT_ENV = "CLASSIC_CONSUMER_CONFORMANCE_OUTPUT";
constexpr auto RUNNER_ID = "classic-gui-consumer-conformance";

class RunnerError final : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

struct QtConsumerObservations {
    QJsonObject workerDispatch;
    QJsonObject pathLinks;
    QJsonObject recoveryInteraction;
    QJsonObject modelUpdates;
    QJsonObject displayContentDelivery;
};

/// Returns one required object member or rejects the closed input plan early.
QJsonObject requiredObject(const QJsonObject& object, const QString& member)
{
    const auto value = object.value(member);
    if (!value.isObject()) {
        throw RunnerError(QStringLiteral("run plan member %1 must be an object").arg(member).toStdString());
    }
    return value.toObject();
}

/// Returns one required array member or rejects the closed input plan early.
QJsonArray requiredArray(const QJsonObject& object, const QString& member)
{
    const auto value = object.value(member);
    if (!value.isArray()) {
        throw RunnerError(QStringLiteral("run plan member %1 must be an array").arg(member).toStdString());
    }
    return value.toArray();
}

/// Reads one immutable JSON document and rejects malformed or non-object roots.
QJsonObject readJsonObject(const QString& path)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) {
        throw RunnerError(QStringLiteral("cannot open run plan: %1").arg(file.errorString()).toStdString());
    }
    QJsonParseError parseError;
    const auto document = QJsonDocument::fromJson(file.readAll(), &parseError);
    if (parseError.error != QJsonParseError::NoError || !document.isObject()) {
        throw RunnerError(QStringLiteral("invalid run plan JSON: %1").arg(parseError.errorString()).toStdString());
    }
    return document.object();
}

/// Publishes the receipt atomically so validation never observes partial JSON.
void publishReceipt(const QString& path, const QJsonObject& receipt)
{
    QSaveFile file(path);
    if (!file.open(QIODevice::WriteOnly)) {
        throw RunnerError(QStringLiteral("cannot create receipt: %1").arg(file.errorString()).toStdString());
    }
    const QByteArray payload = QJsonDocument(receipt).toJson(QJsonDocument::Indented);
    if (file.write(payload) != payload.size() || !file.commit()) {
        throw RunnerError(QStringLiteral("cannot publish receipt: %1").arg(file.errorString()).toStdString());
    }
}

/// Creates one flattened bridge segment with every carrier field explicit.
scanner::ScanRunDisplaySegment displaySegment(scanner::ScanRunDisplaySegmentKind kind, const char* text = "",
                                              const char* path = "", std::uint64_t count = 0)
{
    scanner::ScanRunDisplaySegment segment{};
    segment.kind = kind;
    segment.text = text;
    segment.path = path;
    segment.count = count;
    return segment;
}

/// Returns the frozen observation token for one bridged Display Content segment kind.
QString segmentKindToken(scanner::ScanRunDisplaySegmentKind kind)
{
    using Kind = scanner::ScanRunDisplaySegmentKind;
    switch (kind) {
    case Kind::Text:
        return QStringLiteral("text");
    case Kind::Label:
        return QStringLiteral("label");
    case Kind::Count:
        return QStringLiteral("count");
    case Kind::Path:
        return QStringLiteral("path");
    case Kind::Name:
        return QStringLiteral("name");
    case Kind::Emphasis:
        return QStringLiteral("emphasis");
    }
    throw RunnerError("unknown Display Content segment kind");
}

/// Returns the frozen observation token for one bridged Display Content severity.
QString severityToken(scanner::ScanRunDisplaySeverity severity)
{
    using Severity = scanner::ScanRunDisplaySeverity;
    switch (severity) {
    case Severity::Info:
        return QStringLiteral("info");
    case Severity::Notice:
        return QStringLiteral("notice");
    case Severity::Warning:
        return QStringLiteral("warning");
    case Severity::Failure:
        return QStringLiteral("failure");
    case Severity::Success:
        return QStringLiteral("success");
    }
    throw RunnerError("unknown Display Content severity");
}

/// Returns the frozen observation token for one Local Ignore recovery decision.
QString recoveryDecisionToken(scanner::ScanRunLocalIgnoreRecoveryDecision decision)
{
    switch (decision) {
    case scanner::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore:
        return QStringLiteral("proceed-without-ignore");
    case scanner::ScanRunLocalIgnoreRecoveryDecision::ResetToDefault:
        return QStringLiteral("reset-to-default");
    }
    throw RunnerError("unknown Local Ignore recovery decision");
}

/// Returns the frozen observation token for the choice returned by the Qt recovery interaction.
QString recoveryChoiceToken(classic::gui::ScanRunLocalIgnoreRecoveryChoice choice)
{
    using Choice = classic::gui::ScanRunLocalIgnoreRecoveryChoice;
    switch (choice) {
    case Choice::ProceedWithoutIgnore:
        return QStringLiteral("proceed-without-ignore");
    case Choice::ResetToDefault:
        return QStringLiteral("reset-to-default");
    case Choice::Cancel:
        return QStringLiteral("cancel");
    }
    throw RunnerError("unknown Local Ignore recovery choice");
}

/// Builds the bridged recovery prompt used to exercise projection and GUI-thread interaction.
classic::gui::ScanRunLocalIgnoreRecoveryPresentation recoveryPresentation()
{
    scanner::ScanRunContractExecutionResult execution{};
    execution.has_result = true;
    execution.result.status = scanner::ScanRunContractStatus::LocalIgnoreRecoveryRequired;
    execution.has_recovery_prompt = true;

    scanner::ScanRunDisplayLine runLine{};
    runLine.severity = scanner::ScanRunDisplaySeverity::Warning;
    runLine.segments.push_back(displaySegment(scanner::ScanRunDisplaySegmentKind::Text, "receipt recovery run"));
    execution.display_lines.push_back(std::move(runLine));

    scanner::ScanRunDisplayLine promptLine{};
    promptLine.severity = scanner::ScanRunDisplaySeverity::Warning;
    promptLine.segments.push_back(displaySegment(scanner::ScanRunDisplaySegmentKind::Text, "receipt recovery prompt"));
    execution.recovery_prompt.lines.push_back(std::move(promptLine));

    scanner::ScanRunRecoveryDecisionDescription proceed{};
    proceed.decision = scanner::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore;
    proceed.label = "Proceed Without Ignore";
    proceed.description.push_back(
        displaySegment(scanner::ScanRunDisplaySegmentKind::Text, "continue without Local Ignore YAML Data"));
    proceed.available = true;
    execution.recovery_prompt.decisions.push_back(std::move(proceed));

    scanner::ScanRunRecoveryDecisionDescription reset{};
    reset.decision = scanner::ScanRunLocalIgnoreRecoveryDecision::ResetToDefault;
    reset.label = "Reset To Default";
    reset.description.push_back(
        displaySegment(scanner::ScanRunDisplaySegmentKind::Text, "replace Local Ignore YAML Data"));
    // Keep transported availability independent from the callback result so neither observation can
    // be inferred from the other.
    reset.available = false;
    execution.recovery_prompt.decisions.push_back(std::move(reset));

    const auto terminal = classic::gui::presentScanRunExecution(execution);
    if (!terminal.hasRecoveryPrompt) {
        throw RunnerError("Qt terminal projection dropped the Rust-owned recovery prompt");
    }
    return terminal.recoveryPrompt;
}

struct RecoveryDispatchObservation {
    bool callerThreadObserved = false;
    bool workerThreadObserved = false;
    bool promptDeliveredOnGuiThread = false;
    classic::gui::ScanRunLocalIgnoreRecoveryChoice selected = classic::gui::ScanRunLocalIgnoreRecoveryChoice::Cancel;
    classic::gui::ScanRunLocalIgnoreRecoveryPresentation delivered;
};

/// Dispatches one recovery request from a real worker thread through ScanController's GUI seam.
RecoveryDispatchObservation
observeRecoveryDispatch(const classic::gui::ScanRunLocalIgnoreRecoveryPresentation& recovery)
{
    using Choice = classic::gui::ScanRunLocalIgnoreRecoveryChoice;
    ScanController controller(nullptr, nullptr);
    QThread* const guiThread = QThread::currentThread();
    QThread* promptThread = nullptr;
    classic::gui::ScanRunLocalIgnoreRecoveryPresentation delivered;
    controller.setLocalIgnoreRecoveryPrompt(
        [&promptThread, &delivered](const classic::gui::ScanRunLocalIgnoreRecoveryPresentation& value) {
            promptThread = QThread::currentThread();
            delivered = value;
            return Choice::ResetToDefault;
        });
    const auto prompt = controller.makeLocalIgnoreRecoveryPrompt();

    RecoveryDispatchObservation observation;
    observation.callerThreadObserved = guiThread == QCoreApplication::instance()->thread();
    QThread worker;
    QObject context;
    context.moveToThread(&worker);
    QThread* requestThread = nullptr;
    QObject::connect(&worker, &QThread::started, &context, [&]() {
        requestThread = QThread::currentThread();
        observation.selected = prompt(recovery);
        worker.quit();
    });
    worker.start();

    // The launcher owns the outer timeout; keep pumping until the blocking invoke returns so the
    // QThread and its stack-capturing callback are never destroyed while still running.
    while (!worker.wait(10)) {
        QCoreApplication::processEvents(QEventLoop::AllEvents, 10);
    }
    observation.workerThreadObserved = requestThread != nullptr && requestThread != guiThread;
    observation.promptDeliveredOnGuiThread = promptThread == guiThread;
    observation.delivered = std::move(delivered);
    return observation;
}

/// Creates one serialized lifecycle event consumed by BatchProgressModel.
scanner::ScanRunContractEvent logEvent(scanner::ScanRunContractEventKind kind,
                                       scanner::ScanRunContractProgressPhase phase, std::size_t discoveryIndex,
                                       std::size_t completed, std::size_t total)
{
    scanner::ScanRunContractEvent event{};
    event.kind = kind;
    event.phase = phase;
    event.discovery_index = discoveryIndex;
    event.completed = completed;
    event.total = total;
    event.crash_log = "C:/CLASSIC/Crash Logs/crash.log";
    return event;
}

/// Observes typed Display Content before layout and the path link produced by Qt layout.
std::pair<QJsonObject, QJsonObject> observeDisplayContent()
{
    constexpr auto path = "C:/CLASSIC/Crash Logs/crash-AUTOSCAN.md";
    rust::Vec<scanner::ScanRunDisplayLine> lines;

    scanner::ScanRunDisplayLine contentLine{};
    contentLine.severity = scanner::ScanRunDisplaySeverity::Success;
    contentLine.segments.push_back(displaySegment(scanner::ScanRunDisplaySegmentKind::Text, "receipt sentinel"));
    contentLine.segments.push_back(displaySegment(scanner::ScanRunDisplaySegmentKind::Count, "sprockets", "", 12));
    contentLine.segments.push_back(displaySegment(scanner::ScanRunDisplaySegmentKind::Path, "", path));
    lines.push_back(std::move(contentLine));

    scanner::ScanRunDisplayLine pathLine{};
    pathLine.severity = scanner::ScanRunDisplaySeverity::Info;
    pathLine.segments.push_back(displaySegment(scanner::ScanRunDisplaySegmentKind::Path, "", path));
    lines.push_back(std::move(pathLine));

    const auto presented = classic::gui::presentScanRunDisplayLines(lines);
    if (presented.size() != 2 || presented[0].segments.size() != 3 || presented[1].segments.size() != 1) {
        throw RunnerError("Qt Display Content projection changed the supplied line or segment count");
    }

    QJsonArray segments;
    for (const auto& segment : presented[0].segments) {
        segments.append(QJsonObject{
            {QStringLiteral("kind"), segmentKindToken(segment.kind)},
            {QStringLiteral("text"), segment.text},
            {QStringLiteral("path"), segment.path},
            {QStringLiteral("count"), static_cast<qint64>(segment.count)},
        });
    }
    QJsonObject displayObservation{
        {QStringLiteral("severity"), severityToken(presented[0].severity)},
        {QStringLiteral("segments"), segments},
    };

    const QString plain = classic::gui::renderScanRunDisplayLineAsPlainText(presented[1]);
    const QString rich = classic::gui::renderScanRunDisplayLineAsRichText(presented[1]);
    const QRegularExpression anchorPattern(QStringLiteral("href=\"([^\"]+)\""));
    const auto anchorMatch = anchorPattern.match(rich);
    QJsonObject linkObservation{
        {QStringLiteral("segmentKind"), segmentKindToken(presented[1].segments[0].kind)},
        {QStringLiteral("path"), presented[1].segments[0].path},
        {QStringLiteral("plainText"), plain},
        {QStringLiteral("fileHref"), anchorMatch.hasMatch() ? anchorMatch.captured(1) : QString{}},
    };
    return {std::move(displayObservation), std::move(linkObservation)};
}

/// Observes serialized lifecycle events updating the maintained GUI progress model.
QJsonObject observeProgressModel()
{
    BatchProgressModel model;
    scanner::ScanRunContractEvent discovery{};
    discovery.kind = scanner::ScanRunContractEventKind::DiscoveryCompleted;
    discovery.discovery.accepted_logs.push_back("C:/CLASSIC/Crash Logs/one.log");
    discovery.discovery.accepted_logs.push_back("C:/CLASSIC/Crash Logs/two.log");

    scanner::ScanRunContractEvent concurrency{};
    concurrency.kind = scanner::ScanRunContractEventKind::EffectiveConcurrencySelected;
    concurrency.effective_concurrency = 1;

    QJsonArray progress;
    progress.append(static_cast<int>(std::lround(model.update(discovery))));
    model.update(concurrency);
    progress.append(static_cast<int>(std::lround(model.update(logEvent(
        scanner::ScanRunContractEventKind::LogStarted, scanner::ScanRunContractProgressPhase::Setup, 0, 0, 2)))));
    progress.append(static_cast<int>(std::lround(model.update(logEvent(
        scanner::ScanRunContractEventKind::LogPhase, scanner::ScanRunContractProgressPhase::Analyze, 0, 0, 2)))));
    progress.append(static_cast<int>(std::lround(model.update(logEvent(
        scanner::ScanRunContractEventKind::LogFinished, scanner::ScanRunContractProgressPhase::Finalize, 0, 1, 2)))));
    progress.append(static_cast<int>(std::lround(model.update(logEvent(
        scanner::ScanRunContractEventKind::LogFinished, scanner::ScanRunContractProgressPhase::Finalize, 1, 2, 2)))));

    return {
        {QStringLiteral("totalLogs"), model.totalLogs()},
        {QStringLiteral("effectiveConcurrency"), model.effectiveConcurrency()},
        {QStringLiteral("progress"), progress},
    };
}

/// Executes every GUI obligation probe once so profiles share the exact same Qt interaction.
QtConsumerObservations observeQtConsumerSeams()
{
    const auto [displayContent, pathLinks] = observeDisplayContent();
    const auto recovery = recoveryPresentation();
    const auto dispatch = observeRecoveryDispatch(recovery);

    QJsonArray decisionOrder;
    QJsonArray availability;
    for (const auto& decision : dispatch.delivered.decisions) {
        decisionOrder.append(recoveryDecisionToken(decision.decision));
        availability.append(decision.available);
    }

    QtConsumerObservations observations;
    observations.workerDispatch = {
        {QStringLiteral("callerThread"),
         dispatch.callerThreadObserved ? QStringLiteral("gui") : QStringLiteral("worker")},
        {QStringLiteral("workerThread"),
         dispatch.workerThreadObserved ? QStringLiteral("worker") : QStringLiteral("gui")},
        {QStringLiteral("deliveryThread"),
         dispatch.promptDeliveredOnGuiThread ? QStringLiteral("gui") : QStringLiteral("worker")},
        {QStringLiteral("returnedChoice"), recoveryChoiceToken(dispatch.selected)},
    };
    observations.pathLinks = pathLinks;
    observations.recoveryInteraction = {
        {QStringLiteral("decisionOrder"), decisionOrder},
        {QStringLiteral("availability"), availability},
        {QStringLiteral("selected"), recoveryChoiceToken(dispatch.selected)},
        {QStringLiteral("promptThread"),
         dispatch.promptDeliveredOnGuiThread ? QStringLiteral("gui") : QStringLiteral("worker")},
    };
    observations.modelUpdates = observeProgressModel();
    observations.displayContentDelivery = displayContent;
    return observations;
}

/// Selects the actual observation produced for one source-owned GUI obligation.
QJsonObject obligationObservation(const QString& id, const QtConsumerObservations& observations)
{
    if (id == QStringLiteral("gui.worker-dispatch")) {
        return observations.workerDispatch;
    }
    if (id == QStringLiteral("gui.path-links")) {
        return observations.pathLinks;
    }
    if (id == QStringLiteral("gui.recovery-interaction")) {
        return observations.recoveryInteraction;
    }
    if (id == QStringLiteral("gui.model-updates")) {
        return observations.modelUpdates;
    }
    if (id == QStringLiteral("gui.display-content-delivery")) {
        return observations.displayContentDelivery;
    }
    throw RunnerError(QStringLiteral("unknown GUI consumer obligation: %1").arg(id).toStdString());
}

/// Builds one obligation receipt after validating the plan-owned scenario denominator.
QJsonObject obligationReceipt(const QJsonObject& obligation, const QtConsumerObservations& observations)
{
    const QString id = obligation.value(QStringLiteral("id")).toString();
    const QJsonArray scenarioIds = requiredArray(obligation, QStringLiteral("scenarioIds"));
    if (id.isEmpty() || scenarioIds.isEmpty()) {
        throw RunnerError("consumer obligation must have an id and at least one scenario");
    }
    try {
        return {
            {QStringLiteral("id"), id},
            {QStringLiteral("executionStatus"), QStringLiteral("completed")},
            {QStringLiteral("observation"), obligationObservation(id, observations)},
            {QStringLiteral("failure"), QJsonValue::Null},
        };
    } catch (const std::exception& error) {
        return {
            {QStringLiteral("id"), id},
            {QStringLiteral("executionStatus"), QStringLiteral("failed")},
            {QStringLiteral("observation"), QJsonObject{}},
            {QStringLiteral("failure"),
             QJsonObject{{QStringLiteral("kind"), QStringLiteral("consumer-obligation-failure")},
                         {QStringLiteral("message"), QString::fromUtf8(error.what())}}},
        };
    }
}

/// Builds the consumer receipt without scenario semantics or parity capability claims.
QJsonObject buildReceipt(const QJsonObject& plan)
{
    const auto participant = requiredObject(plan, QStringLiteral("participant"));
    const QString expectedInstance = QStringLiteral("windows-") + QStringLiteral(CLASSIC_GUI_CONFORMANCE_TOOLCHAIN);
    if (participant.value(QStringLiteral("id")).toString() != QStringLiteral("gui") ||
        participant.value(QStringLiteral("role")).toString() != QStringLiteral("consumer") ||
        participant.value(QStringLiteral("executionInstanceId")).toString() != expectedInstance) {
        throw RunnerError("run plan participant must match this GUI consumer toolchain");
    }

    const auto observations = observeQtConsumerSeams();
    QJsonArray obligations;
    for (const auto& value : requiredArray(plan, QStringLiteral("obligations"))) {
        if (!value.isObject()) {
            throw RunnerError("run plan obligations must contain only objects");
        }
        obligations.append(obligationReceipt(value.toObject(), observations));
    }
    if (obligations.isEmpty()) {
        throw RunnerError("GUI consumer run plan contains no obligations");
    }

    return {
        {QStringLiteral("schemaVersion"), plan.value(QStringLiteral("schemaVersion"))},
        {QStringLiteral("familyId"), plan.value(QStringLiteral("familyId"))},
        {QStringLiteral("familyVersion"), plan.value(QStringLiteral("familyVersion"))},
        {QStringLiteral("expectationDigest"), plan.value(QStringLiteral("expectationDigest"))},
        {QStringLiteral("invocation"), requiredObject(plan, QStringLiteral("invocation"))},
        {QStringLiteral("participant"), participant},
        {QStringLiteral("runner"),
         QJsonObject{{QStringLiteral("id"), QString::fromUtf8(RUNNER_ID)},
                     {QStringLiteral("version"), 1},
                     {QStringLiteral("platform"), QStringLiteral("windows")},
                     {QStringLiteral("toolchain"), QStringLiteral(CLASSIC_GUI_CONFORMANCE_TOOLCHAIN)}}},
        {QStringLiteral("obligations"), obligations},
    };
}

} // namespace

/// Runs the source-bound GUI consumer probes or visibly skips when no prepared plan is present.
int main(int argc, char* argv[])
{
    QCoreApplication application(argc, argv);
    const QString runPlanValue = qEnvironmentVariable(RUN_PLAN_ENV);
    const QString outputValue = qEnvironmentVariable(OUTPUT_ENV);
    if (runPlanValue.isEmpty() || outputValue.isEmpty()) {
        std::cout << "SKIP: " << RUN_PLAN_ENV << " and " << OUTPUT_ENV
                  << " are required for GUI consumer conformance\n";
        return SKIP_RETURN_CODE;
    }

    try {
        const QString runPlanPath = QDir::cleanPath(runPlanValue);
        const QString outputPath = QDir::cleanPath(outputValue);
        if (!QFileInfo(runPlanPath).isAbsolute() || !QFileInfo(outputPath).isAbsolute() ||
            QFileInfo(runPlanPath).absolutePath() != QFileInfo(outputPath).absolutePath()) {
            throw RunnerError("run plan and receipt must be absolute sibling paths");
        }
        if (QFileInfo::exists(outputPath)) {
            throw RunnerError("reserved GUI consumer receipt path already exists");
        }
        publishReceipt(outputPath, buildReceipt(readJsonObject(runPlanPath)));
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "GUI consumer conformance failed: " << error.what() << '\n';
        return 1;
    }
}
