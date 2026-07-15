#include "scan_run_cli.h"

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#endif

#include <atomic>
#include <chrono>
#include <fmt/format.h>
#include <thread>
#include <utility>

namespace {

namespace scanner = classic::scanner;

#ifdef _WIN32
std::atomic_bool g_console_cancel_requested{false};

/// Publishes Ctrl+C/Break without crossing into Rust from the system callback thread.
BOOL WINAPI handle_console_control(DWORD control_type) {
    if (control_type != CTRL_C_EVENT && control_type != CTRL_BREAK_EVENT) {
        return FALSE;
    }

    // The console callback may run on a system thread. It only publishes an
    // atomic request; the monitor thread calls Rust outside the callback.
    g_console_cancel_requested.store(true, std::memory_order_release);
    return TRUE;
}
#endif

std::string to_std_string(const rust::String& value) {
    return std::string(value.data(), value.size());
}

std::string plural(std::size_t count, std::string singular, std::string plural_value) {
    return count == 1 ? std::move(singular) : std::move(plural_value);
}

/// Returns the stable user-facing label for every terminal per-log disposition.
std::string log_disposition_name(scanner::ScanRunContractLogDisposition disposition) {
    switch (disposition) {
    case scanner::ScanRunContractLogDisposition::Succeeded:
        return "succeeded";
    case scanner::ScanRunContractLogDisposition::Failed:
        return "failed";
    case scanner::ScanRunContractLogDisposition::CancelledBeforeStart:
        return "cancelled before start";
    }
    return "unknown disposition";
}

/// Returns the stable user-facing label for every structured per-log failure stage.
std::string log_failure_stage_name(scanner::ScanRunContractLogFailureStage stage) {
    switch (stage) {
    case scanner::ScanRunContractLogFailureStage::Analysis:
        return "analysis";
    case scanner::ScanRunContractLogFailureStage::ReportWrite:
        return "report write";
    case scanner::ScanRunContractLogFailureStage::UnsolvedLogsFinalization:
        return "Unsolved Logs finalization";
    }
    return "unknown stage";
}

/// Returns the stable user-facing label for every run-wide infrastructure stage.
std::string infrastructure_stage_name(scanner::ScanRunContractInfrastructureErrorStage stage) {
    switch (stage) {
    case scanner::ScanRunContractInfrastructureErrorStage::RequestValidation:
        return "request validation";
    case scanner::ScanRunContractInfrastructureErrorStage::Discovery:
        return "discovery";
    case scanner::ScanRunContractInfrastructureErrorStage::Intake:
        return "intake";
    case scanner::ScanRunContractInfrastructureErrorStage::FormIdDatabaseAccess:
        return "FormID database access";
    case scanner::ScanRunContractInfrastructureErrorStage::Initialization:
        return "initialization";
    case scanner::ScanRunContractInfrastructureErrorStage::InternalInvariant:
        return "internal invariant validation";
    }
    return "unknown stage";
}

/// Appends all present run-scoped FCX setup facts, diagnostics, and actions.
void append_setup_messages(const scanner::ScanRunContractRunResult& result, std::vector<CliScanRunMessage>& messages) {
    if (!result.has_setup) {
        return;
    }

    messages.push_back({false, fmt::format("FCX setup: {}", to_std_string(result.setup.status))});
    if (result.setup.has_message) {
        messages.push_back({false, fmt::format("  {}", to_std_string(result.setup.message))});
    }
    if (!result.setup.rendered_report.empty()) {
        messages.push_back({false, to_std_string(result.setup.rendered_report)});
    }
    for (const auto& check : result.setup.checks) {
        messages.push_back({false, fmt::format("  [{}] {}: {}", to_std_string(check.state), to_std_string(check.kind),
                                               to_std_string(check.message))});
        for (const auto& detail : check.details) {
            messages.push_back({false, fmt::format("    {}", to_std_string(detail))});
        }
    }
    for (const auto& update : result.setup.path_updates) {
        messages.push_back(
            {false, fmt::format("  Proposed {} path: {}", to_std_string(update.kind), to_std_string(update.path))});
    }
    for (const auto& issue : result.setup.configuration_issues) {
        const auto section = issue.has_section ? fmt::format("/[{}]", to_std_string(issue.section_or_empty)) : "";
        messages.push_back(
            {false, fmt::format("  [{}] {}{} {}: {} (current: {}, recommended: {})", to_std_string(issue.severity),
                                to_std_string(issue.file_path), section, to_std_string(issue.setting),
                                to_std_string(issue.description), to_std_string(issue.current_value),
                                to_std_string(issue.recommended_value))});
    }
    for (const auto& action : result.setup.actions) {
        messages.push_back({false, fmt::format("  Action: {}", to_std_string(action))});
    }
    for (const auto& error : result.setup.fatal_errors) {
        messages.push_back({true, fmt::format("  Setup error: {}", to_std_string(error))});
    }
}

/// Formats one typed terminal log result without discarding structured failures.
std::string describe_log_result(const scanner::ScanRunContractLogResult& log) {
    std::string line = fmt::format("  {}. {} - {}", log.discovery_index + 1, to_std_string(log.crash_log),
                                   log_disposition_name(log.disposition));
    if (log.has_autoscan_report) {
        line += fmt::format(" (report: {})", to_std_string(log.autoscan_report));
    }
    for (const auto& failure : log.failures) {
        line += fmt::format(" [{}: {}]", log_failure_stage_name(failure.stage), to_std_string(failure.message));
    }
    if (log.has_message && log.failures.empty()) {
        line += fmt::format(" ({})", to_std_string(log.message));
    }
    if (log.moved_to_unsolved_logs) {
        line += " (moved to Unsolved Logs)";
    }
    return line;
}

/// Appends terminal per-log messages in the Rust-provided discovery order.
void append_log_messages(const scanner::ScanRunContractRunResult& result, std::vector<CliScanRunMessage>& messages) {
    if (result.logs.empty()) {
        return;
    }

    messages.push_back({false, "Results (discovery order):"});
    for (const auto& log : result.logs) {
        messages.push_back(
            {log.disposition == scanner::ScanRunContractLogDisposition::Failed, describe_log_result(log)});
    }
}

/// Projects typed User Settings into the shared final-contract configuration DTO.
scanner::ScanRunConfigurationDto make_configuration(const PreparedScanUserSettings& settings,
                                                    const std::string& yaml_dir_root,
                                                    const std::string& yaml_dir_data) {
    scanner::ScanRunConfigurationDto configuration{};
    configuration.yaml_dir_root = yaml_dir_root;
    configuration.yaml_dir_data = yaml_dir_data;
    configuration.game = settings.game;
    configuration.game_version = settings.game_version;
    configuration.show_formid_values = settings.show_formid_values;
    configuration.simplify_logs = settings.simplify_logs;
    for (const auto& path : settings.formid_database_paths) {
        configuration.formid_database_paths.push_back(path);
    }
    configuration.has_configured_unsolved_logs_destination = !settings.unsolved_logs_destination.empty();
    configuration.configured_unsolved_logs_destination = settings.unsolved_logs_destination;
    configuration.has_max_concurrent = settings.max_concurrent > 0;
    configuration.max_concurrent = settings.max_concurrent;
    return configuration;
}

/// Projects optional typed setup paths into explicit presence/value pairs for FCX requests.
scanner::ScanRunSetupContextDto make_setup_context(const PreparedScanUserSettings& settings) {
    scanner::ScanRunSetupContextDto setup{};
    setup.has_game_root = !settings.setup_game_root.empty();
    setup.game_root = settings.setup_game_root;
    setup.has_docs_root = !settings.setup_docs_root.empty();
    setup.docs_root = settings.setup_docs_root;
    setup.has_game_exe_path = !settings.setup_game_exe_path.empty();
    setup.game_exe_path = settings.setup_game_exe_path;
    setup.has_xse_log_path = !settings.setup_xse_log_path.empty();
    setup.xse_log_path = settings.setup_xse_log_path;
    return setup;
}

} // namespace

rust::Box<scanner::ScanRunRequest> build_cli_scan_run_request(const CliArgs& args,
                                                              const PreparedScanUserSettings& settings,
                                                              const std::string& yaml_dir_root,
                                                              const std::string& yaml_dir_data,
                                                              const std::string& base_directory) {
    const auto configuration = make_configuration(settings, yaml_dir_root, yaml_dir_data);
    const auto setup = make_setup_context(settings);

    if (!args.input_paths.empty()) {
        scanner::ScanRunTargetedSourceDto source{};
        for (const auto& input : args.input_paths) {
            source.inputs.push_back(input);
        }
        return settings.fcx_mode ? scanner::scan_run_request_targeted_with_fcx(configuration, source, setup)
                                 : scanner::scan_run_request_targeted(configuration, source);
    }

    scanner::ScanRunStandardSourceDto source{};
    source.base_directory = base_directory;
    source.has_custom_scan_directory = !settings.custom_scan_directory.empty();
    source.custom_scan_directory = settings.custom_scan_directory;
    source.has_configured_documents_root = !settings.configured_documents_root.empty();
    source.configured_documents_root = settings.configured_documents_root;

    const auto unsolved_logs = settings.move_unsolved_logs
                                   ? scanner::scan_run_unsolved_logs_move_to_configured_or_default()
                                   : scanner::scan_run_unsolved_logs_leave_in_place();
    return settings.fcx_mode ? scanner::scan_run_request_standard_with_fcx(configuration, source, *unsolved_logs, setup)
                             : scanner::scan_run_request_standard(configuration, source, *unsolved_logs);
}

std::vector<CliScanRunMessage> describe_cli_scan_run_event(const scanner::ScanRunContractEvent& event) {
    std::vector<CliScanRunMessage> messages;
    switch (event.kind) {
    case scanner::ScanRunContractEventKind::DiscoveryCompleted: {
        const auto accepted = event.discovery.accepted_logs.size();
        if (accepted > 0) {
            messages.push_back(
                {false, fmt::format("Found {} {}", accepted, plural(accepted, "crash log", "crash logs"))});
        }
        const auto rejected = event.discovery.rejected_inputs.size();
        if (rejected > 0) {
            messages.push_back({false, fmt::format("Rejected {} {}:", rejected,
                                                   plural(rejected, "targeted input", "targeted inputs"))});
            for (const auto& input : event.discovery.rejected_inputs) {
                messages.push_back(
                    {false, fmt::format("  {} ({})", to_std_string(input.path), to_std_string(input.reason))});
            }
        }
        break;
    }
    case scanner::ScanRunContractEventKind::EffectiveConcurrencySelected:
        messages.push_back({false, fmt::format("Scanning with {} concurrent {}", event.effective_concurrency,
                                               plural(event.effective_concurrency, "scan", "scans"))});
        break;
    case scanner::ScanRunContractEventKind::LogStarted:
        messages.push_back({false, fmt::format("Scanning {}/{}: {}", event.discovery_index + 1, event.total,
                                               to_std_string(event.crash_log))});
        break;
    case scanner::ScanRunContractEventKind::LogFinished:
        messages.push_back({event.disposition == scanner::ScanRunContractLogDisposition::Failed,
                            fmt::format("Finished {}/{}: {} - {}", event.discovery_index + 1, event.total,
                                        to_std_string(event.crash_log), log_disposition_name(event.disposition))});
        break;
    case scanner::ScanRunContractEventKind::LogQueued:
    case scanner::ScanRunContractEventKind::LogPhase:
        break;
    }
    return messages;
}

CliScanRunPresentation present_cli_scan_run_execution(const scanner::ScanRunContractExecutionResult& execution,
                                                      double duration_seconds) {
    CliScanRunPresentation presentation{};
    if (execution.has_error) {
        presentation.exit_code = 2;
        std::string message =
            fmt::format("Fatal: Crash Log Scan Run failed during {}: {}",
                        infrastructure_stage_name(execution.error.stage), to_std_string(execution.error.message));
        if (execution.error.has_path) {
            message += fmt::format(" (path: {})", to_std_string(execution.error.path));
        }
        presentation.messages.push_back({true, std::move(message)});
        return presentation;
    }
    if (!execution.has_result) {
        presentation.exit_code = 2;
        presentation.messages.push_back(
            {true, "Fatal: Crash Log Scan Run returned neither a result nor an infrastructure error."});
        return presentation;
    }

    const auto& result = execution.result;
    switch (result.status) {
    case scanner::ScanRunContractStatus::NoCrashLogsFound:
        presentation.messages.push_back(
            {false, result.has_message ? to_std_string(result.message) : "No crash logs found."});
        if (result.has_discovery) {
            for (const auto& location : result.discovery.searched_locations) {
                presentation.messages.push_back({false, fmt::format("  Searched: {}", to_std_string(location))});
            }
        }
        return presentation;
    case scanner::ScanRunContractStatus::SetupFailed:
        presentation.exit_code = 1;
        presentation.messages.push_back(
            {true, result.has_message ? to_std_string(result.message) : "Crash Log Scan setup failed."});
        append_setup_messages(result, presentation.messages);
        return presentation;
    case scanner::ScanRunContractStatus::CancelledBeforeDiscovery:
        presentation.exit_code = 130;
        presentation.messages.push_back({false, "Scan cancelled safely before discovery completed."});
        return presentation;
    case scanner::ScanRunContractStatus::Cancelled:
        presentation.exit_code = 130;
        append_setup_messages(result, presentation.messages);
        append_log_messages(result, presentation.messages);
        presentation.messages.push_back({false, fmt::format("Scan cancelled safely: {} completed, {} not started.",
                                                            result.succeeded + result.failed, result.cancelled)});
        return presentation;
    case scanner::ScanRunContractStatus::Completed:
        break;
    }

    append_setup_messages(result, presentation.messages);
    append_log_messages(result, presentation.messages);

    std::size_t reports_written = 0;
    std::size_t moved_to_unsolved_logs = 0;
    for (const auto& log : result.logs) {
        reports_written += log.has_autoscan_report ? 1 : 0;
        moved_to_unsolved_logs += log.moved_to_unsolved_logs ? 1 : 0;
    }

    presentation.messages.push_back({false, "Scan Complete"});
    presentation.messages.push_back(
        {false, fmt::format("  Scanned: {} {}", result.total, plural(result.total, "log", "logs"))});
    if (result.failed > 0) {
        presentation.messages.push_back(
            {true, fmt::format("  Errors: {} {}", result.failed, plural(result.failed, "log", "logs"))});
    }
    if (result.cancelled > 0) {
        presentation.messages.push_back({false, fmt::format("  Cancelled: {} not started", result.cancelled)});
    }
    presentation.messages.push_back({false, fmt::format("  Reports: {} written", reports_written)});
    if (moved_to_unsolved_logs > 0) {
        presentation.messages.push_back({false, fmt::format("  Unsolved: {} moved", moved_to_unsolved_logs)});
    }
    presentation.messages.push_back({false, fmt::format("  Duration: {:.2f}s", duration_seconds)});
    const auto speed = duration_seconds > 0.0 ? static_cast<double>(result.total) / duration_seconds : 0.0;
    presentation.messages.push_back({false, fmt::format("  Speed: {:.1f} logs/sec", speed)});
    presentation.exit_code = result.failed > 0 ? 1 : 0;
    return presentation;
}

class CliScanRunCancellation::Impl final {
public:
    /// Creates the Rust control before installing any platform monitor that can request it.
    explicit Impl(bool monitor_console)
        : token_(scanner::scan_run_cancellation_new()) {
#ifdef _WIN32
        if (monitor_console) {
            g_console_cancel_requested.store(false, std::memory_order_release);
            handler_installed_ = SetConsoleCtrlHandler(handle_console_control, TRUE) != 0;
            monitor_ = std::thread([this] {
                while (!stop_.load(std::memory_order_acquire)) {
                    if (g_console_cancel_requested.load(std::memory_order_acquire)) {
                        request();
                        return;
                    }
                    std::this_thread::sleep_for(std::chrono::milliseconds(25));
                }
            });
        }
#else
        (void)monitor_console;
#endif
    }

    /// Joins the monitor before unregistering the callback and releasing the token.
    ~Impl() {
        stop_.store(true, std::memory_order_release);
        if (monitor_.joinable()) {
            monitor_.join();
        }
#ifdef _WIN32
        if (handler_installed_) {
            SetConsoleCtrlHandler(handle_console_control, FALSE);
        }
        g_console_cancel_requested.store(false, std::memory_order_release);
#endif
    }

    /// Makes the monotonic request exactly once even if Ctrl+C and adapter failure race.
    void request() {
        if (!requested_.exchange(true, std::memory_order_acq_rel)) {
            scanner::scan_run_cancellation_cancel(*token_);
        }
    }

    /// Returns the live Rust control for the synchronous execution call.
    [[nodiscard]] const scanner::ScanRunCancellation& token() const noexcept { return *token_; }

private:
    rust::Box<scanner::ScanRunCancellation> token_;
    std::atomic_bool requested_{false};
    std::atomic_bool stop_{false};
    std::thread monitor_;
#ifdef _WIN32
    bool handler_installed_ = false;
#endif
};

CliScanRunCancellation::CliScanRunCancellation(bool monitor_console)
    : impl_(std::make_unique<Impl>(monitor_console)) {}

CliScanRunCancellation::~CliScanRunCancellation() = default;

void CliScanRunCancellation::request() {
    impl_->request();
}

const scanner::ScanRunCancellation& CliScanRunCancellation::token() const noexcept {
    return impl_->token();
}
