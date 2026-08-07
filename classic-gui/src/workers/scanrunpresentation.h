#pragma once

#include <QMetaType>
#include <QString>
#include <QStringList>
#include <QVector>

#include "classic_cxx_bridge/scanner.h"
#include "rust/cxx.h"

#include <functional>

namespace classic::gui {

/// GUI-facing terminal category for one typed Crash Log Scan Run execution envelope.
enum class ScanRunTerminalKind {
    Completed,
    NoCrashLogsFound,
    SetupFailed,
    LocalIgnoreRecoveryRequired,
    CancelledBeforeDiscovery,
    Cancelled,
    InfrastructureError,
};

/// Explicit GUI response to a malformed Local Ignore file encountered by an active scan run.
enum class ScanRunLocalIgnoreRecoveryChoice {
    ProceedWithoutIgnore,
    ResetToDefault,
    Cancel,
};

/// One Local Ignore recovery decision as Rust describes it, projected into Qt-owned values.
///
/// A copy rather than a view onto the bridged envelope, and free of any `rust::Box`: this rides a
/// `Qt::BlockingQueuedConnection` from the worker thread to the GUI thread, so it must be copyable
/// and must carry nothing the worker still owns.
struct ScanRunRecoveryDecisionPresentation {
    /// The decision to hand back when this option is chosen.
    classic::scanner::ScanRunLocalIgnoreRecoveryDecision decision =
        classic::scanner::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore;
    /// The decision's Display Label, as Rust resolved it. Button text, unchanged.
    QString label;
    /// What choosing it will actually do, rendered as rich text like every other line.
    QString description;
    /// Whether this run can honor the decision.
    ///
    /// A prompt must not offer a decision for which this is false: Rust still fails safely and
    /// touches nothing on disk, but the attempt spends the one-shot continuation, so the user is
    /// left with no scan and no second attempt. Defaults to false so a partially built decision is
    /// withheld rather than offered.
    bool available = false;
};

/// The Rust-owned content of a Local Ignore recovery prompt, projected into Qt-owned values.
///
/// Rendered on the worker thread before the hop to the GUI thread, because the bridged envelope
/// cannot cross that hop and cannot be re-rendered on the far side.
struct ScanRunLocalIgnoreRecoveryPresentation {
    /// The paused run rendered as rich text, not a sentence about it.
    ///
    /// The whole rendered run, because Rust exposes the Installed YAML Data block — the facts this
    /// decision is about — only as part of it. An implementation must be prepared for markup and
    /// for more than one line.
    QString message;
    /// Rust's own question, rendered as rich text: why the run paused, which file is at fault, and
    /// — when one is being withheld — why fewer decisions are about to be offered.
    QString prompt;
    /// Every decision the continuation contract accepts, in Rust's declared order.
    ///
    /// Carries the unavailable ones too, so a prompt that must explain the absence it is about to
    /// create is told what is being withheld. Filtering happens where a button is created.
    QVector<ScanRunRecoveryDecisionPresentation> decisions;
};

/// GUI-thread prompt used by ScanWorker while Rust retains the single-use recovery continuation.
///
/// Takes one value rather than a message and a flag beside it. Availability travels attached to the
/// decision it describes, which is what stops a prompt offering a decision that would burn the
/// continuation: a button cannot be created without reading the field that says whether it can
/// succeed.
using ScanRunLocalIgnoreRecoveryPrompt =
    std::function<ScanRunLocalIgnoreRecoveryChoice(const ScanRunLocalIgnoreRecoveryPresentation& recovery)>;

/// One typed piece of a Crash Log Scan Run display line, projected into Qt-owned values.
///
/// The bridge cannot express a Rust enum carrying payloads, so a segment crosses flattened as a
/// kind tag plus one field per payload shape. This mirrors that flattening rather than rebuilding a
/// tagged union, so `kind` still selects which field to read and the fields it does not select stay
/// empty. For `Count`, `text` is the noun the Rust core already resolved to agree with `count` — an
/// adapter prints the two side by side and never re-decides the form.
struct ScanRunDisplaySegmentPresentation {
    classic::scanner::ScanRunDisplaySegmentKind kind = classic::scanner::ScanRunDisplaySegmentKind::Text;
    QString text;
    QString path;
    quint64 count = 0;
};

/// One line of Crash Log Scan Run Display Content, projected into Qt-owned values.
///
/// `severity` says how gravely the line should read. It names no colour: mapping it onto a palette
/// is this frontend's own choice, which is why the same line reads plain in the native CLI and
/// coloured here.
struct ScanRunDisplayLinePresentation {
    classic::scanner::ScanRunDisplaySeverity severity = classic::scanner::ScanRunDisplaySeverity::Info;
    QVector<ScanRunDisplaySegmentPresentation> segments;
};

/// Presentation-ready projection of one discovery-ordered per-log outcome.
///
/// There is no `failures` list any more, and no per-log prose of any kind. Both the outcome line and
/// its structured failures now arrive as Display Content in the run's rendered lines, so composing
/// them again here would be the second copy this whole change exists to delete. What survives are
/// the facts the GUI consumes as data rather than as words: the report path it collects directories
/// from, and the booleans behind `logScanned`.
struct ScanRunLogPresentation {
    int discoveryIndex = 0;
    bool succeeded = false;
    bool failed = false;
    bool cancelledBeforeStart = false;
    QString crashLog;
    QString autoscanReport;
    QString message;
    bool movedToUnsolvedLogs = false;
};

/// Exact identity of one YAML Data byte sequence retained by the scan run.
struct ScanRunYamlDataContentIdentityPresentation {
    QString sha256;
    quint64 byteLength = 0;
};

/// Selected Main or game YAML Data metadata projected into Qt-owned values.
struct ScanRunInstalledYamlDataFilePresentation {
    classic::scanner::ScanRunInstalledYamlDataRole role = classic::scanner::ScanRunInstalledYamlDataRole::Main;
    classic::scanner::ScanRunInstalledYamlDataProvenance provenance =
        classic::scanner::ScanRunInstalledYamlDataProvenance::Bundled;
    QString schemaVersion;
    QString sha256;
    quint64 byteLength = 0;
};

/// One structured Installed YAML Data diagnostic with explicit optional context.
struct ScanRunInstalledYamlDataDiagnosticPresentation {
    bool hasRole = false;
    classic::scanner::ScanRunInstalledYamlDataRole role = classic::scanner::ScanRunInstalledYamlDataRole::Main;
    bool hasCandidate = false;
    classic::scanner::ScanRunInstalledYamlDataProvenance candidate =
        classic::scanner::ScanRunInstalledYamlDataProvenance::Bundled;
    bool hasPath = false;
    QString path;
    classic::scanner::ScanRunInstalledYamlDataDiagnosticKind kind =
        classic::scanner::ScanRunInstalledYamlDataDiagnosticKind::CacheUnavailable;
    QString message;
};

/// Qt-owned durable metadata from a successful Local Ignore reset.
struct ScanRunLocalIgnoreResetPresentation {
    QString localIgnorePath;
    QString backupPath;
    ScanRunYamlDataContentIdentityPresentation malformedIdentity;
    ScanRunYamlDataContentIdentityPresentation backupIdentity;
    ScanRunYamlDataContentIdentityPresentation replacementIdentity;
};

/// Qt-owned projection of the immutable Installed YAML Data selected for one run.
struct ScanRunInstalledYamlDataPresentation {
    ScanRunInstalledYamlDataFilePresentation main;
    ScanRunInstalledYamlDataFilePresentation gameFile;
    classic::scanner::ScanRunLocalIgnoreYamlDataState localIgnoreState =
        classic::scanner::ScanRunLocalIgnoreYamlDataState::Existing;
    ScanRunYamlDataContentIdentityPresentation localIgnoreIdentity;
    QVector<ScanRunInstalledYamlDataDiagnosticPresentation> diagnostics;
    /// Whether Reset To Default is a decision the paused run can actually satisfy.
    ///
    /// False when the selected Main YAML Data retained no usable default Local Ignore to publish.
    /// Offering the decision anyway spends the single-use continuation on a typed failure, so the
    /// user is left with no scan, no repair, and no second attempt without starting over. Defaults
    /// to false to mirror the bridge DTO; a caller deciding whether to offer the decision reads
    /// `hasInstalledYamlData` first, because silence from the run is not a denial.
    bool localIgnoreResetAvailable = false;
    bool hasLocalIgnoreReset = false;
    ScanRunLocalIgnoreResetPresentation localIgnoreReset;
    /// The rendered run this Installed YAML Data snapshot belongs to.
    ///
    /// It rides on this struct rather than reaching the window by some other route because the
    /// run-level warning is raised from the slot this struct arrives on, and the Rust core exposes
    /// the Installed YAML Data block only as part of the whole rendered run. Picking that block back
    /// out by position would be a structural assumption about a sequence that deliberately carries
    /// no structure; the native CLI and the TUI resolved the same problem the same way for their
    /// recovery prompts.
    QVector<ScanRunDisplayLinePresentation> runDisplayLines;
};

/// Presentation-ready terminal state without flattening typed counts or per-log dispositions.
///
/// `displayLines` is what the run says; every other field is what this frontend needs as data.
/// `message` and `richText` are those lines in the two shapes Qt surfaces want — one for a plain
/// single-string sink, one for a widget that can style and link.
///
/// The two are not always identical, and the one place they differ is deliberate: on a setup
/// failure `richText` also carries the FCX Mode setup projection, because it reaches the failure
/// dialog and that dialog has to state the whole failure in one place. `message` stays exactly the
/// rendered lines, because it is what the worker logs — and the worker logs `setupDetails` on its
/// own line for every status, so folding it into both would print that block twice.
struct ScanRunTerminalPresentation {
    ScanRunTerminalKind kind = ScanRunTerminalKind::InfrastructureError;
    QVector<ScanRunDisplayLinePresentation> displayLines;
    QString message;
    QString richText;
    QString setupDetails;
    int total = 0;
    int succeeded = 0;
    int failed = 0;
    int cancelled = 0;
    QVector<ScanRunLogPresentation> logs;
    bool hasInstalledYamlData = false;
    ScanRunInstalledYamlDataPresentation installedYamlData;
    /// Whether `recoveryPrompt` describes a decision this run is waiting on.
    ///
    /// True only for `LocalIgnoreRecoveryRequired`, which is also exactly when the execution
    /// retains a continuation to answer with.
    bool hasRecoveryPrompt = false;
    /// What to ask the user, and which answers this run can honor. Empty when there is nothing to
    /// ask, so a finished run never carries a question a frontend could show.
    ScanRunLocalIgnoreRecoveryPresentation recoveryPrompt;
};

/// Returns the core Display Label for one scan-run Local Ignore YAML Data state.
///
/// The wording belongs to the Rust core and is fetched through the bridge, so the CLI, the GUI, and
/// the TUI cannot describe the same outcome differently. Presentation only — branch on the enum, and
/// never on this string, because a Display Label may be reworded between releases.
QString localIgnoreStateLabel(classic::scanner::ScanRunLocalIgnoreYamlDataState state);

/// Returns the core Display Label for one selected YAML Data provenance.
///
/// Same contract as localIgnoreStateLabel: core-owned prose, safe to reword, never parsed.
QString installedYamlDataProvenanceLabel(classic::scanner::ScanRunInstalledYamlDataProvenance provenance);

/// Projects one rendered Crash Log Scan Run block into Qt-owned display lines.
///
/// The order Rust chose is preserved exactly, both between lines and between the segments inside a
/// line. This frontend may reorder, group, or omit whole lines — it may never reorder within one.
QVector<ScanRunDisplayLinePresentation> presentScanRunDisplayLines(
    const rust::Vec<classic::scanner::ScanRunDisplayLine>& lines);

/// Returns the hex colour this frontend reads one display severity in.
///
/// The mapping is entirely the GUI's: the Rust core names how gravely a line should read and never
/// names a colour, which is why the same line arrives plain in the native CLI's pipeable output and
/// coloured here. Values are the dark theme's, so a run reads like the rest of the window.
QString scanRunSeverityColor(classic::scanner::ScanRunDisplaySeverity severity);

/// Concatenates one display line's segments into plain text, in the order Rust put them in.
///
/// Exposed for the renderer-conformance test, which asserts ordering and the count's noun without
/// re-pinning wording `classic-scan-presentation` already pins once.
QString renderScanRunDisplayLineAsPlainText(const ScanRunDisplayLinePresentation& line);

/// Joins every line's plain text with newlines, preserving Rust's line order.
QString renderScanRunDisplayLinesAsPlainText(const QVector<ScanRunDisplayLinePresentation>& lines);

/// Concatenates one display line's segments into rich text, in the order Rust put them in.
///
/// Per-kind styling is this frontend's whole contribution: a `Path` becomes an actionable
/// `file:` anchor so a user can open the Autoscan Report the run just wrote, a `Count` emphasises
/// its value and prints Rust's noun beside it untouched, an `Emphasis` reads italic, and the line as
/// a whole takes its severity's colour. No segment's words are changed, and a `Label` is rendered
/// exactly as handed over rather than looked up again.
///
/// Exposed for the renderer-conformance test for the same reason as the plain-text renderer.
QString renderScanRunDisplayLineAsRichText(const ScanRunDisplayLinePresentation& line);

/// Joins every line's rich text with `<br>`, preserving Rust's line order.
QString renderScanRunDisplayLinesAsRichText(const QVector<ScanRunDisplayLinePresentation>& lines);

/// Aggregates degraded Installed YAML Data selection and durable Local Ignore recovery into one
/// run-level warning, or returns an empty string when the run has nothing the user must act on.
///
/// Which situations are worth interrupting the user is Display Layout and stays here.
/// `LocalIgnoreGenerated` is deliberately excluded: generating a missing Local Ignore file from the
/// selected Main defaults is an expected successful path, so a clean first run stays silent. The
/// result is run-level only and never contributes to Autoscan Report content.
///
/// What the warning *says* is no longer this frontend's. Once the decision to warn is made, the body
/// is the run's rendered lines under a GUI-owned section header. It carries the whole run rather
/// than the Installed YAML Data block alone because that block is only reachable as part of the
/// rendered run, and every surrounding line describes the very run whose YAML Data went wrong.
///
/// Two classes of line are withheld, both of them whole-line omissions the adapter contract allows:
/// an expected first-run Local Ignore generation, and any Local Ignore problem the recovery dialog
/// already asked the user about. A withheld line is recognised by the diagnostic message it carries,
/// which this frontend already holds a typed copy of — it compares that payload rather than reading
/// the prose around it.
QString formatInstalledYamlDataWarning(const ScanRunInstalledYamlDataPresentation& installedYamlData);

/// Formats Targeted discovery rejections without reapplying GUI-owned rejection policy.
QString formatScanRunRejections(const classic::scanner::ScanRunContractDiscoveryResult& discovery);

/// Returns unique report directories derived from Rust-accepted Crash Logs.
QStringList scanRunReportDirectories(const classic::scanner::ScanRunContractDiscoveryResult& discovery);

/// Maps every typed terminal status, disposition, failure stage, and infrastructure stage for Qt presentation.
ScanRunTerminalPresentation presentScanRunExecution(const classic::scanner::ScanRunContractExecutionResult& execution);

} // namespace classic::gui

Q_DECLARE_METATYPE(classic::gui::ScanRunInstalledYamlDataPresentation)
