// Contract audit for the Vocabulary naming rule: the Rust core crate that
// defines a domain concept owns what that concept is called, and this frontend
// renders that Display Label rather than keeping a table of its own.
//
// Why a source audit rather than a behavior test. A newly written duplicate
// table produces correct strings on the day it is written and only diverges
// later, so it is behaviorally perfect at exactly the moment it should be
// rejected. That is the failure mode this catches and no assertion on rendered
// output can: the CLI, the GUI, and the TUI each had a copy of this vocabulary
// and the copies drifted silently for exactly that reason.
//
// The design is ported from `ui-applications/classic-tui/tests/shared_runtime_audit.rs`,
// including the two properties that make it hold up:
//
//   * It counts occurrences rather than naming functions, so a table added to
//     an already-audited file is covered without anyone remembering to extend
//     this file.
//   * It carries a meta-test that fails when its own source file list goes
//     stale, so a brand-new CLI source file cannot slip past unaudited.
//
// Only `classic-cli/src/` is audited. Test files legitimately quote settled
// Display Labels as literals — that is how a wording a ticket decided is pinned
// across the binding boundary — and `test_scan_run_contract.cpp` deliberately
// keeps a table of *Vocabulary Tokens*, which are frozen manifest identifiers
// rather than prose.

#include <catch2/catch_test_macros.hpp>

#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <set>
#include <sstream>
#include <string>
#include <string_view>
#include <vector>

namespace {

namespace fs = std::filesystem;

/// Returns `classic-cli/`, derived from this file's compile-time location.
///
/// The same technique `test_app_update_wiring.cpp` already uses, so the audit
/// needs no new CMake macro and stays in the bridge-free test target.
fs::path cli_root() {
    return fs::path(__FILE__).parent_path().parent_path();
}

/// Reads one `classic-cli/`-relative source file whole.
std::string read_source(std::string_view relative_path) {
    const auto path = cli_root() / relative_path;
    std::ifstream file(path);
    REQUIRE(file.is_open());

    std::ostringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

/// Every CLI source file this audit inspects.
///
/// C++ could glob `src/` instead of declaring these, unlike the Rust audit this
/// is ported from, where `include_str!` demands literal paths. The list is kept
/// anyway because it makes the audited set reviewable in a diff and lets a
/// failure name the offending file — and `the_audit_covers_every_cli_source_file`
/// below is what stops it from quietly falling behind the directory.
constexpr auto AUDITED_SOURCES = std::to_array<std::string_view>({
    "src/app_update.cpp",
    "src/app_update.h",
    "src/cli_args.cpp",
    "src/cli_args.h",
    "src/main.cpp",
    "src/progress.cpp",
    "src/progress.h",
    "src/scan_run_cli.cpp",
    "src/scan_run_cli.h",
    "src/scanner.cpp",
    "src/scanner.h",
    "src/thread_pool.cpp",
    "src/thread_pool.h",
    "src/user_settings_action.cpp",
    "src/user_settings_action.h",
    "src/yaml_update.cpp",
    "src/yaml_update.h",
});

/// One domain enum the CLI renders, paired with the bridge entry point that
/// supplies its Display Label.
///
/// Paired rather than held in two parallel arrays so the type and its accessor
/// cannot drift out of step, which is the same failure this whole audit exists
/// to prevent one level down.
struct RenderedEnum {
    std::string_view type_name;
    std::string_view label_accessor;
};

/// Every domain enum whose Display Label the Rust core owns.
///
/// These are the seven the CLI renders. Each has a bridge accessor returning
/// the core's prose, so a table here producing a string is by definition a
/// second copy of a vocabulary that already has a home.
constexpr auto RENDERED_ENUMS = std::to_array<RenderedEnum>({
    {"ScanRunContractLogDisposition", "scanner::scan_run_log_disposition_label"},
    {"ScanRunContractLogFailureStage", "scanner::scan_run_log_failure_stage_label"},
    {"ScanRunContractInfrastructureErrorStage", "scanner::scan_run_infrastructure_error_stage_label"},
    {"ScanRunLocalIgnoreResetFailureStage", "scanner::scan_run_local_ignore_reset_failure_stage_label"},
    {"ScanRunInstalledYamlDataProvenance", "scanner::scan_run_installed_yaml_data_provenance_label"},
    {"ScanRunLocalIgnoreYamlDataState", "scanner::scan_run_local_ignore_yaml_data_state_label"},
    {"ScanRunInstalledYamlDataDiagnosticKind", "scanner::scan_run_installed_yaml_data_diagnostic_kind_label"},
});

/// Returns one past the `:` terminating the `case` label starting at `case_start`.
///
/// A scoped-enum label contains `::`, so the first colon is not the terminator.
/// Skipping doubled colons is the whole trick: it separates the label from the
/// namespace and type qualifiers embedded in it.
std::size_t find_case_label_end(const std::string& source, std::size_t case_start) {
    for (std::size_t at = case_start; at < source.size(); ++at) {
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
std::size_t find_arm_body_end(const std::string& source, std::size_t body_start) {
    return std::min({source.find("case ", body_start), source.find("default:", body_start),
                     source.find("\n}", body_start), source.size()});
}

/// Counts `switch` arms on `enum_name` whose body returns a string literal.
///
/// Counting rather than naming is deliberate: this never asks whether a
/// particular function exists, so a table written into an audited file under any
/// name is found.
std::size_t count_literal_returning_arms(const std::string& source, std::string_view enum_name) {
    const std::string qualified = std::string(enum_name) + "::";
    std::size_t count = 0;
    for (std::size_t at = source.find("case "); at != std::string::npos; at = source.find("case ", at + 1)) {
        const auto label_end = find_case_label_end(source, at);
        if (label_end == std::string::npos) {
            break;
        }
        // `find` returning npos compares greater than any real offset, so an
        // arm labelled with some other enum is skipped by the same test that
        // rejects a match found past the end of this label.
        if (source.find(qualified, at) >= label_end) {
            continue;
        }
        if (source.find("return \"", label_end) < find_arm_body_end(source, label_end)) {
            ++count;
        }
    }
    return count;
}

/// Counts single-line branches naming an audited variant beside a literal return.
///
/// The `switch` scan cannot see `return kind == Kind::Parse ? "parse" : "";`,
/// which is the same table written as an expression. Pairing the two on one
/// line catches that shape without trying to parse C++.
std::size_t count_literal_returning_lines(const std::string& source, std::string_view enum_name) {
    const std::string qualified = std::string(enum_name) + "::";
    std::size_t count = 0;
    std::istringstream reader(source);
    std::string line;
    while (std::getline(reader, line)) {
        if (line.find(qualified) != std::string::npos && line.find("return \"") != std::string::npos) {
            ++count;
        }
    }
    return count;
}

/// Returns the offset of the `{` opening a body, or npos when there is none.
///
/// Stops at `;` so a forward declaration is never mistaken for a definition.
std::size_t find_body_start(const std::string& source, std::size_t at) {
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

/// Returns the offset one past the `}` closing the body opened at `body_start`.
///
/// Braces are counted naively rather than lexed. Format strings such as `"{}"`
/// carry balanced braces and so cancel out; an unbalanced one would end the
/// body early, which makes the scan read *more* text than it should. That
/// errs toward a false positive, which a contributor sees and can argue with,
/// rather than a false negative, which no one ever sees.
std::size_t find_body_end(const std::string& source, std::size_t body_start) {
    int depth = 0;
    for (std::size_t index = body_start; index < source.size(); ++index) {
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

/// Counts string literals inside string-returning functions that take `enum_name`.
///
/// This is the detector that holds when the other two do not. A naming table
/// need not be a `switch` at all — an indexed `constexpr const char*[]`, a
/// `std::unordered_map`, or a bare `default: return "unknown stage";` all
/// produce the same drift while naming neither a `case` label nor a variant
/// beside a literal. What every one of them shares is the shape: a function
/// that takes one of these enums and hands back a string. Nothing in this
/// frontend has a legitimate reason to be that function anymore, because the
/// bridge already is one.
///
/// Restricting the check to a *string-returning* signature is what keeps it
/// usable: a function that merely takes a disposition and formats a wider
/// message is not a naming table and is not counted.
std::size_t count_literals_in_label_shaped_functions(const std::string& source, std::string_view enum_name) {
    std::size_t count = 0;
    for (std::size_t at = source.find(enum_name); at != std::string::npos;
         at = source.find(enum_name, at + enum_name.size())) {
        const auto body_start = find_body_start(source, at);
        if (body_start == std::string::npos) {
            continue;
        }
        // The signature runs back to whatever terminated the previous
        // construct, so a declaration wrapped across several lines is still
        // read whole.
        const auto previous = source.find_last_of(";{}", at);
        const auto signature_start = previous == std::string::npos ? 0 : previous + 1;
        const auto signature = source.substr(signature_start, body_start - signature_start);

        // Everything before the parameter list is the return type and the
        // name. Checking only that part keeps a `std::string_view` *parameter*
        // from reading as a string return.
        const auto parameters = signature.find('(');
        if (parameters == std::string::npos) {
            continue;
        }
        const auto returns = signature.substr(0, parameters);
        if (returns.find("std::string") == std::string::npos && returns.find("char*") == std::string::npos &&
            returns.find("char *") == std::string::npos) {
            continue;
        }

        const auto body_end = find_body_end(source, body_start);
        for (auto quote = source.find('"', body_start); quote != std::string::npos && quote < body_end;
             quote = source.find('"', quote + 1)) {
            ++count;
        }
    }
    // Quotes come in pairs, so halving them reports literals rather than
    // delimiters. Escaped quotes would inflate this, but the assertion is
    // against zero, so an inflated non-zero count is still a correct verdict.
    return count / 2;
}

/// Returns the shared deny-list of phrases about a Crash Log Scan Run that no
/// frontend may write.
///
/// One file, read by all four frontend audits, rather than four inline copies.
/// A per-frontend list would put back into the test layer the four-copies drift
/// `classic-scan-presentation` exists to delete: a contributor adding core-owned
/// prose would have to remember four lists, and forgetting one would leave the
/// phrase unenforced in exactly the frontend nobody was looking at.
std::vector<std::string> core_owned_phrases() {
    const auto path = cli_root().parent_path() / "business-logic" / "classic-scan-presentation" /
                      "core-owned-phrases.txt";
    std::ifstream file(path);
    REQUIRE(file.is_open());

    std::vector<std::string> phrases;
    std::string line;
    while (std::getline(file, line)) {
        // `\r` is trimmed with the rest: the file is read as text on a repo where
        // the working copy may hold either line ending, and a trailing carriage
        // return would silently make every phrase unmatchable.
        const auto first = line.find_first_not_of(" \t\r\n");
        if (first == std::string::npos) {
            continue;
        }
        const auto last = line.find_last_not_of(" \t\r\n");
        std::string phrase = line.substr(first, last - first + 1);
        if (phrase.front() == '#') {
            continue;
        }
        phrases.push_back(std::move(phrase));
    }
    return phrases;
}

/// Returns `source` with its comments removed and everything else, string
/// literals included, intact.
///
/// Comments are excluded for the reason the CXX parity gate's name scan was
/// fixed: a comment *describing* the drift is not the drift, and this file's own
/// header quotes phrases the detector forbids. String literals are kept rather
/// than extracted because every deny-list phrase contains a space — enforced by
/// "The shared deny-list is readable and not empty" — so a phrase cannot occur
/// anywhere but a string.
///
/// String state is tracked only so a `//` or `/*` *inside* a literal does not
/// read as the start of a comment; a path or URL literal would otherwise swallow
/// the rest of its line, taking any phrase written there out of the audit.
std::string code_without_comments(const std::string& source) {
    std::string out;
    out.reserve(source.size());

    std::size_t index = 0;
    while (index < source.size()) {
        // A character literal holding a quote — `'"'` or `'\"'` — would otherwise
        // open a string that never closes where the scanner thinks it does,
        // dropping the rest of the file from the audit. That is exactly the
        // "reads as coverage while providing none" failure these guards exist to
        // prevent, so it is handled rather than left latent. A digit separator
        // (`1'000`) and any other `'` fall through to the ordinary branch, since
        // neither can be mistaken for a string.
        if (source[index] == '\'') {
            const auto escaped = index + 1 < source.size() && source[index + 1] == '\\';
            const auto close = index + (escaped ? 3 : 2);
            if (close < source.size() && source[close] == '\'') {
                index = close + 1;
                continue;
            }
        }
        // A raw string takes no escapes, so `R"(C:\dir\)"` ends at its own
        // delimiter and a `\"` inside it is two characters rather than one.
        // Handled before the ordinary-string branch, which would otherwise read
        // that backslash as an escape and run past the end of the literal.
        if (source[index] == 'R' && index + 1 < source.size() && source[index + 1] == '"') {
            // Bounded because the standard caps a raw delimiter at 16 characters
            // and forbids `(` in it. Searching to end-of-file instead would let a
            // stray `R"` synthesize a closer that never matches and silently swallow
            // the remainder of the source.
            const auto limit = std::min(index + 2 + 16, source.size());
            const auto open = source.find('(', index + 2);
            if (open != std::string::npos && open <= limit) {
                const std::string closer = ")" + source.substr(index + 2, open - (index + 2)) + "\"";
                const auto close = source.find(closer, open + 1);
                const auto body_end = close == std::string::npos ? source.size() : close;
                out.append(source, open + 1, body_end - (open + 1));
                index = close == std::string::npos ? source.size() : close + closer.size();
                continue;
            }
        }
        if (source.compare(index, 2, "//") == 0) {
            while (index < source.size() && source[index] != '\n') {
                ++index;
            }
            continue;
        }
        if (source.compare(index, 2, "/*") == 0) {
            const auto close = source.find("*/", index + 2);
            index = close == std::string::npos ? source.size() : close + 2;
            continue;
        }
        if (source[index] == '"') {
            ++index;
            while (index < source.size()) {
                if (source[index] == '\\') {
                    index += 2;
                    continue;
                }
                if (source[index] == '"') {
                    ++index;
                    break;
                }
                out.push_back(source[index]);
                ++index;
            }
            continue;
        }
        out.push_back(source[index]);
        ++index;
    }
    return out;
}

/// The sentence a frontend would reach for, written as the template it would
/// actually be written as.
///
/// `std::format`-shaped rather than a verbatim paste, because a template is the
/// shape drift takes in practice: the phrase survives and only the stage is
/// substituted. Matching a phrase rather than a whole sentence is what lets the
/// plain substring test see it.
constexpr std::string_view REWORDED_SENTENCE =
    "std::string summary(ScanRunContractInfrastructureErrorStage stage) {\n"
    "    return std::format(\"Crash Log Scan Run failed during {}\", label(stage));\n"
    "}\n";

} // namespace

TEST_CASE("No CLI source turns an audited enum into a string literal", "[display-label][audit]") {
    for (const auto& relative_path : AUDITED_SOURCES) {
        const std::string source = read_source(relative_path);
        for (const auto& rendered : RENDERED_ENUMS) {
            // Three detectors, because a naming table has more than one shape.
            // The first two read `switch` arms and single-line branches, which
            // both key on `Enum::` and so would miss a table written under
            // `using enum`. The third keys on the signature instead and needs
            // no variant to be named at all, which is what makes it the one
            // that holds when the vocabulary is hidden in a lookup container.
            const auto tables = count_literal_returning_arms(source, rendered.type_name) +
                                count_literal_returning_lines(source, rendered.type_name) +
                                count_literals_in_label_shaped_functions(source, rendered.type_name);
            INFO(relative_path << " turns " << rendered.type_name << " into " << tables
                               << " string literal(s); call " << rendered.label_accessor
                               << " instead, so the CLI, the GUI, and the TUI cannot disagree about the same "
                                  "outcome");
            // CHECK rather than REQUIRE: a contributor who reached for tables
            // usually wrote more than one, and aborting on the first would
            // report them a file at a time across as many runs as they wrote.
            CHECK(tables == 0);
        }
    }
}

TEST_CASE("Every CLI Display Label arrives inside a rendered display line", "[display-label][audit]") {
    // The negative audit above proves no table was written. This proves the
    // labels are still rendered at all: without it, deleting a call site would
    // read as compliance rather than as a frontend that stopped saying what
    // happened.
    //
    // What it checks changed when this frontend stopped composing sentences.
    // Every Display Label the CLI prints now arrives inside a `Label` segment of
    // a Rust-rendered display line, so it calls none of the seven bridge
    // accessors any more. Their absence is asserted rather than merely
    // tolerated: re-deriving a label that a segment already carries is how a
    // frontend ends up disagreeing with the sentence built around it.
    //
    // The accessors themselves stay. They remain the correct surface for
    // labelling a domain enum *outside* a display line, and the Qt GUI still
    // renders that way until its own migration lands.
    const std::string source = read_source("src/scan_run_cli.cpp");
    for (const auto& rendered : RENDERED_ENUMS) {
        INFO(rendered.label_accessor << " is called from src/scan_run_cli.cpp, but " << rendered.type_name
                                     << " is already labelled inside the display line that carries it");
        CHECK(source.find(rendered.label_accessor) == std::string::npos);
    }

    // The positive half, moved down one level: the renderer must read every
    // segment kind, because a `Label` it fails to handle is a Display Label that
    // crossed the bridge and was then silently dropped. Checking all six rather
    // than just `Label` costs nothing and catches the same mistake for a path or
    // a count.
    for (const auto& kind : {"Text", "Label", "Count", "Path", "Name", "Emphasis"}) {
        INFO("src/scan_run_cli.cpp never reads ScanRunDisplaySegmentKind::"
             << kind << ", so a segment of that kind would be rendered as something else or not at all");
        CHECK(source.find(std::string("ScanRunDisplaySegmentKind::") + kind) != std::string::npos);
    }
}

TEST_CASE("No CLI source writes a sentence the presentation crate owns", "[display-label][audit]") {
    // The naming audit above proves this frontend keeps no table of Display
    // Labels. This proves the narrower thing every frontend must show once it
    // renders display lines: that it did not reword what it was given.
    //
    // Deliberately scoped to the deny-list. A general "no format strings" rule
    // was considered and rejected as unworkably noisy — it would bury real
    // findings in false positives and get switched off, which is worse than not
    // having it.
    const auto phrases = core_owned_phrases();
    for (const auto& relative_path : AUDITED_SOURCES) {
        const std::string code = code_without_comments(read_source(relative_path));
        for (const auto& phrase : phrases) {
            INFO(relative_path << " writes \"" << phrase
                               << "\", which classic-scan-presentation already says about a Crash Log Scan "
                                  "Run; render the display lines it produces instead, so a wording fix "
                                  "lands once and reaches every frontend");
            CHECK(code.find(phrase) == std::string::npos);
        }
    }
}

TEST_CASE("The shared deny-list is readable and not empty", "[display-label][audit]") {
    // The detector loops over the deny-list, so an empty or mislocated list
    // asserts nothing while still reporting green — an audit that reads as
    // coverage while providing none. The other three audits carry the same guard
    // against the same file.
    const auto phrases = core_owned_phrases();
    CHECK(phrases.size() >= 10);
    CHECK(std::find(phrases.begin(), phrases.end(), "Crash Log Scan Run failed during") != phrases.end());

    // Every phrase must be multi-word. That is what lets this detector search
    // comment-stripped code rather than extracted literals: a phrase containing a
    // space cannot hide inside an identifier, so the only place it can appear is
    // a string.
    for (const auto& phrase : phrases) {
        INFO('"' << phrase
                 << "\" is a single word; a deny-list entry must be a phrase, or the detector cannot "
                    "tell prose from an identifier");
        CHECK(phrase.find(' ') != std::string::npos);
    }
}

TEST_CASE("The phrase detector catches the drift it exists for", "[display-label][audit]") {
    // The CLI writes none of these phrases now, so a broken detector and a
    // compliant frontend look identical from here. Feeding the detector the drift
    // it exists to catch is what tells the two apart — the same proof the TUI
    // audit carries for its naming detectors.
    //
    // Split into sections so a failure names which property broke, matching the
    // one-test-per-property shape the Rust and Qt ports use.
    SECTION("a sentence template reusing a core-owned phrase is caught") {
        const std::string drift = code_without_comments(std::string(REWORDED_SENTENCE));
        CHECK(drift.find("Crash Log Scan Run failed during") != std::string::npos);
    }

    SECTION("a comment describing the drift is documentation, not the drift") {
        const std::string commented = code_without_comments(
            "// Crash Log Scan Run failed during is core's to say.\n"
            "/* Crash Log Scan Run failed during, again. */\n"
            "int x = 1;\n");
        CHECK(commented.find("Crash Log Scan Run failed during") == std::string::npos);
    }

    SECTION("a raw string is a literal, and `//` inside one is not a comment") {
        // Without this, everything after a path or URL on the same line silently
        // leaves the audited text, taking any phrase written there with it.
        const std::string raw = code_without_comments(
            "const auto s = R\"(Crash Log Scan Run failed during)\";\n"
            "const auto u = \"https://example.invalid\";\n"
            "const auto t = \"Start the Crash Log Scan again to retry.\";\n");
        CHECK(raw.find("Crash Log Scan Run failed during") != std::string::npos);
        CHECK(raw.find("Start the Crash Log Scan again to retry.") != std::string::npos);
    }

    SECTION("a character literal holding a quote does not swallow the rest of the file") {
        // No CLI source contains one today, which is exactly why this needs a
        // test rather than a reader's vigilance: the failure would be a silent
        // hole in the audit, not a red test.
        const std::string quoted = code_without_comments(
            "const char q = '\"';\n"
            "const char e = '\\'';\n"
            "const auto s = \"Crash Log Scan Run failed during\";\n");
        CHECK(quoted.find("Crash Log Scan Run failed during") != std::string::npos);
    }

    SECTION("rendering core's own segments stays quiet") {
        // The other half of the proof. A detector that answered "drift" to
        // everything would make the audit noise a contributor learns to work
        // around, which is worse than not having it.
        const std::string compliant = code_without_comments(
            "for (const auto& segment : line.segments) { out += segment_text(segment); }\n");
        for (const auto& phrase : core_owned_phrases()) {
            INFO("concatenating core's own segments should not read as writing \"" << phrase << '"');
            CHECK(compliant.find(phrase) == std::string::npos);
        }
    }
}

TEST_CASE("The audit covers every CLI source file", "[display-label][audit]") {
    // The stale-list guard. AUDITED_SOURCES is written by hand, so a new file
    // under src/ would otherwise be unaudited from the day it lands — and a
    // naming table is most likely to appear in new code, not old.
    const std::set<std::string> audited(AUDITED_SOURCES.begin(), AUDITED_SOURCES.end());

    // Recursive, because a file added under a future `src/<subdir>/` would
    // otherwise be neither audited nor reported — silently unaudited, which is
    // the one hole this test exists to close.
    const auto source_root = cli_root() / "src";
    std::vector<std::string> unaudited;
    for (const auto& entry : fs::recursive_directory_iterator(source_root)) {
        if (!entry.is_regular_file()) {
            continue;
        }
        const auto extension = entry.path().extension().string();
        if (extension != ".cpp" && extension != ".h" && extension != ".hpp" && extension != ".cc") {
            continue;
        }
        auto relative_path = fs::relative(entry.path(), source_root).generic_string();
        relative_path = "src/" + relative_path;
        if (audited.find(relative_path) == audited.end()) {
            unaudited.push_back(relative_path);
        }
    }

    std::sort(unaudited.begin(), unaudited.end());
    std::string joined;
    for (const auto& path : unaudited) {
        joined += joined.empty() ? path : ", " + path;
    }
    INFO("add these to AUDITED_SOURCES so their Display Label handling stays audited: " << joined);
    REQUIRE(unaudited.empty());
}
