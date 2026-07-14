#include "scanrequestbuilder.h"

#include "core/rust_qt_bridge.h"

#include <cstdint>

namespace classic::gui {
namespace {

/// Converts a Qt string list into the owning CXX vector representation.
rust::Vec<rust::String> toRustStrings(const QStringList& values)
{
    rust::Vec<rust::String> converted;
    converted.reserve(static_cast<std::size_t>(values.size()));
    for (const auto& value : values) {
        converted.push_back(classic::toRustString(value));
    }
    return converted;
}

} // namespace

classic::scanner::ScanRunRequestDto buildScanRunRequest(const QStringList& logPaths, const QString& yamlRoot,
                                                        const QString& yamlData, const QString& baseDirectory,
                                                        const CrashLogScanLaunchSettings& settings,
                                                        const QString& setupXseLogPath, bool targetedMode,
                                                        const QStringList& targetedInputs)
{
    classic::scanner::ScanRunRequestDto request{};
    request.yaml_dir_root = classic::toRustString(yamlRoot);
    request.yaml_dir_data = classic::toRustString(yamlData);
    request.game = classic::toRustString(settings.game);
    request.game_version = classic::toRustString(settings.gameVersion);
    request.base_directory = classic::toRustString(baseDirectory.isEmpty() ? yamlRoot : baseDirectory);
    request.custom_scan_directory = classic::toRustString(settings.customScanDirectory);
    request.configured_documents_root = classic::toRustString(settings.setupDocumentsRoot);
    request.show_formid_values = settings.formIdValueLookup;
    request.formid_database_paths = toRustStrings(settings.formIdDatabasePaths);
    request.fcx_mode = settings.fcxMode;
    request.simplify_logs = settings.simplifyLogs;
    request.move_unsolved_logs = settings.moveUnsolvedLogs;
    request.unsolved_logs_destination = classic::toRustString(settings.unsolvedLogsDestination);
    request.targeted_mode = targetedMode;
    request.setup_game_root = classic::toRustString(settings.setupGameRoot);
    request.setup_docs_root = classic::toRustString(settings.setupDocumentsRoot);
    request.setup_game_exe_path = classic::toRustString(settings.setupGameExecutable);
    request.setup_xse_log_path = classic::toRustString(setupXseLogPath);
    request.max_concurrent =
        settings.maxConcurrentScans > 0 ? static_cast<std::uint32_t>(settings.maxConcurrentScans) : std::uint32_t{0};
    request.targeted_inputs = toRustStrings(targetedInputs);
    request.log_paths = toRustStrings(logPaths);
    return request;
}

} // namespace classic::gui
