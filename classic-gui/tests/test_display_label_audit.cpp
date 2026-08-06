// Contract audit for the Vocabulary naming rule: the Rust core crate that
// defines a domain concept owns what that concept is called, and this frontend
// renders that Display Label rather than keeping a table of its own.
//
// Why a source audit rather than a behavior test. A newly written duplicate
// table produces correct strings on the day it is written and only diverges
// later, so it is behaviorally perfect at exactly the moment it should be
// rejected. That is the failure mode this catches and no assertion on rendered
// output can, and this frontend is the proof: the GUI shipped six Display
// Labels that disagreed with the TUI's, and the entire Qt suite stayed green
// over all six, because the only labels any test pinned were the ones all three
// frontends already agreed about.
//
// The design is ported from `classic-cli/tests/test_display_label_audit.cpp`,
// which is itself ported from `ui-applications/classic-tui/tests/shared_runtime_audit.rs`,
// including the two properties that make it hold up:
//
//   * It counts occurrences rather than naming functions, so a table added to
//     an already-audited file is covered without anyone remembering to extend
//     this file.
//   * It carries a meta-test that fails when its own source file list goes
//     stale, so a brand-new GUI source file cannot slip past unaudited.
//
// The port is not a copy. Six things changed, none of them cosmetic, and the
// first three exist because the CLI's detectors are wholly or partly blind on a
// Qt frontend — a detector that matches nothing still passes, which is a worse
// state than having no audit at all:
//
//   * `QString` joins the return-type allowlist in the third detector, which
//     also learns to read a trailing return type. Every label-shaped function
//     in a Qt frontend returns `QString`, so without this the one detector that
//     survives a `default:` arm or an interpolating body matched nothing here.
//   * The first two detectors no longer require the literal `return "`. A Qt
//     table reads `return QStringLiteral("analysis");` and contains no such
//     text. The second drops `return` altogether and asks only that a variant
//     and a literal share a line, which additionally catches a table written as
//     container data rather than as control flow.
//   * All three run under every name the type answers to, `using X = ...;`
//     aliases included, with identifier-boundary matching so a short alias does
//     not match the middle of a longer name. This is the hole that mattered
//     most: aliasing the enum first is the house style in the very file this
//     audits, so a table written that way would have named the audited type on
//     no line but its `using` declaration.
//   * The positive test additionally asserts each audited type is still spelled
//     in the rendering source. `RENDERED_ENUMS` holds strings, never types, so a
//     bridge-side rename would otherwise leave the detectors matching nothing
//     forever while the suite stayed green.
//   * The audited file list is subdirectory-aware. `classic-cli/src/` is flat;
//     `classic-gui/src/` is five directories deep in places.
//   * Offenders are accumulated and reported in one assertion rather than one
//     per file. Qt Test has no non-fatal check, so where the CLI leans on
//     Catch2's `CHECK` to report every table a contributor wrote, this collects
//     them and fails once. Same intent, different framework.
//
// Each detector was verified by planting the shape it targets and watching it
// fail, rather than by observing a green run.
//
// Only `classic-gui/src/` is audited. Test files legitimately quote settled
// Display Labels as literals — that is how a wording a ticket decided is pinned
// across the binding boundary, and `test_scanrunpresentation.cpp` does exactly
// that on purpose.

#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QSet>
#include <QStringList>
#include <QtTest/QtTest>

#include <algorithm>
#include <array>
#include <cctype>
#include <cstring>
#include <sstream>
#include <string>
#include <string_view>
#include <vector>

namespace {

/// Returns `classic-gui/`, derived from the test's compile-time source directory.
///
/// `QT_TESTCASE_SOURCEDIR` is what every other source-scraping GUI test uses
/// (`test_scan_settings_wiring.cpp`, `test_mainwindow_geometry.cpp`), so this
/// needs no new CMake macro.
QString guiRoot()
{
    return QDir::cleanPath(QStringLiteral(QT_TESTCASE_SOURCEDIR "/.."));
}

/// Reads one `classic-gui/`-relative source file whole, or returns an empty optional.
///
/// Returns `false` rather than asserting so the caller can attribute an
/// unreadable file to the path that named it.
bool readSource(const QString& relativePath, std::string& contents)
{
    QFile file(guiRoot() + QLatin1Char('/') + relativePath);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return false;
    }
    const QByteArray bytes = file.readAll();
    contents.assign(bytes.constData(), static_cast<std::size_t>(bytes.size()));
    return true;
}

/// Every GUI source file this audit inspects.
///
/// C++ could glob `src/` instead of declaring these, unlike the Rust audit this
/// design descends from, where `include_str!` demands literal paths. The list is
/// kept anyway because it makes the audited set reviewable in a diff and lets a
/// failure name the offending file — and `the_audit_covers_every_gui_source_file`
/// below is what stops it from quietly falling behind the directory.
constexpr auto AUDITED_SOURCES = std::to_array<std::string_view>({
    "src/app/aboutdialog.cpp",
    "src/app/aboutdialog.h",
    "src/app/errordialog.cpp",
    "src/app/errordialog.h",
    "src/app/localignorerecoveryprompt.cpp",
    "src/app/localignorerecoveryprompt.h",
    "src/app/mainwindow.cpp",
    "src/app/mainwindow.h",
    "src/app/papyrusdialog.cpp",
    "src/app/papyrusdialog.h",
    "src/app/pathdialog.cpp",
    "src/app/pathdialog.h",
    "src/app/settingsdialog.cpp",
    "src/app/settingsdialog.h",
    "src/app/typography.cpp",
    "src/app/typography.h",
    "src/controllers/backupcontroller.cpp",
    "src/controllers/backupcontroller.h",
    "src/controllers/gamefilescontroller.cpp",
    "src/controllers/gamefilescontroller.h",
    "src/controllers/resultscontroller.cpp",
    "src/controllers/resultscontroller.h",
    "src/controllers/scancontroller.cpp",
    "src/controllers/scancontroller.h",
    "src/core/featurecontext.cpp",
    "src/core/featurecontext.h",
    "src/core/gamepathutils.h",
    "src/core/gamesetupusersettings.cpp",
    "src/core/gamesetupusersettings.h",
    "src/core/guiusersettings.cpp",
    "src/core/guiusersettings.h",
    "src/core/reportpathkey.cpp",
    "src/core/reportpathkey.h",
    "src/core/rust_qt_bridge.h",
    "src/core/signalhub.cpp",
    "src/core/signalhub.h",
    "src/core/threadmanager.cpp",
    "src/core/threadmanager.h",
    "src/main.cpp",
    "src/widgets/adaptiveprogressbar.cpp",
    "src/widgets/adaptiveprogressbar.h",
    "src/widgets/markdownviewer.cpp",
    "src/widgets/markdownviewer.h",
    "src/widgets/reportlistwidget.cpp",
    "src/widgets/reportlistwidget.h",
    "src/widgets/reportmetadatawidget.cpp",
    "src/widgets/reportmetadatawidget.h",
    "src/widgets/toggleswitch.cpp",
    "src/widgets/toggleswitch.h",
    "src/workers/gamefilesworker.cpp",
    "src/workers/gamefilesworker.h",
    "src/workers/papyrusworker.cpp",
    "src/workers/papyrusworker.h",
    "src/workers/scanprogressmodel.cpp",
    "src/workers/scanprogressmodel.h",
    "src/workers/scanrequestbuilder.cpp",
    "src/workers/scanrequestbuilder.h",
    "src/workers/scanrunpresentation.cpp",
    "src/workers/scanrunpresentation.h",
    "src/workers/scanworker.cpp",
    "src/workers/scanworker.h",
    "src/workers/updateworker.cpp",
    "src/workers/updateworker.h",
    "src/workers/yamlupdateworker.cpp",
    "src/workers/yamlupdateworker.h",
});

/// One domain enum whose Display Label the Rust core owns, paired with the
/// bridge entry point that supplies it.
///
/// Paired rather than held in two parallel arrays so the type and its accessor
/// cannot drift out of step, which is the same failure this whole audit exists
/// to prevent one level down.
struct RenderedEnum {
    std::string_view typeName;
    std::string_view labelAccessor;
    /// Whether this frontend actually renders the label today.
    ///
    /// Only `ScanRunContractLogDisposition` is `false`, and that is a recorded
    /// decision rather than an omission — see the comment on the positive test.
    bool renderedByTheGui;
};

/// Every domain enum whose Display Label the Rust core owns and the bridge exposes.
///
/// A table here producing a string is by definition a second copy of a
/// vocabulary that already has a home, which is why all seven are audited
/// negatively even though the GUI renders six.
constexpr auto RENDERED_ENUMS = std::to_array<RenderedEnum>({
    {"ScanRunContractLogFailureStage", "scanner::scan_run_log_failure_stage_label", true},
    {"ScanRunContractInfrastructureErrorStage", "scanner::scan_run_infrastructure_error_stage_label", true},
    {"ScanRunLocalIgnoreResetFailureStage", "scanner::scan_run_local_ignore_reset_failure_stage_label", true},
    {"ScanRunInstalledYamlDataProvenance", "scanner::scan_run_installed_yaml_data_provenance_label", true},
    {"ScanRunLocalIgnoreYamlDataState", "scanner::scan_run_local_ignore_yaml_data_state_label", true},
    {"ScanRunInstalledYamlDataDiagnosticKind", "scanner::scan_run_installed_yaml_data_diagnostic_kind_label", true},
    {"ScanRunContractLogDisposition", "scanner::scan_run_log_disposition_label", false},
});

/// The one GUI file that renders scan-run Display Labels.
constexpr std::string_view LABEL_RENDERING_SOURCE = "src/workers/scanrunpresentation.cpp";

/// True for a character C++ allows inside an identifier.
bool isIdentifierChar(char character)
{
    return std::isalnum(static_cast<unsigned char>(character)) != 0 || character == '_';
}

/// True when `name` sits at `at` as a whole identifier rather than inside a longer one.
///
/// Needed once aliases join the search: `State` occurs inside both
/// `ScanRunLocalIgnoreYamlDataState` and `localIgnoreState`, and a plain
/// substring search would report a hit on every mention of either.
bool isWholeIdentifierAt(const std::string& source, std::size_t at, std::string_view name)
{
    if (at > 0 && isIdentifierChar(source[at - 1])) {
        return false;
    }
    const auto after = at + name.size();
    return after >= source.size() || !isIdentifierChar(source[after]);
}

/// Returns every name `enumName` answers to inside `source`: the type itself,
/// plus each `using X = <enumName>;` alias the file declares.
///
/// Without this the audit has a hole exactly where this frontend is most likely
/// to fall into it. All three detectors below have to spell the type to find
/// anything, and the house style in `scanrunpresentation.cpp` is to alias it
/// first — `using Disposition = ...;` and `using State = ...;` are both already
/// there. A table written under either alias would have named the audited type
/// nowhere except on the `using` line, and sailed through.
std::vector<std::string> namesFor(const std::string& source, std::string_view enumName)
{
    std::vector<std::string> names{std::string(enumName)};
    std::istringstream reader(source);
    std::string line;
    while (std::getline(reader, line)) {
        const auto usingAt = line.find("using ");
        if (usingAt == std::string::npos) {
            continue;
        }
        const auto equals = line.find('=', usingAt);
        // No `=` means `using namespace ...;` or a using-declaration, neither of
        // which introduces a second name for this type.
        if (equals == std::string::npos || line.find(enumName, equals) == std::string::npos) {
            continue;
        }

        auto start = usingAt + std::strlen("using ");
        auto end = equals;
        while (start < end && std::isspace(static_cast<unsigned char>(line[start])) != 0) {
            ++start;
        }
        while (end > start && std::isspace(static_cast<unsigned char>(line[end - 1])) != 0) {
            --end;
        }
        const auto alias = line.substr(start, end - start);
        // A well-formed alias is one identifier. Anything else — `using enum X`,
        // a wrapped declaration — is left alone rather than guessed at.
        if (!alias.empty() && alias.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_") ==
                                  std::string::npos) {
            names.push_back(alias);
        }
    }
    return names;
}

/// True when `text` names a string return type.
bool namesAStringReturn(const std::string& text)
{
    return text.find("QString") != std::string::npos || text.find("std::string") != std::string::npos ||
           text.find("char*") != std::string::npos || text.find("char *") != std::string::npos;
}

/// Returns one past the `:` terminating the `case` label starting at `caseStart`.
///
/// A scoped-enum label contains `::`, so the first colon is not the terminator.
/// Skipping doubled colons is the whole trick: it separates the label from the
/// namespace and type qualifiers embedded in it.
std::size_t findCaseLabelEnd(const std::string& source, std::size_t caseStart)
{
    for (std::size_t at = caseStart; at < source.size(); ++at) {
        if (source[at] != ':') {
            continue;
        }
        if (at + 1 < source.size() && source[at + 1] == ':') {
            ++at;
            continue;
        }
        return at + 1;
    }
    return std::string::npos;
}

/// Returns where one `switch` arm's body ends.
///
/// An arm runs to the next label or to the end of the enclosing function,
/// whichever comes first. The function end is anchored on a newline followed by
/// `}` because this project formats every function's closing brace at column
/// zero, and the final arm of a `switch` has no label after it to bound it.
std::size_t findArmBodyEnd(const std::string& source, std::size_t bodyStart)
{
    return std::min({source.find("case ", bodyStart), source.find("default:", bodyStart),
                     source.find("\n}", bodyStart), source.size()});
}

/// Counts `switch` arms on `enumName` whose body returns a string literal.
///
/// Counting rather than naming is deliberate: this never asks whether a
/// particular function exists, so a table written into an audited file under any
/// name is found.
///
/// The CLI's version keys on the literal `return "`. That is exact but blind in
/// Qt, where a table reads `return QStringLiteral("analysis");` and contains no
/// `return "` at all. So the quote is looked for after the `return` rather than
/// adjacent to it — after, not merely inside the arm, so that an arm which
/// builds a message and then returns a variable is still not counted.
std::size_t countLiteralReturningArms(const std::string& source, std::string_view enumName)
{
    const std::string qualified = std::string(enumName) + "::";
    std::size_t count = 0;
    for (std::size_t at = source.find("case "); at != std::string::npos; at = source.find("case ", at + 1)) {
        const auto labelEnd = findCaseLabelEnd(source, at);
        if (labelEnd == std::string::npos) {
            break;
        }
        // `find` returning npos compares greater than any real offset, so an
        // arm labelled with some other enum is skipped by the same test that
        // rejects a match found past the end of this label.
        if (source.find(qualified, at) >= labelEnd) {
            continue;
        }
        const auto armEnd = findArmBodyEnd(source, labelEnd);
        const auto returnAt = source.find("return ", labelEnd);
        if (returnAt < armEnd && source.find('"', returnAt) < armEnd) {
            ++count;
        }
    }
    return count;
}

/// Counts lines that name an audited variant beside a string literal.
///
/// The `switch` scan cannot see `return kind == Kind::Parse ? "parse" : "";`,
/// which is the same table written as an expression. Pairing a variant with a
/// literal on one line catches that shape without trying to parse C++.
///
/// The CLI's version requires the literal `return "`. This drops the `return`
/// entirely, for two reasons. Qt wraps its literals, so `return
/// QStringLiteral("parse");` carries no `return "` at all. And a naming table
/// need not return anything on the line where it pairs the two: a container
/// literal such as `{{Kind::Parse, QStringLiteral("parse failure")}, ...}` is
/// the same vocabulary with the same drift, written as data. Requiring only
/// adjacency catches both.
std::size_t countVariantsBesideLiterals(const std::string& source, std::string_view enumName)
{
    const std::string qualified = std::string(enumName) + "::";
    std::size_t count = 0;
    std::istringstream reader(source);
    std::string line;
    while (std::getline(reader, line)) {
        if (line.find(qualified) != std::string::npos && line.find('"') != std::string::npos) {
            ++count;
        }
    }
    return count;
}

/// Returns the offset of the `{` opening a body, or npos when there is none.
///
/// Stops at `;` so a forward declaration — or a struct member with a default
/// initializer, of which `scanrunpresentation.h` has several — is never mistaken
/// for a definition.
std::size_t findBodyStart(const std::string& source, std::size_t at)
{
    for (std::size_t index = at; index < source.size(); ++index) {
        if (source[index] == ';') {
            return std::string::npos;
        }
        if (source[index] == '{') {
            return index;
        }
    }
    return std::string::npos;
}

/// Returns the offset one past the `}` closing the body opened at `bodyStart`.
///
/// Braces are counted naively rather than lexed. Format strings such as `"{}"`
/// carry balanced braces and so cancel out; an unbalanced one would end the
/// body early, which makes the scan read *more* text than it should. That
/// errs toward a false positive, which a contributor sees and can argue with,
/// rather than a false negative, which no one ever sees.
std::size_t findBodyEnd(const std::string& source, std::size_t bodyStart)
{
    int depth = 0;
    for (std::size_t index = bodyStart; index < source.size(); ++index) {
        if (source[index] == '{') {
            ++depth;
        } else if (source[index] == '}') {
            if (--depth == 0) {
                return index + 1;
            }
        }
    }
    return source.size();
}

/// Counts string literals inside string-returning functions that take `enumName`.
///
/// This is the detector that holds when the other two do not. A naming table
/// need not be a `switch` and need not put a variant beside a literal: a
/// `default: return QStringLiteral("unknown stage");`, or a body that
/// interpolates into a wider phrase, produces the same drift while naming no
/// variant at all. What those share is the shape — a function that takes one of
/// these enums and hands back a string. Nothing in this frontend has a
/// legitimate reason to be that function anymore, because the bridge already is
/// one.
///
/// `QString` heads the return-type allowlist because in a Qt frontend it is the
/// only one that matters; `std::string` and `char*` are kept so a helper written
/// in either still trips the check. A trailing return type is checked too, since
/// `auto label(Kind k) -> QString` puts the type after the parameter list.
///
/// Restricting the check to a *string-returning* signature is what keeps it
/// usable: a function that merely takes a diagnostic kind and formats a wider
/// message is not a naming table and should not be counted. Note that this is a
/// narrower exemption than it sounds — it excludes nothing in this file today.
/// `formatInstalledYamlDataDiagnostic` returns `QString` and would not survive
/// the return-type filter; what actually spares it is that no audited type is
/// named in its signature, only in its body.
///
/// **Known limits.** Two shapes still escape all three detectors, and are
/// recorded here rather than papered over. A table keyed by index —
/// `constexpr const char* kLabels[] = {"parse failure", ...}` selected with
/// `static_cast<int>(kind)` — names no variant and puts no literal in the
/// accessor's body. So does a lookup container filled elsewhere, if its
/// insertions live in a file where the enum is never spelled. Both defeat text
/// scanning by construction; catching them needs a real parse. What closes the
/// gap in practice is that either one still has to hand its result to a caller
/// that renders it, and the positive test below asserts every rendered label
/// still comes from a bridge accessor.
std::size_t countLiteralsInLabelShapedFunctions(const std::string& source, std::string_view enumName)
{
    std::size_t count = 0;
    for (std::size_t at = source.find(enumName); at != std::string::npos;
         at = source.find(enumName, at + enumName.size())) {
        // Aliases are short, so a bare substring hit is often the middle of a
        // longer identifier rather than a use of the type.
        if (!isWholeIdentifierAt(source, at, enumName)) {
            continue;
        }
        const auto bodyStart = findBodyStart(source, at);
        if (bodyStart == std::string::npos) {
            continue;
        }
        // The signature runs back to whatever terminated the previous
        // construct, so a declaration wrapped across several lines is still
        // read whole.
        const auto previous = source.find_last_of(";{}", at);
        const auto signatureStart = previous == std::string::npos ? 0 : previous + 1;
        const auto signature = source.substr(signatureStart, bodyStart - signatureStart);

        // Everything before the parameter list is the return type and the
        // name. Checking that part rather than the whole signature keeps a
        // `QString` *parameter* from reading as a string return, and keeps an
        // `if (x == Enum::Variant) {` inside some other function from reading
        // as a signature at all.
        const auto parameters = signature.find('(');
        if (parameters == std::string::npos) {
            continue;
        }
        const auto leading = signature.substr(0, parameters);
        // `rfind` can land on a member access in a default argument rather than
        // a real trailing return. That over-matches, which errs toward a false
        // positive a contributor can argue with.
        const auto arrow = signature.rfind("->");
        const auto trailing = arrow == std::string::npos ? std::string{} : signature.substr(arrow);
        if (!namesAStringReturn(leading) && !namesAStringReturn(trailing)) {
            continue;
        }

        const auto bodyEnd = findBodyEnd(source, bodyStart);
        for (auto quote = source.find('"', bodyStart); quote != std::string::npos && quote < bodyEnd;
             quote = source.find('"', quote + 1)) {
            ++count;
        }
    }
    // Quotes come in pairs, so halving them reports literals rather than
    // delimiters. Escaped quotes would inflate this, but the assertion is
    // against zero, so an inflated non-zero count is still a correct verdict.
    return count / 2;
}

/// Counts every naming-table shape for `enumName`, under every name it answers to.
///
/// Summed rather than short-circuited so one report names the whole problem. An
/// alias means the same table can be counted twice, once per name — the count
/// is inflated but the verdict is not, since the assertion is against zero.
std::size_t countNamingTables(const std::string& source, std::string_view enumName)
{
    std::size_t tables = 0;
    for (const auto& name : namesFor(source, enumName)) {
        tables += countLiteralReturningArms(source, name) + countVariantsBesideLiterals(source, name) +
                  countLiteralsInLabelShapedFunctions(source, name);
    }
    return tables;
}

} // namespace

class DisplayLabelAuditTests : public QObject {
    Q_OBJECT

private slots:
    void no_gui_source_turns_an_audited_enum_into_a_string_literal();
    void every_rendered_gui_display_label_comes_from_a_bridge_accessor();
    void the_audit_covers_every_gui_source_file();
};

void DisplayLabelAuditTests::no_gui_source_turns_an_audited_enum_into_a_string_literal()
{
    QStringList offenders;
    for (const auto& relativePath : AUDITED_SOURCES) {
        const QString path = QString::fromUtf8(relativePath.data(), static_cast<qsizetype>(relativePath.size()));
        std::string source;
        QVERIFY2(readSource(path, source), qPrintable(QStringLiteral("Unable to read %1").arg(path)));

        for (const auto& rendered : RENDERED_ENUMS) {
            // Three detectors, because a naming table has more than one shape.
            // The first two read `switch` arms and variant-beside-literal
            // lines; the third keys on the function signature instead and needs
            // no variant named at all, which is what catches a `default:` arm
            // or a body that interpolates rather than returning a bare label.
            //
            // All three run under every name the type answers to, aliases
            // included. That is not hypothetical tidiness: `presentLog` spells
            // its disposition switch `using Disposition = ...;` and
            // `formatInstalledYamlDataWarning` spells its state comparison
            // `using State = ...;`, so a table added beside either would name
            // the audited type on no line but the `using` one.
            const auto tables = countNamingTables(source, rendered.typeName);
            if (tables == 0) {
                continue;
            }
            offenders.append(
                QStringLiteral("%1 turns %2 into %3 string literal(s); call %4 instead, so the CLI, the GUI, and "
                               "the TUI cannot disagree about the same outcome")
                    .arg(path, QString::fromUtf8(rendered.typeName.data(), static_cast<qsizetype>(rendered.typeName.size())))
                    .arg(static_cast<qulonglong>(tables))
                    .arg(QString::fromUtf8(rendered.labelAccessor.data(),
                                           static_cast<qsizetype>(rendered.labelAccessor.size()))));
        }
    }

    // One assertion over the whole sweep rather than one per file. Qt Test has
    // no non-fatal check, and a contributor who reached for tables usually
    // wrote more than one — failing on the first would report them a file at a
    // time across as many runs as they wrote.
    QVERIFY2(offenders.isEmpty(), qPrintable(offenders.join(QStringLiteral("\n"))));
}

void DisplayLabelAuditTests::every_rendered_gui_display_label_comes_from_a_bridge_accessor()
{
    // The negative audit above proves no table was written. This proves the
    // labels are still rendered at all: without it, deleting a call site would
    // read as compliance rather than as a frontend that stopped saying what
    // happened. It checks the call appears, not that it is reached — the
    // behavioral half of that lives in test_scanrunpresentation.cpp.
    //
    // Per-log disposition is excluded on purpose, decided on #167. The GUI has
    // no disposition line to label: `presentLog` maps the three variants onto
    // booleans that select control flow and feed counts, so requiring the
    // accessor here would force a results-view column into existence to justify
    // it. The enum stays in the negative audit above, so the guard still holds
    // if that column is ever added.
    const QString path =
        QString::fromUtf8(LABEL_RENDERING_SOURCE.data(), static_cast<qsizetype>(LABEL_RENDERING_SOURCE.size()));
    std::string source;
    QVERIFY2(readSource(path, source), qPrintable(QStringLiteral("Unable to read %1").arg(path)));

    QStringList missing;
    for (const auto& rendered : RENDERED_ENUMS) {
        const QString typeName =
            QString::fromUtf8(rendered.typeName.data(), static_cast<qsizetype>(rendered.typeName.size()));

        // Every audited type is checked to still be spelled somewhere in this
        // file, including the disposition the GUI renders no label for — it
        // appears as `using Disposition = ...`. This closes the one way the
        // negative audit could go quiet without anyone noticing: `RENDERED_ENUMS`
        // holds strings, never the types, so a bridge-side rename would leave
        // all three detectors matching nothing forever. The rename itself breaks
        // the GUI build, but the fix for that build break would not touch this
        // file, and a green audit afterwards would mean only that it had stopped
        // looking.
        if (source.find(rendered.typeName) == std::string::npos) {
            missing.append(QStringLiteral("%1 is named nowhere in %2, so the audit's detectors for it match nothing; "
                                          "if the bridge renamed it, rename it in RENDERED_ENUMS too")
                               .arg(typeName, path));
            continue;
        }

        if (!rendered.renderedByTheGui) {
            continue;
        }
        if (source.find(rendered.labelAccessor) != std::string::npos) {
            continue;
        }
        missing.append(QStringLiteral("%1 is not called from %2, so %3 has no Display Label to render")
                           .arg(QString::fromUtf8(rendered.labelAccessor.data(),
                                                  static_cast<qsizetype>(rendered.labelAccessor.size())),
                                path, typeName));
    }
    QVERIFY2(missing.isEmpty(), qPrintable(missing.join(QStringLiteral("\n"))));
}

void DisplayLabelAuditTests::the_audit_covers_every_gui_source_file()
{
    // The stale-list guard. AUDITED_SOURCES is written by hand, so a new file
    // under src/ would otherwise be unaudited from the day it lands — and a
    // naming table is most likely to appear in new code, not old.
    QSet<QString> audited;
    for (const auto& relativePath : AUDITED_SOURCES) {
        audited.insert(QString::fromUtf8(relativePath.data(), static_cast<qsizetype>(relativePath.size())));
    }

    // Recursive, because `classic-gui/src/` is already several directories deep
    // and a file added under a future one would otherwise be neither audited
    // nor reported — silently unaudited, which is the one hole this test exists
    // to close.
    const QDir sourceRoot(guiRoot() + QStringLiteral("/src"));
    QVERIFY2(sourceRoot.exists(), qPrintable(QStringLiteral("Missing %1").arg(sourceRoot.path())));

    // `.cxx` and `.inl` are listed although `src/` has none today, because the
    // cost of listing an extension nobody uses is nothing and the cost of
    // omitting one somebody adds is a silently unaudited file. Non-C++ assets
    // under `src/` — `.ui`, `.qss`, `.css`, `.rc.in`, `qt.conf` — are outside
    // this audit's reach on purpose: none can hold a `switch` on a C++ enum, so
    // none can be a naming table in the sense audited here.
    QStringList unaudited;
    QDirIterator iterator(sourceRoot.path(),
                          {QStringLiteral("*.cpp"), QStringLiteral("*.h"), QStringLiteral("*.hpp"),
                           QStringLiteral("*.cc"), QStringLiteral("*.cxx"), QStringLiteral("*.inl")},
                          QDir::Files, QDirIterator::Subdirectories);
    while (iterator.hasNext()) {
        // QDir yields '/' separators on every platform, so the comparison
        // against the hand-written list works on Windows unchanged.
        const QString relativePath = QStringLiteral("src/") + sourceRoot.relativeFilePath(iterator.next());
        if (!audited.contains(relativePath)) {
            unaudited.append(relativePath);
        }
    }

    unaudited.sort();
    QVERIFY2(unaudited.isEmpty(),
             qPrintable(QStringLiteral("add these to AUDITED_SOURCES so their Display Label handling stays audited: %1")
                            .arg(unaudited.join(QStringLiteral(", ")))));
}

QTEST_MAIN(DisplayLabelAuditTests)
#include "test_display_label_audit.moc"
