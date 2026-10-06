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
#include <QTemporaryDir>

#include "controllers/scancontroller.h"
#include "core/guiusersettings.h"
#include "core/rust_qt_bridge.h"
#include "workers/scanlaunch.h"
#include "workers/scanprogressmodel.h"
#include "workers/scanrunpresentation.h"
#include "workers/scanworker.h"

#include <cmath>
#include <exception>
#include <iostream>
#include <optional>
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

/// Maps one settle scenario identity onto the answer the GUI-thread prompt gives in this profile.
classic::gui::ScanRunLocalIgnoreRecoveryChoice settlementChoice(const QString& scenarioId)
{
    using Choice = classic::gui::ScanRunLocalIgnoreRecoveryChoice;
    if (scenarioId == QStringLiteral("settle-proceed-without-ignore")) {
        return Choice::ProceedWithoutIgnore;
    }
    if (scenarioId == QStringLiteral("settle-reset-to-default")) {
        return Choice::ResetToDefault;
    }
    if (scenarioId == QStringLiteral("settle-without-decision")) {
        return Choice::Cancel;
    }
    throw RunnerError(QStringLiteral("unsupported GUI recovery settlement scenario: %1").arg(scenarioId).toStdString());
}

/// Returns the decision Rust applied when it settled the run, read from the settled Local Ignore state.
///
/// The settled run reports which recovery it carried out, so this is what the worker passed to
/// settling as Rust saw it, not what the prompt claims it returned. A run settled with no decision
/// still reports the recovery as required, which reads back as JSON null.
QJsonValue settledDecisionToken(const classic::gui::ScanRunInstalledYamlDataPresentation& settled)
{
    using State = scanner::ScanRunLocalIgnoreYamlDataState;
    switch (settled.localIgnoreState) {
    case State::ProceedWithoutIgnore:
        return QStringLiteral("proceed-without-ignore");
    case State::ResetToDefault:
        return QStringLiteral("reset-to-default");
    case State::RecoveryRequired:
        return QJsonValue::Null;
    case State::Existing:
    case State::Generated:
        break;
    }
    // A malformed Local Ignore file is never Existing or Generated, so this is a profile failure.
    throw RunnerError("GUI recovery settlement reported a Local Ignore state no settlement produces");
}

/// Copies one launcher-declared crash-log-scan-run fixture into an isolated installation root.
void copyPlanFixture(const QJsonObject& plan, const QString& fixtureRef, const QString& destination)
{
    const auto fixtures = requiredObject(plan, QStringLiteral("fixtures"));
    const QString source = fixtures.value(fixtureRef).toString();
    if (source.isEmpty() || !QDir().mkpath(QFileInfo(destination).absolutePath()) ||
        !QFile::copy(source, destination)) {
        throw RunnerError(QStringLiteral("GUI recovery profile cannot stage fixture %1").arg(fixtureRef).toStdString());
    }
}

/// Runs one real paused scan on a worker thread and observes how the GUI settles it.
///
/// The `ScanWorker` executes on its own thread and is handed the controller's marshalled prompt, so
/// the answer is chosen on the GUI thread through the shipped `BlockingQueuedConnection` and the
/// settlement happens back on the worker thread, exactly as a user-driven scan does.
QJsonObject observeRecoverySettlement(const QJsonObject& plan, const QString& scenarioId)
{
    QTemporaryDir root;
    if (!root.isValid()) {
        throw RunnerError("cannot create GUI recovery installation root");
    }
    copyPlanFixture(plan, QStringLiteral("mainYaml"),
                    root.filePath(QStringLiteral("CLASSIC Data/databases/CLASSIC Main.yaml")));
    copyPlanFixture(plan, QStringLiteral("gameYaml"),
                    root.filePath(QStringLiteral("CLASSIC Data/databases/CLASSIC Fallout4.yaml")));
    copyPlanFixture(plan, QStringLiteral("malformedLocalIgnoreYaml"),
                    root.filePath(QStringLiteral("CLASSIC Data/CLASSIC Ignore.yaml")));
    const QString crashLog = root.filePath(scenarioId + QStringLiteral(".log"));
    copyPlanFixture(plan, QStringLiteral("validCrashLog"), crashLog);

    const auto choice = settlementChoice(scenarioId);
    ScanController controller(nullptr, nullptr);
    QThread* const guiThread = QThread::currentThread();
    QThread* promptThread = nullptr;
    classic::gui::ScanRunLocalIgnoreRecoveryChoice selected = classic::gui::ScanRunLocalIgnoreRecoveryChoice::Cancel;
    controller.setLocalIgnoreRecoveryPrompt(
        [&promptThread, &selected, choice](const classic::gui::ScanRunLocalIgnoreRecoveryPresentation&) {
            promptThread = QThread::currentThread();
            selected = choice;
            return choice;
        });
    const auto prompt = controller.makeLocalIgnoreRecoveryPrompt();

    // No User Settings document is staged: Crash Log Scan Launch reads the defaults (Fallout 4,
    // game version auto), which is the game the staged YAML Data describes.

    // Everything below is written on the worker thread and read here only after it has finished.
    std::optional<classic::gui::ScanRunInstalledYamlDataPresentation> settled;
    QString terminal = QStringLiteral("none");
    QThread workerThread;
    QObject context;
    context.moveToThread(&workerThread);
    QObject::connect(&workerThread, &QThread::started, &context, [&]() {
        // Constructed on the worker thread so the worker and its signals never change affinity.
        ScanWorker worker(prompt);
        QObject::connect(
            &worker, &ScanWorker::installedYamlDataResolved,
            [&settled](const classic::gui::ScanRunInstalledYamlDataPresentation& installed) { settled = installed; });
        QObject::connect(&worker, &ScanWorker::finished,
                         [&terminal](int, int, int, const QString&) { terminal = QStringLiteral("completed"); });
        QObject::connect(&worker, &ScanWorker::cancelled,
                         [&terminal](const QString&) { terminal = QStringLiteral("cancelled"); });
        QObject::connect(&worker, &ScanWorker::noLogsFound,
                         [&terminal](const QString&) { terminal = QStringLiteral("no-crash-logs-found"); });
        QObject::connect(&worker, &ScanWorker::error,
                         [&terminal](const QString&) { terminal = QStringLiteral("error"); });
        worker.doScan(root.path(), {crashLog});
        workerThread.quit();
    });
    workerThread.start();
    // The launcher owns the outer timeout; keep pumping so the blocking prompt invoke can return.
    while (!workerThread.wait(10)) {
        QCoreApplication::processEvents(QEventLoop::AllEvents, 10);
    }

    if (!settled.has_value()) {
        throw RunnerError("GUI recovery settlement published no Installed YAML Data");
    }
    return {
        {QStringLiteral("scenarioId"), scenarioId},
        {QStringLiteral("selected"), recoveryChoiceToken(selected)},
        {QStringLiteral("promptThread"),
         promptThread == nullptr ? QStringLiteral("none")
                                 : (promptThread == guiThread ? QStringLiteral("gui") : QStringLiteral("worker"))},
        {QStringLiteral("settledDecision"), settledDecisionToken(*settled)},
        {QStringLiteral("terminal"), terminal},
    };
}

/// Observes one real settlement per scenario the recovery obligation names, in catalog order.
QJsonArray observeRecoverySettlements(const QJsonObject& plan, const QJsonArray& scenarioIds)
{
    QJsonArray settlements;
    for (const auto& scenarioId : scenarioIds) {
        settlements.append(observeRecoverySettlement(plan, scenarioId.toString()));
    }
    return settlements;
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

/// Reads exact persisted bytes for non-mutation and unknown-entry observations.
QByteArray settingsBytes(const QString& path)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) {
        throw RunnerError("cannot read GUI settings observation");
    }
    return file.readAll();
}

/// Observes the maintained Qt settings adapter through actual opens, saves, and transitions.
QJsonObject settingsObservation(const QJsonObject& plan, const QJsonObject& obligation)
{
    using namespace classic::gui;
    QTemporaryDir temporary;
    if (!temporary.isValid()) {
        throw RunnerError("cannot create GUI settings root");
    }
    const QString root = temporary.path();
    const QString path = root + QStringLiteral("/CLASSIC Settings.yaml");
    const auto fixtures = requiredObject(plan, QStringLiteral("fixtures"));
    const QString id = obligation.value(QStringLiteral("id")).toString();
    if (id == QStringLiteral("gui.settings-scan-projection")) {
        if (!QFile::copy(fixtures.value(QStringLiteral("canonical_current_nested")).toString(), path)) {
            throw RunnerError("cannot copy canonical GUI settings fixture");
        }
        const auto before = settingsBytes(path);
        const auto snapshot = GuiUserSettings::open(root);
        const QString game = QStringLiteral("Fallout4");
        const bool unchanged = before == settingsBytes(path);

        // Crash Log Scan Launch reads the saved scan values itself (`gui.scan-launch` observes
        // that); the GUI still projects them for the Settings dialog, which lists the managed
        // game's Rust-selected rows. A Fallout 4 VR user's rows are observed the same way rather
        // than by naming the VR key here.
        if (!QFile::remove(path)
            || !QFile::copy(fixtures.value(QStringLiteral("vr_shared_and_legacy_formid_databases")).toString(),
                            path)) {
            throw RunnerError("cannot copy Fallout 4 VR GUI settings fixture");
        }
        const auto vrBefore = settingsBytes(path);
        const auto vrSnapshot = GuiUserSettings::open(root);
        const QString vrGame = vrSnapshot.gameSetup.managedGame;
        const QJsonObject fallout4Vr{
            {"game", vrGame},
            {"formIdDatabasePaths", QJsonArray::fromStringList(vrSnapshot.scan.scanFormIdDatabases.value(vrGame))},
            {"unchanged", vrBefore == settingsBytes(path)}};
        return {{"classification", snapshot.classification}, {"updateCheck", snapshot.update.updateCheck},
                {"game", game}, {"gameVersion", snapshot.scan.gameVersion},
                {"formIdDatabasePaths", QJsonArray::fromStringList(snapshot.scan.scanFormIdDatabases.value(game))},
                {"unchanged", unchanged}, {"fallout4Vr", fallout4Vr}};
    }
    if (id == QStringLiteral("gui.settings-explicit-bootstrap")) {
        GuiUserSettings::open(root);
        const bool readCreatedFile = QFile::exists(path);
        GuiUserSettingsChanges changes;
        changes.fcxMode = true;
        changes.autoSwitchAfterScan = false;
        const auto committed = GuiUserSettings::bootstrap(root, changes);
        const auto snapshot = GuiUserSettings::open(root);
        return {{"readCreatedFile", readCreatedFile}, {"status", committed.status},
                {"classification", snapshot.classification}, {"fcxMode", snapshot.scan.fcxMode},
                {"autoSwitchAfterScan", snapshot.frontend.autoSwitchAfterScan}};
    }
    if (id == QStringLiteral("gui.settings-revision-and-geometry")) {
        if (!QFile::copy(fixtures.value(QStringLiteral("unknown_entries")).toString(), path)) {
            throw RunnerError("cannot copy GUI unknown-entry fixture");
        }
        const auto initial = GuiUserSettings::open(root);
        GuiUserSettingsChanges changes;
        changes.updateCheck = false;
        const auto committed = GuiUserSettings::commit(root, initial.revision, changes);
        changes.updateCheck = true;
        const auto stale = GuiUserSettings::commit(root, initial.revision, changes);
        auto snapshot = GuiUserSettings::open(root);
        const auto geometry = GuiUserSettings::commitFrontendTransition(
            root, snapshot, GuiWindowGeometryChange{GuiWindow::Main, GuiWindowGeometry{false, 940, 710}});
        const auto reopened = GuiUserSettings::open(root);
        const auto window = reopened.frontend.windowGeometry.value(GuiWindow::Main);
        return {{"status", committed.status}, {"staleStatus", stale.status},
                {"updateCheck", reopened.update.updateCheck},
                {"unknownRetained", settingsBytes(path).contains("ThirdPartyPlugin")},
                {"geometryStatus", geometry.status}, {"width", window.width}, {"height", window.height},
                {"snapshotRefreshed", snapshot.revision == reopened.revision && snapshot.revision != committed.revision}};
    }
    throw RunnerError("unknown GUI User Settings obligation");
}

/// One Crash Log Scan Launch scenario as the GUI drives it: the saved settings and the intent.
struct GuiLaunchScenario {
    QString settingsFixtureRef;
    QStringList targetedInputs;
};

/// Maps one launch scenario identity onto what the GUI does in this profile.
///
/// The plan carries no scenario semantics, so the GUI side of each scenario is restated here: which
/// saved settings the user has, and whether they dropped Crash Logs on the window (Targeted) or
/// pressed the scan button with none (Standard). The GUI supplies no per-run overrides.
GuiLaunchScenario launchScenario(const QString& scenarioId)
{
    if (scenarioId == QStringLiteral("managed-game-saved-values")) {
        return {QStringLiteral("managed-fallout4"), {}};
    }
    if (scenarioId == QStringLiteral("targeted-scans-exactly-its-inputs")) {
        return {QStringLiteral("managed-fallout4"), {QStringLiteral("b.log"), QStringLiteral("a folder")}};
    }
    if (scenarioId == QStringLiteral("fcx-missing-setup-folders-still-launch")) {
        return {QStringLiteral("fcx-saved-setup"), {}};
    }
    if (scenarioId == QStringLiteral("malformed-settings-launch-from-defaults")) {
        return {QStringLiteral("malformed"), {}};
    }
    throw RunnerError(QStringLiteral("unsupported GUI launch scenario: %1").arg(scenarioId).toStdString());
}

/// Writes one launch settings fixture as the Installation Root's User Settings document.
///
/// Fixtures name the Installation Root through a placeholder every launch runner fills, because the
/// saved FCX folders are absolute paths beneath a root that only exists for this run.
void stageLaunchSettings(const QJsonObject& plan, const QString& fixtureRef, const QString& root)
{
    const auto fixtures = requiredObject(plan, QStringLiteral("fixtures"));
    QFile source(fixtures.value(fixtureRef).toString());
    if (!source.open(QIODevice::ReadOnly)) {
        throw RunnerError(QStringLiteral("GUI launch profile cannot read fixture %1").arg(fixtureRef).toStdString());
    }
    QByteArray document = source.readAll();
    document.replace("{{installationRoot}}", root.toUtf8());
    QSaveFile settings(QDir(root).filePath(QStringLiteral("CLASSIC Settings.yaml")));
    if (!settings.open(QIODevice::WriteOnly) || settings.write(document) != document.size() || !settings.commit()) {
        throw RunnerError(QStringLiteral("GUI launch profile cannot stage fixture %1").arg(fixtureRef).toStdString());
    }
}

/// Returns `path` relative to the Installation Root, with the root itself reading as `.`.
QJsonValue rootRelative(const QString& root, const rust::String& path)
{
    const QString cleaned = QDir::cleanPath(classic::toQString(path));
    if (cleaned.compare(QDir::cleanPath(root), Qt::CaseInsensitive) == 0) {
        return QStringLiteral(".");
    }
    return QDir(root).relativeFilePath(cleaned);
}

/// Launches one scenario exactly as `ScanWorker::doScan` does and observes what the GUI got back.
///
/// The observation is the launched request's shape as the GUI consumes it: that a Standard scan's
/// base folder is the Installation Root, that dropped inputs become a Targeted intent in order,
/// that FCX Mode with missing saved folders still launches (the setup problem is the run's to
/// report, not a refusal here), and how many Rust-rendered warning lines the user is shown.
QJsonObject observeLaunch(const QJsonObject& plan, const QString& scenarioId)
{
    QTemporaryDir temporary;
    if (!temporary.isValid()) {
        throw RunnerError("cannot create GUI launch Installation Root");
    }
    const QString root = temporary.path();
    const auto scenario = launchScenario(scenarioId);
    stageLaunchSettings(plan, scenario.settingsFixtureRef, root);
    QStringList inputs;
    for (const auto& input : scenario.targetedInputs) {
        inputs.append(QDir(root).filePath(input));
    }

    const auto launch = classic::gui::launchScanRun(root, inputs);
    const auto error = scanner::scan_run_launch_error(*launch);
    if (error.has_error) {
        return {{QStringLiteral("scenarioId"), scenarioId}, {QStringLiteral("outcome"), QStringLiteral("error")}};
    }
    const auto view = scanner::scan_run_launch_view(*launch);
    const bool standard = view.intent == scanner::ScanRunLaunchIntent::Standard;

    QJsonValue targetedInputs = QJsonValue::Null;
    if (!standard) {
        QJsonArray relative;
        for (const auto& input : view.targeted_source.inputs) {
            relative.append(rootRelative(root, input));
        }
        targetedInputs = relative;
    }
    QJsonValue setupFolders = QJsonValue::Null;
    if (view.fcx_enabled) {
        const auto& setup = view.setup_context;
        setupFolders = QJsonObject{
            {QStringLiteral("gameRoot"), setup.has_game_root ? rootRelative(root, setup.game_root) : QJsonValue::Null},
            {QStringLiteral("docsRoot"), setup.has_docs_root ? rootRelative(root, setup.docs_root) : QJsonValue::Null},
            {QStringLiteral("gameRootExists"),
             setup.has_game_root && QFileInfo(classic::toQString(setup.game_root)).isDir()},
            {QStringLiteral("docsRootExists"),
             setup.has_docs_root && QFileInfo(classic::toQString(setup.docs_root)).isDir()},
        };
    }

    const auto warningLines = classic::gui::presentScanRunDisplayLines(view.display_lines).size();
    if ((warningLines == 0) != classic::gui::formatScanRunLaunchWarning(view).isEmpty()) {
        throw RunnerError("GUI launch warning disagrees with the launch's rendered diagnostics");
    }
    return {
        {QStringLiteral("scenarioId"), scenarioId},
        {QStringLiteral("outcome"), QStringLiteral("launched")},
        {QStringLiteral("intent"), standard ? QStringLiteral("standard") : QStringLiteral("targeted")},
        {QStringLiteral("baseDirectory"),
         standard ? rootRelative(root, view.standard_source.base_directory) : QJsonValue::Null},
        {QStringLiteral("targetedInputs"), targetedInputs},
        {QStringLiteral("fcxEnabled"), view.fcx_enabled},
        {QStringLiteral("setupFolders"), setupFolders},
        {QStringLiteral("warningLines"), static_cast<qint64>(warningLines)},
    };
}

/// Observes the GUI Crash Log Scan Launch obligation, one launch per scenario in catalog order.
QJsonObject launchObservation(const QJsonObject& plan, const QJsonObject& obligation)
{
    if (obligation.value(QStringLiteral("id")).toString() != QStringLiteral("gui.scan-launch")) {
        throw RunnerError("unknown GUI Crash Log Scan Launch obligation");
    }
    QJsonArray launches;
    for (const auto& scenarioId : requiredArray(obligation, QStringLiteral("scenarioIds"))) {
        launches.append(observeLaunch(plan, scenarioId.toString()));
    }
    return {{QStringLiteral("launches"), launches}};
}

/// Builds one obligation receipt after validating the plan-owned scenario denominator.
QJsonObject obligationReceipt(const QJsonObject& plan, const QJsonObject& obligation,
                              const QtConsumerObservations& observations)
{
    const QString id = obligation.value(QStringLiteral("id")).toString();
    const QJsonArray scenarioIds = requiredArray(obligation, QStringLiteral("scenarioIds"));
    if (id.isEmpty() || scenarioIds.isEmpty()) {
        throw RunnerError("consumer obligation must have an id and at least one scenario");
    }
    try {
        const QString family = plan.value(QStringLiteral("familyId")).toString();
        QJsonObject observation = family == QStringLiteral("user-settings")
                                      ? settingsObservation(plan, obligation)
                                  : family == QStringLiteral("crash-log-scan-launch")
                                      ? launchObservation(plan, obligation)
                                      : obligationObservation(id, observations);
        if (id == QStringLiteral("gui.recovery-interaction")) {
            // The prompt choice is observed where it lands: in a real run the worker settles.
            observation.insert(QStringLiteral("settlements"), observeRecoverySettlements(plan, scenarioIds));
        }
        return {
            {QStringLiteral("id"), id},
            {QStringLiteral("executionStatus"), QStringLiteral("completed")},
            {QStringLiteral("observation"), observation},
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

    const auto family = plan.value(QStringLiteral("familyId")).toString();
    if ((family != QStringLiteral("crash-log-scan-run") && family != QStringLiteral("user-settings") &&
         family != QStringLiteral("crash-log-scan-launch")) ||
        plan.contains(QStringLiteral("scenarios")) || plan.contains(QStringLiteral("expected"))) {
        throw RunnerError("unsupported GUI consumer family or semantic input");
    }
    const auto observations = family == QStringLiteral("crash-log-scan-run")
        ? observeQtConsumerSeams() : QtConsumerObservations{};
    QJsonArray obligations;
    for (const auto& value : requiredArray(plan, QStringLiteral("obligations"))) {
        if (!value.isObject()) {
            throw RunnerError("run plan obligations must contain only objects");
        }
        obligations.append(obligationReceipt(plan, value.toObject(), observations));
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
