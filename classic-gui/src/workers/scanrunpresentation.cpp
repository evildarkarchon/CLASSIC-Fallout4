#include "scanrunpresentation.h"

#include "core/rust_qt_bridge.h"

#include <QDir>
#include <QFileInfo>
#include <QSet>
#include <QStringList>
#include <QUrl>

#include <algorithm>
#include <utility>

namespace classic::gui {

// The Rust core decides what a Crash Log Scan Run says; this file decides only
// how it looks.
//
// Two rounds of consolidation landed here. The first (#167) deleted six `switch`
// tables, one per rendered enum, that were this frontend's private copy of a
// vocabulary the CLI and the TUI each also kept. Six of this frontend's variant
// wordings were stale against the canonical form and the entire Qt suite stayed
// green over all six, because nothing asserted a label the three frontends
// disagreed about.
//
// The second round is this one. Labels were centralized but *sentences* were
// not, so the sentences drifted instead. Every sentence about a run now arrives
// already written, as an ordered sequence of `ScanRunDisplayLine` on the
// execution envelope and on every observed event, rendered by
// `classic-scan-presentation` while the Rust value was still live. What this
// file does with them is concatenate each line's segments in order and style
// them — a path becomes an actionable link, a severity becomes a colour, a
// count prints the noun Rust already agreed with its value.
//
// What that leaves behind, and why:
//
//   * Only two bridge label accessors survive, and both label a domain enum
//     *outside* a display line: `installedYamlDataStatusSuffix` in
//     `mainwindow.cpp` compresses the YAML Data selection into one status row
//     that has no room for the rendered block. Rendering a label there is still
//     correct; re-deriving one that a `Label` segment already carries is not.
//   * The four accessors that used to serve infrastructure errors, resume
//     errors, per-log failures, and Installed YAML Data diagnostics are gone,
//     because every one of those labels now reaches the user inside the line
//     that carries it. `tests/test_display_label_audit.cpp` asserts their
//     *absence*, so a contributor who reaches for one is told where the label
//     already lives.
//   * Per-log disposition stays unlabelled here, as it has since #167.
//     `presentLog` below maps the three variants onto booleans that select
//     control flow and feed counts; the disposition a user reads arrives inside
//     the rendered per-log line instead.
//   * The FCX Mode setup projection keeps its `Display`-based rendering. Its
//     four types have not adopted the shared vocabulary, so the presentation
//     crate deliberately does not render it, and this frontend groups those
//     lines in after the rendered ones rather than splicing into a flat sequence
//     by guessing an index.
//
// That audit is what stops any of this growing back. It reads this file as
// text, so it catches shapes the compiler cannot object to.

namespace {

QString setupDetails(const classic::scanner::ScanRunContractRunResult& result)
{
    QStringList lines;
    if (!result.has_setup) {
        return {};
    }

    lines.append(QStringLiteral("FCX setup: %1").arg(classic::toQString(result.setup.status)));
    if (result.setup.has_message) {
        lines.append(classic::toQString(result.setup.message));
    }
    if (!result.setup.rendered_report.empty()) {
        lines.append(classic::toQString(result.setup.rendered_report));
    }
    for (const auto& check : result.setup.checks) {
        lines.append(QStringLiteral("[%1] %2: %3")
                         .arg(classic::toQString(check.state), classic::toQString(check.kind),
                              classic::toQString(check.message)));
        for (const auto& detail : check.details) {
            lines.append(QStringLiteral("  %1").arg(classic::toQString(detail)));
        }
    }
    for (const auto& update : result.setup.path_updates) {
        lines.append(QStringLiteral("Proposed %1 path: %2")
                         .arg(classic::toQString(update.kind), classic::toQString(update.path)));
    }
    for (const auto& issue : result.setup.configuration_issues) {
        const QString section =
            issue.has_section ? QStringLiteral("/[%1]").arg(classic::toQString(issue.section_or_empty)) : QString{};
        lines.append(QStringLiteral("[%1] %2%3 %4: %5 (current: %6, recommended: %7)")
                         .arg(classic::toQString(issue.severity), classic::toQString(issue.file_path), section,
                              classic::toQString(issue.setting), classic::toQString(issue.description),
                              classic::toQString(issue.current_value), classic::toQString(issue.recommended_value)));
    }
    for (const auto& action : result.setup.actions) {
        lines.append(QStringLiteral("Action: %1").arg(classic::toQString(action)));
    }
    for (const auto& error : result.setup.fatal_errors) {
        lines.append(QStringLiteral("Setup error: %1").arg(classic::toQString(error)));
    }
    return lines.join('\n');
}

ScanRunLogPresentation presentLog(const classic::scanner::ScanRunContractLogResult& log)
{
    ScanRunLogPresentation presentation;
    presentation.discoveryIndex = static_cast<int>(log.discovery_index);
    presentation.crashLog = classic::toQString(log.crash_log);
    if (log.has_autoscan_report) {
        presentation.autoscanReport = classic::toQString(log.autoscan_report);
    }
    presentation.message = log.has_message ? classic::toQString(log.message) : QString{};
    presentation.movedToUnsolvedLogs = log.moved_to_unsolved_logs;

    // Booleans rather than a Display Label, decided on #167 and kept deliberately. The bridge does
    // expose `scan_run_log_disposition_label` — but every GUI consumer of this field reads it as
    // control flow or as a count, not as prose: `cancelledBeforeStart` selects whether the log is
    // reported at all, `succeeded` crosses a signal as a bool, and the aggregate reaches the user as
    // three integers. The disposition a user actually reads arrives inside the rendered per-log
    // line, so labelling it again here would be a second copy of the same word.
    using Disposition = classic::scanner::ScanRunContractLogDisposition;
    switch (log.disposition) {
    case Disposition::Succeeded:
        presentation.succeeded = true;
        break;
    case Disposition::Failed:
        presentation.failed = true;
        break;
    case Disposition::CancelledBeforeStart:
        presentation.cancelledBeforeStart = true;
        break;
    }

    // Structured per-log failures are deliberately not projected into strings. Rust renders each one
    // as its own display line beneath the log's outcome, so a `<stage>: <message>` list built here
    // would be the same sentence written twice in two places able to disagree.
    return presentation;
}

/// Projects one exact selected YAML Data file into Qt-owned strings and scalar metadata.
ScanRunInstalledYamlDataFilePresentation presentInstalledYamlDataFile(
    const classic::scanner::ScanRunInspectedYamlDataFileDto& file)
{
    ScanRunInstalledYamlDataFilePresentation presentation;
    presentation.role = file.role;
    presentation.provenance = file.provenance;
    presentation.schemaVersion = classic::toQString(file.schema_version);
    presentation.sha256 = classic::toQString(file.sha256);
    presentation.byteLength = file.byte_len;
    return presentation;
}

/// Projects Installed YAML Data run metadata without flattening diagnostic presence flags.
ScanRunInstalledYamlDataPresentation presentInstalledYamlData(
    const classic::scanner::ScanRunInstalledYamlDataRunDataDto& installed)
{
    ScanRunInstalledYamlDataPresentation presentation;
    presentation.main = presentInstalledYamlDataFile(installed.main);
    presentation.gameFile = presentInstalledYamlDataFile(installed.game_file);
    presentation.localIgnoreState = installed.local_ignore_state;
    presentation.localIgnoreIdentity.sha256 = classic::toQString(installed.local_ignore_identity.sha256);
    presentation.localIgnoreIdentity.byteLength = installed.local_ignore_identity.byte_len;
    presentation.localIgnoreResetAvailable = installed.local_ignore_reset_available;
    presentation.hasLocalIgnoreReset = installed.has_local_ignore_reset;
    if (installed.has_local_ignore_reset) {
        const auto& reset = installed.local_ignore_reset;
        presentation.localIgnoreReset.localIgnorePath = classic::toQString(reset.local_ignore_path);
        presentation.localIgnoreReset.backupPath = classic::toQString(reset.backup_path);
        presentation.localIgnoreReset.malformedIdentity.sha256 = classic::toQString(reset.malformed_identity.sha256);
        presentation.localIgnoreReset.malformedIdentity.byteLength = reset.malformed_identity.byte_len;
        presentation.localIgnoreReset.backupIdentity.sha256 = classic::toQString(reset.backup_identity.sha256);
        presentation.localIgnoreReset.backupIdentity.byteLength = reset.backup_identity.byte_len;
        presentation.localIgnoreReset.replacementIdentity.sha256 = classic::toQString(reset.replacement_identity.sha256);
        presentation.localIgnoreReset.replacementIdentity.byteLength = reset.replacement_identity.byte_len;
    }
    presentation.diagnostics.reserve(static_cast<qsizetype>(installed.diagnostics.size()));
    for (const auto& diagnostic : installed.diagnostics) {
        ScanRunInstalledYamlDataDiagnosticPresentation mapped;
        mapped.hasRole = diagnostic.has_role;
        mapped.role = diagnostic.role;
        mapped.hasCandidate = diagnostic.has_candidate;
        mapped.candidate = diagnostic.candidate;
        mapped.hasPath = diagnostic.has_path;
        mapped.path = diagnostic.has_path ? classic::toQString(diagnostic.path) : QString{};
        mapped.kind = diagnostic.kind;
        mapped.message = classic::toQString(diagnostic.message);
        presentation.diagnostics.append(std::move(mapped));
    }
    return presentation;
}

} // namespace

bool offersLocalIgnoreResetToDefault(const ScanRunTerminalPresentation& terminal)
{
    return !terminal.hasInstalledYamlData || terminal.installedYamlData.localIgnoreResetAvailable;
}

QString localIgnoreStateLabel(classic::scanner::ScanRunLocalIgnoreYamlDataState state)
{
    return classic::toQString(classic::scanner::scan_run_local_ignore_yaml_data_state_label(state));
}

QString installedYamlDataProvenanceLabel(classic::scanner::ScanRunInstalledYamlDataProvenance provenance)
{
    return classic::toQString(classic::scanner::scan_run_installed_yaml_data_provenance_label(provenance));
}

QVector<ScanRunDisplayLinePresentation> presentScanRunDisplayLines(
    const rust::Vec<classic::scanner::ScanRunDisplayLine>& lines)
{
    QVector<ScanRunDisplayLinePresentation> presented;
    presented.reserve(static_cast<qsizetype>(lines.size()));
    for (const auto& line : lines) {
        ScanRunDisplayLinePresentation mapped;
        mapped.severity = line.severity;
        mapped.segments.reserve(static_cast<qsizetype>(line.segments.size()));
        for (const auto& segment : line.segments) {
            ScanRunDisplaySegmentPresentation mappedSegment;
            mappedSegment.kind = segment.kind;
            mappedSegment.text = classic::toQString(segment.text);
            mappedSegment.path = classic::toQString(segment.path);
            mappedSegment.count = segment.count;
            mapped.segments.append(std::move(mappedSegment));
        }
        presented.append(std::move(mapped));
    }
    return presented;
}

QString scanRunSeverityColor(classic::scanner::ScanRunDisplaySeverity severity)
{
    // Values are the dark theme's own: the ordinary foreground for a neutral fact, the accent blue
    // the markdown viewer already links in, and warning/failure/success hues that read against
    // #2b2b2b. The Rust core names none of this — it says only how gravely a line should read.
    switch (severity) {
    case classic::scanner::ScanRunDisplaySeverity::Notice:
        return QStringLiteral("#5599dd");
    case classic::scanner::ScanRunDisplaySeverity::Warning:
        return QStringLiteral("#e8b339");
    case classic::scanner::ScanRunDisplaySeverity::Failure:
        return QStringLiteral("#ff6b6b");
    case classic::scanner::ScanRunDisplaySeverity::Success:
        return QStringLiteral("#52ff52");
    case classic::scanner::ScanRunDisplaySeverity::Info:
        break;
    }
    return QStringLiteral("#e0e0e0");
}

QString renderScanRunDisplayLineAsPlainText(const ScanRunDisplayLinePresentation& line)
{
    QStringList rendered;
    rendered.reserve(line.segments.size());
    for (const auto& segment : line.segments) {
        switch (segment.kind) {
        case classic::scanner::ScanRunDisplaySegmentKind::Count:
            // The value beside the noun Rust already resolved to agree with it. Re-deciding the
            // form here is what would let this frontend print "1 logs".
            rendered.append(QStringLiteral("%1 %2").arg(segment.count).arg(segment.text));
            continue;
        case classic::scanner::ScanRunDisplaySegmentKind::Path:
            // Whole and untruncated. Shortening is a layout choice this shape declines to make,
            // because plain text is what reaches log files and single-string sinks.
            rendered.append(segment.path);
            continue;
        case classic::scanner::ScanRunDisplaySegmentKind::Text:
        case classic::scanner::ScanRunDisplaySegmentKind::Label:
        case classic::scanner::ScanRunDisplaySegmentKind::Name:
        case classic::scanner::ScanRunDisplaySegmentKind::Emphasis:
            break;
        }
        // Dropped rather than joined, so a segment with an empty payload cannot open a line with a
        // stray space or double one inside it. No render path in `classic-scan-presentation` emits
        // an empty payload today; this keeps a future one from being a spacing bug rather than a
        // no-op. Ordering is unaffected — nothing is moved, only nothing is added.
        if (!segment.text.isEmpty()) {
            rendered.append(segment.text);
        }
    }
    return rendered.join(QLatin1Char(' '));
}

QString renderScanRunDisplayLinesAsPlainText(const QVector<ScanRunDisplayLinePresentation>& lines)
{
    QStringList rendered;
    rendered.reserve(lines.size());
    for (const auto& line : lines) {
        rendered.append(renderScanRunDisplayLineAsPlainText(line));
    }
    return rendered.join(QLatin1Char('\n'));
}

QString renderScanRunDisplayLineAsRichText(const ScanRunDisplayLinePresentation& line)
{
    QStringList rendered;
    rendered.reserve(line.segments.size());
    for (const auto& segment : line.segments) {
        switch (segment.kind) {
        case classic::scanner::ScanRunDisplaySegmentKind::Count:
            rendered.append(QStringLiteral("<b>%1</b> %2")
                                .arg(QString::number(segment.count), segment.text.toHtmlEscaped()));
            continue;
        case classic::scanner::ScanRunDisplaySegmentKind::Path: {
            // A `file:` anchor rather than escaped text, so the Autoscan Report a run just wrote is
            // one click away and the path is still selectable. The label stays the whole path: a
            // shortened one is not a path a user can copy into anything else.
            const QString href = QUrl::fromLocalFile(segment.path).toString(QUrl::FullyEncoded);
            rendered.append(QStringLiteral(R"(<a href="%1">%2</a>)")
                                .arg(href.toHtmlEscaped(), segment.path.toHtmlEscaped()));
            continue;
        }
        case classic::scanner::ScanRunDisplaySegmentKind::Emphasis:
            rendered.append(QStringLiteral("<i>%1</i>").arg(segment.text.toHtmlEscaped()));
            continue;
        case classic::scanner::ScanRunDisplaySegmentKind::Text:
        case classic::scanner::ScanRunDisplaySegmentKind::Label:
        case classic::scanner::ScanRunDisplaySegmentKind::Name:
            break;
        }
        // A `Label` is printed exactly as it arrived. Looking the wording up again through a bridge
        // accessor is what the adapter contract forbids, and what the display-label audit catches.
        // Empty payloads are dropped for the same reason as in the plain-text shape.
        if (!segment.text.isEmpty()) {
            rendered.append(segment.text.toHtmlEscaped());
        }
    }
    return QStringLiteral(R"(<span style="color:%1;">%2</span>)")
        .arg(scanRunSeverityColor(line.severity), rendered.join(QLatin1Char(' ')));
}

QString renderScanRunDisplayLinesAsRichText(const QVector<ScanRunDisplayLinePresentation>& lines)
{
    QStringList rendered;
    rendered.reserve(lines.size());
    for (const auto& line : lines) {
        rendered.append(renderScanRunDisplayLineAsRichText(line));
    }
    return rendered.join(QStringLiteral("<br>"));
}

QString formatInstalledYamlDataWarning(const ScanRunInstalledYamlDataPresentation& installedYamlData)
{
    if (installedYamlData.localIgnoreState == classic::scanner::ScanRunLocalIgnoreYamlDataState::RecoveryRequired) {
        // This is the pre-decision snapshot published while the run still awaits a recovery choice.
        // The choice dialog is that snapshot's presentation, so a warning here would double-report it
        // and would interrupt the user before they can answer.
        return {};
    }

    using State = classic::scanner::ScanRunLocalIgnoreYamlDataState;
    const bool localIgnoreWasDecided = installedYamlData.localIgnoreState == State::ProceedWithoutIgnore ||
                                       installedYamlData.localIgnoreState == State::ResetToDefault;

    // Two decisions come out of this pass, both of them Display Layout. Whether to interrupt the
    // user at all, and which diagnostics this dialog declines to restate.
    bool worthInterrupting = installedYamlData.hasLocalIgnoreReset;
    QSet<QString> withheldDiagnosticMessages;
    for (const auto& diagnostic : installedYamlData.diagnostics) {
        if (diagnostic.kind == classic::scanner::ScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreGenerated) {
            // Generating an absent Local Ignore file is an expected successful path, not a warning.
            withheldDiagnosticMessages.insert(diagnostic.message);
            continue;
        }
        if (localIgnoreWasDecided && !diagnostic.hasRole) {
            // Local Ignore diagnostics carry no Main/Game role, which is what distinguishes them
            // from selection fallback. The recovery dialog already showed this exact problem and the
            // user answered it, so restating it would warn about a resolved question. What the
            // answer did not cover — where the malformed bytes went — is stated by the durable
            // backup and replacement lines Rust renders beside it.
            withheldDiagnosticMessages.insert(diagnostic.message);
            continue;
        }
        worthInterrupting = true;
    }

    if (!worthInterrupting || installedYamlData.runDisplayLines.isEmpty()) {
        return {};
    }

    // Whole lines are omitted, which is what an adapter may do; nothing inside a kept line is
    // touched. A withheld line is recognised by the diagnostic message it carries as its `Emphasis`
    // payload — a value this frontend already holds a typed copy of, and compares rather than
    // parses. Matching a payload is deliberately not the same as matching prose: the message is the
    // run's own data, and nothing here reads or depends on the words around it.
    //
    // This does couple to *where* Rust puts that payload, which is the one assumption worth naming.
    // It is not an unpinned one: `installed_yaml_data_pins_a_diagnostic_line` in
    // `business-logic/classic-scan-presentation/src/lib_tests.rs` asserts the whole segment sequence
    // for a diagnostic line, message included, so moving the message out of `Emphasis` fails there
    // before it can silently stop this filter from matching. If that ever becomes a deliberate
    // change, this is the call site it has to reach.
    QVector<ScanRunDisplayLinePresentation> shown;
    shown.reserve(installedYamlData.runDisplayLines.size());
    for (const auto& line : installedYamlData.runDisplayLines) {
        const bool withheld = std::any_of(line.segments.cbegin(), line.segments.cend(), [&](const auto& segment) {
            return segment.kind == classic::scanner::ScanRunDisplaySegmentKind::Emphasis &&
                   withheldDiagnosticMessages.contains(segment.text);
        });
        if (!withheld) {
            shown.append(line);
        }
    }

    // The header is Display Layout and stays this frontend's. The body is the run's own words: the
    // Installed YAML Data block, the durable backup and replacement paths, and every diagnostic this
    // dialog has not already answered — rendered once by Rust, shown here with the paths actionable.
    return QStringLiteral("<b>CLASSIC could not use some of its installed YAML Data for this scan.</b><br><br>") +
           renderScanRunDisplayLinesAsRichText(shown);
}

QString formatScanRunRejections(const classic::scanner::ScanRunContractDiscoveryResult& discovery)
{
    if (discovery.rejected_inputs.empty()) {
        return {};
    }

    QStringList lines;
    const auto count = discovery.rejected_inputs.size();
    lines.append(QStringLiteral("Ignored %1 targeted input%2:").arg(count).arg(count == 1 ? "" : "s"));
    for (const auto& rejection : discovery.rejected_inputs) {
        lines.append(
            QStringLiteral("- %1 (%2)").arg(classic::toQString(rejection.path), classic::toQString(rejection.reason)));
    }
    return lines.join('\n');
}

QStringList scanRunReportDirectories(const classic::scanner::ScanRunContractDiscoveryResult& discovery)
{
    QStringList directories;
    QSet<QString> seen;
    for (const auto& accepted : discovery.accepted_logs) {
        const QString directory = QDir::cleanPath(QFileInfo(classic::toQString(accepted)).absolutePath());
        const QString key = directory.toLower();
        if (!directory.isEmpty() && !seen.contains(key)) {
            seen.insert(key);
            directories.append(directory);
        }
    }
    return directories;
}

ScanRunTerminalPresentation presentScanRunExecution(const classic::scanner::ScanRunContractExecutionResult& execution)
{
    ScanRunTerminalPresentation presentation;

    // One rendered block covers all three payloads. `scan_run_contract_execute` and
    // `scan_run_continuation_resume` return the same envelope, and `display_lines` describes
    // whichever of the result, the infrastructure error, or the resume error the presence flags
    // below select — so it is projected once, before anything branches on them.
    presentation.displayLines = presentScanRunDisplayLines(execution.display_lines);
    presentation.message = renderScanRunDisplayLinesAsPlainText(presentation.displayLines);
    presentation.richText = renderScanRunDisplayLinesAsRichText(presentation.displayLines);

    if (execution.has_error || execution.has_resume_error) {
        // Both failure envelopes land on one terminal kind, exactly as before. The machine-facing
        // distinction stays on `error` and `resume_error` for a consumer that wants it — including
        // `resume_error.code`, which the rendered sentences deliberately omit because a stable error
        // code is not what belongs in a sentence.
        presentation.kind = ScanRunTerminalKind::InfrastructureError;
        return presentation;
    }

    if (!execution.has_result) {
        presentation.kind = ScanRunTerminalKind::InfrastructureError;
        // Unreachable through the bridge, which always sets exactly one presence flag. Kept because
        // the alternative is a silent empty dialog, which reads to a user as the window losing the
        // run rather than as a run that produced nothing. This sentence reports a broken bridge
        // promise rather than anything a run said, so it stays this frontend's to write.
        presentation.message =
            QStringLiteral("Crash Log Scan Run returned neither a result nor an infrastructure error.");
        presentation.richText = presentation.message.toHtmlEscaped();
        return presentation;
    }

    const auto& result = execution.result;
    presentation.total = static_cast<int>(result.total);
    presentation.succeeded = static_cast<int>(result.succeeded);
    presentation.failed = static_cast<int>(result.failed);
    presentation.cancelled = static_cast<int>(result.cancelled);
    presentation.setupDetails = setupDetails(result);
    presentation.hasInstalledYamlData = result.has_installed_yaml_data;
    if (result.has_installed_yaml_data) {
        presentation.installedYamlData = presentInstalledYamlData(result.installed_yaml_data);
        presentation.installedYamlData.runDisplayLines = presentation.displayLines;
    }
    presentation.logs.reserve(static_cast<qsizetype>(result.logs.size()));
    for (const auto& log : result.logs) {
        presentation.logs.append(presentLog(log));
    }

    // The section model is unchanged: each terminal status still selects exactly one GUI-facing kind,
    // and that kind still selects which lifecycle signal the worker emits. What the switch no longer
    // does is decide what the run says.
    using Status = classic::scanner::ScanRunContractStatus;
    switch (result.status) {
    case Status::Completed:
        presentation.kind = ScanRunTerminalKind::Completed;
        break;
    case Status::NoCrashLogsFound:
        presentation.kind = ScanRunTerminalKind::NoCrashLogsFound;
        break;
    case Status::SetupFailed:
        presentation.kind = ScanRunTerminalKind::SetupFailed;
        // The FCX Mode setup projection is grouped in after the rendered lines rather than spliced
        // into them. The presentation crate deliberately does not render it, and a flat sequence
        // carries no structure to splice into without guessing an index.
        //
        // Only `richText` gains it, and that asymmetry is deliberate. `richText` is what reaches the
        // failure dialog, which is the one surface that has to state the whole failure in one place.
        // `message` stays exactly the rendered lines, because it is what `ScanWorker` logs — and the
        // worker logs `setupDetails` on its own line straight afterwards, for every status rather
        // than just this one. Folding it into both would print the setup block twice in the log.
        if (!presentation.setupDetails.isEmpty()) {
            const QString setupHtml =
                presentation.setupDetails.toHtmlEscaped().replace(QLatin1Char('\n'), QStringLiteral("<br>"));
            presentation.richText.append(presentation.richText.isEmpty() ? setupHtml
                                                                         : QStringLiteral("<br>") + setupHtml);
        }
        break;
    case Status::LocalIgnoreRecoveryRequired:
        presentation.kind = ScanRunTerminalKind::LocalIgnoreRecoveryRequired;
        break;
    case Status::CancelledBeforeDiscovery:
        presentation.kind = ScanRunTerminalKind::CancelledBeforeDiscovery;
        break;
    case Status::Cancelled:
        presentation.kind = ScanRunTerminalKind::Cancelled;
        break;
    }
    return presentation;
}

} // namespace classic::gui
