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

TEST_CASE("Every CLI Display Label comes from a bridge accessor", "[display-label][audit]") {
    // The negative audit above proves no table was written. This proves the
    // labels are still rendered at all: without it, deleting a call site would
    // read as compliance rather than as a frontend that stopped saying what
    // happened. It checks the call appears, not that it is reached — the
    // behavioral half of that lives in test_scanner.cpp.
    const std::string source = read_source("src/scan_run_cli.cpp");
    for (const auto& rendered : RENDERED_ENUMS) {
        INFO(rendered.label_accessor << " is not called from src/scan_run_cli.cpp, so "
                                     << rendered.type_name << " has no Display Label to render");
        CHECK(source.find(rendered.label_accessor) != std::string::npos);
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
