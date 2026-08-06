#include "scanrequestbuilder.h"

#include "core/rust_qt_bridge.h"

#include <cstddef>
#include <stdexcept>

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

/// Converts revision-approved User Settings game text into the scanner-local typed identity.
classic::scanner::ScanRunGameId toScanRunGameId(const QString& game)
{
    if (game == QStringLiteral("Fallout4")) {
        return classic::scanner::ScanRunGameId::Fallout4;
    }
    if (game == QStringLiteral("Fallout4VR")) {
        return classic::scanner::ScanRunGameId::Fallout4VR;
    }
    if (game == QStringLiteral("Skyrim")) {
        return classic::scanner::ScanRunGameId::Skyrim;
    }
    if (game == QStringLiteral("Starfield")) {
        return classic::scanner::ScanRunGameId::Starfield;
    }
    throw std::invalid_argument(QStringLiteral("unsupported Crash Log Scan game: %1").arg(game).toStdString());
}

} // namespace

rust::Box<classic::scanner::ScanRunRequest> buildScanRunRequest(const QString& installationRoot,
                                                                const QString& baseDirectory,
                                                                const CrashLogScanLaunchSettings& settings,
                                                                const QString& setupXseLogPath,
                                                                const QStringList& targetedInputs)
{
    classic::scanner::ScanRunConfigurationDto configuration{};
    configuration.installation_root = classic::toRustString(installationRoot);
    configuration.game = toScanRunGameId(settings.game);
    configuration.game_version = classic::toRustString(settings.gameVersion);
    configuration.show_formid_values = settings.formIdValueLookup;
    configuration.simplify_logs = settings.simplifyLogs;
    configuration.formid_database_paths = toRustStrings(settings.formIdDatabasePaths);
    configuration.has_configured_unsolved_logs_destination = !settings.unsolvedLogsDestination.trimmed().isEmpty();
    configuration.configured_unsolved_logs_destination = classic::toRustString(settings.unsolvedLogsDestination);
    configuration.has_max_concurrent = settings.maxConcurrentScans > 0;
    configuration.max_concurrent =
        configuration.has_max_concurrent ? static_cast<std::size_t>(settings.maxConcurrentScans) : std::size_t{0};

    classic::scanner::ScanRunSetupContextDto setup{};
    setup.has_game_root = !settings.setupGameRoot.trimmed().isEmpty();
    setup.game_root = classic::toRustString(settings.setupGameRoot);
    setup.has_docs_root = !settings.setupDocumentsRoot.trimmed().isEmpty();
    setup.docs_root = classic::toRustString(settings.setupDocumentsRoot);
    setup.has_game_exe_path = !settings.setupGameExecutable.trimmed().isEmpty();
    setup.game_exe_path = classic::toRustString(settings.setupGameExecutable);
    setup.has_xse_log_path = !setupXseLogPath.trimmed().isEmpty();
    setup.xse_log_path = classic::toRustString(setupXseLogPath);

    if (!targetedInputs.isEmpty()) {
        classic::scanner::ScanRunTargetedSourceDto source{};
        source.inputs = toRustStrings(targetedInputs);
        return settings.fcxMode ? classic::scanner::scan_run_request_targeted_with_fcx(configuration, source, setup)
                                : classic::scanner::scan_run_request_targeted(configuration, source);
    }

    classic::scanner::ScanRunStandardSourceDto source{};
    source.base_directory = classic::toRustString(baseDirectory.isEmpty() ? installationRoot : baseDirectory);
    source.has_custom_scan_directory = !settings.customScanDirectory.trimmed().isEmpty();
    source.custom_scan_directory = classic::toRustString(settings.customScanDirectory);
    source.has_configured_documents_root = !settings.setupDocumentsRoot.trimmed().isEmpty();
    source.configured_documents_root = classic::toRustString(settings.setupDocumentsRoot);

    const auto unsolvedLogs = settings.moveUnsolvedLogs
                                  ? classic::scanner::scan_run_unsolved_logs_move_to_configured_or_default()
                                  : classic::scanner::scan_run_unsolved_logs_leave_in_place();
    return settings.fcxMode
               ? classic::scanner::scan_run_request_standard_with_fcx(configuration, source, *unsolvedLogs, setup)
               : classic::scanner::scan_run_request_standard(configuration, source, *unsolvedLogs);
}

} // namespace classic::gui
