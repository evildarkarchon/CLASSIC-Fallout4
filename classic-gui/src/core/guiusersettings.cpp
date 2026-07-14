#include "guiusersettings.h"

#include "core/rust_qt_bridge.h"

#include "classic_cxx_bridge/settings.h"

#include <QByteArray>

#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <string>
#include <utility>

namespace classic::gui {
namespace {

/// Converts a Qt string to an owning UTF-8 string without borrowing a temporary buffer.
std::string toStdString(const QString& value)
{
    const QByteArray utf8 = value.toUtf8();
    return {utf8.constData(), static_cast<std::size_t>(utf8.size())};
}

/// Converts one explicitly-present CXX optional string into its Qt representation.
std::optional<QString> optionalString(bool hasValue, const rust::String& value)
{
    return hasValue ? std::optional<QString>{classic::toQString(value)} : std::nullopt;
}

/// Copies open-time diagnostics without interpreting their stable domain codes.
std::vector<GuiUserSettingsDiagnostic>
diagnosticsFrom(const rust::Vec<classic::settings::UserSettingsDiagnosticDto>& diagnostics)
{
    std::vector<GuiUserSettingsDiagnostic> result;
    result.reserve(diagnostics.size());
    for (const auto& diagnostic : diagnostics) {
        result.push_back({classic::toQString(diagnostic.code), classic::toQString(diagnostic.message), std::nullopt});
    }
    return result;
}

/// Copies update diagnostics while preserving their optional canonical field identity.
std::vector<GuiUserSettingsDiagnostic>
diagnosticsFrom(const rust::Vec<classic::settings::UserSettingsUpdateDiagnosticDto>& diagnostics)
{
    std::vector<GuiUserSettingsDiagnostic> result;
    result.reserve(diagnostics.size());
    for (const auto& diagnostic : diagnostics) {
        result.push_back({classic::toQString(diagnostic.code), classic::toQString(diagnostic.message),
                          optionalString(diagnostic.has_field_path, diagnostic.field_path)});
    }
    return result;
}

/// Applies one selected optional string to CXX's explicit omitted/null/value representation.
void applySelection(const SelectedGuiOptionalString& selection, bool& hasField, bool& hasValue, rust::String& value)
{
    hasField = selection.selected;
    if (!selection.selected) {
        return;
    }

    hasValue = selection.value.has_value();
    value = toStdString(selection.value.value_or(QString{}));
}

/// Flattens one GUI-authored FormID database mapping into the CXX update representation.
void applyFormIdDatabases(const QMap<QString, QStringList>& databases, classic::settings::UserSettingsUpdateDto& update)
{
    update.has_formid_databases = true;
    for (auto game = databases.cbegin(); game != databases.cend(); ++game) {
        update.formid_database_games.push_back(toStdString(game.key()));
        for (const auto& path : game.value()) {
            classic::settings::FormIdDatabasePathDto entry{};
            entry.game = toStdString(game.key());
            entry.path = toStdString(path);
            update.formid_database_paths.push_back(std::move(entry));
        }
    }
}

struct GuiWindowToken {
    GuiWindow window;
    const char* token;
};

constexpr std::array kGuiWindowTokens{
    GuiWindowToken{GuiWindow::Main, "main_tab"},
    GuiWindowToken{GuiWindow::Backups, "backups_tab"},
    GuiWindowToken{GuiWindow::Articles, "articles_tab"},
    GuiWindowToken{GuiWindow::Results, "results_tab"},
};

/// Returns the stable Rust-owned token for one maintained Qt GUI window.
std::string windowToken(GuiWindow window)
{
    for (const auto& mapping : kGuiWindowTokens) {
        if (mapping.window == window) {
            return mapping.token;
        }
    }
    return "main_tab";
}

/// Parses one stable Rust-owned GUI window token without accepting arbitrary namespaces.
std::optional<GuiWindow> guiWindow(const rust::String& token)
{
    const std::string value(token);
    for (const auto& mapping : kGuiWindowTokens) {
        if (value == mapping.token) {
            return mapping.window;
        }
    }
    return std::nullopt;
}

/// Clamps a persisted unsigned dimension to the range accepted by Qt widgets.
int widgetDimension(std::uint32_t value)
{
    const auto maximum = static_cast<std::uint32_t>(std::numeric_limits<int>::max());
    return static_cast<int>(qMin(value, maximum));
}

/// Converts caller-selected GUI values into one all-or-nothing User Settings Update.
classic::settings::UserSettingsUpdateDto updateFrom(const GuiUserSettingsChanges& changes)
{
    classic::settings::UserSettingsUpdateDto update{};
    if (changes.updateCheck.has_value()) {
        update.has_update_check = true;
        update.update_check = *changes.updateCheck;
    }
    if (changes.updateSource.has_value()) {
        update.has_update_source = true;
        update.update_source = toStdString(*changes.updateSource);
    }
    if (changes.autoSwitchAfterScan.has_value()) {
        update.has_auto_switch_after_scan = true;
        update.auto_switch_after_scan = *changes.autoSwitchAfterScan;
    }
    if (changes.windowGeometry.has_value()) {
        const auto& selected = *changes.windowGeometry;
        classic::settings::UserSettingsWindowGeometryUpdateDto geometry{};
        geometry.tab = windowToken(selected.window);
        geometry.maximized = selected.geometry.maximized;
        geometry.width = selected.geometry.width;
        geometry.height = selected.geometry.height;
        update.window_geometry_updates.push_back(std::move(geometry));
    }
    if (changes.gameVersion.has_value()) {
        update.has_game_version_selection = true;
        update.game_version_selection = toStdString(*changes.gameVersion);
    }
    applySelection(changes.gameRoot, update.has_game_root, update.has_game_root_value, update.game_root);
    applySelection(changes.gameExecutable, update.has_game_executable, update.has_game_executable_value,
                   update.game_executable);
    applySelection(changes.documentsRoot, update.has_documents_root, update.has_documents_root_value,
                   update.documents_root);
    applySelection(changes.iniFolder, update.has_ini_folder, update.has_ini_folder_value, update.ini_folder);
    if (changes.fcxMode.has_value()) {
        update.has_fcx_mode = true;
        update.fcx_mode = *changes.fcxMode;
    }
    if (changes.simplifyLogs.has_value()) {
        update.has_simplify_logs = true;
        update.simplify_logs = *changes.simplifyLogs;
    }
    if (changes.showStatistics.has_value()) {
        update.has_show_statistics = true;
        update.show_statistics = *changes.showStatistics;
    }
    if (changes.formIdValueLookup.has_value()) {
        update.has_formid_value_lookup = true;
        update.formid_value_lookup = *changes.formIdValueLookup;
    }
    if (changes.formIdDatabases.has_value()) {
        applyFormIdDatabases(*changes.formIdDatabases, update);
    }
    if (changes.moveUnsolvedLogs.has_value()) {
        update.has_move_unsolved_logs = true;
        update.move_unsolved_logs = *changes.moveUnsolvedLogs;
    }
    applySelection(changes.unsolvedLogsDestination, update.has_unsolved_logs_destination,
                   update.has_unsolved_logs_destination_value, update.unsolved_logs_destination);
    if (changes.maxConcurrentScans.has_value()) {
        update.has_max_concurrent_scans = true;
        update.max_concurrent_scans = *changes.maxConcurrentScans;
    }
    return update;
}

/// Returns a caller-visible conflict when the reopened preview no longer matches the displayed revision.
GuiUserSettingsCommitResult revisionConflict(const QString& expectedRevision, const QString& actualRevision)
{
    const QString actionableActual =
        actualRevision.isEmpty() ? QStringLiteral("unavailable (missing, malformed, or incompatible)") : actualRevision;
    return {
        QStringLiteral("conflict"),
        {},
        expectedRevision,
        actionableActual,
        {{QStringLiteral("user_settings_revision_conflict"),
          QStringLiteral("User Settings changed before the GUI changes could be committed."), std::nullopt}},
    };
}

} // namespace

namespace {

/// Converts one cohesive CXX GUI projection without interpreting default policy in Qt.
GuiUserSettingsSnapshot snapshotFrom(const classic::settings::GuiSettingsSnapshotDto& settings)
{
    QMap<QString, QStringList> databases;
    for (const auto& game : settings.crash_log_scan.formid_database_games) {
        databases.insert(classic::toQString(game), {});
    }
    for (const auto& entry : settings.crash_log_scan.formid_database_paths) {
        databases[classic::toQString(entry.game)].append(classic::toQString(entry.path));
    }

    QMap<GuiWindow, GuiWindowGeometry> windowGeometry;
    for (const auto& geometry : settings.frontend_state.window_geometry) {
        if (const auto window = guiWindow(geometry.tab); window.has_value()) {
            windowGeometry.insert(
                *window, {geometry.maximized, widgetDimension(geometry.width), widgetDimension(geometry.height)});
        }
    }

    return {
        {settings.update_preferences.update_check_enabled,
         classic::toQString(settings.update_preferences.update_source)},
        {settings.crash_log_scan.fcx_mode, settings.crash_log_scan.simplify_logs,
         settings.crash_log_scan.show_statistics, settings.crash_log_scan.formid_value_lookup, std::move(databases),
         settings.crash_log_scan.move_unsolved_logs,
         optionalString(settings.crash_log_scan.has_unsolved_logs_destination,
                        settings.crash_log_scan.unsolved_logs_destination),
         optionalString(settings.crash_log_scan.has_custom_scan_input, settings.crash_log_scan.custom_scan_input),
         classic::toQString(settings.crash_log_scan.game_version_selection),
         static_cast<int>(settings.crash_log_scan.max_concurrent_scans)},
        {classic::toQString(settings.game_setup.managed_game),
         optionalString(settings.game_setup.has_game_root, settings.game_setup.game_root),
         optionalString(settings.game_setup.has_game_executable, settings.game_setup.game_executable),
         optionalString(settings.game_setup.has_documents_root, settings.game_setup.documents_root),
         optionalString(settings.game_setup.has_ini_folder, settings.game_setup.ini_folder),
         optionalString(settings.game_setup.has_mods_root, settings.game_setup.mods_root),
         optionalString(settings.game_setup.has_papyrus_log, settings.game_setup.papyrus_log)},
        {settings.frontend_state.auto_switch_after_scan, std::move(windowGeometry)},
        classic::toQString(settings.update_preferences.classification),
        classic::toQString(settings.update_preferences.revision),
        classic::toQString(settings.update_preferences.commit_eligibility),
        diagnosticsFrom(settings.update_preferences.diagnostics),
    };
}

} // namespace

CrashLogScanLaunchSettings GuiUserSettingsSnapshot::scanLaunchSettings(const QString& game) const
{
    return {
        game,
        scan.gameVersion,
        scan.formIdValueLookup,
        scan.fcxMode,
        scan.simplifyLogs,
        scan.moveUnsolvedLogs,
        scan.unsolvedLogsDestination.value_or(QString{}),
        scan.maxConcurrentScans,
        scan.customScanInput.value_or(QString{}),
        scan.formIdDatabases.value(game),
        gameSetup.gameRoot.value_or(QString{}),
        gameSetup.documentsRoot.value_or(QString{}),
        gameSetup.gameExecutable.value_or(QString{}),
    };
}

GuiUserSettingsSnapshot GuiUserSettings::open(const QString& classicRoot)
{
    return snapshotFrom(classic::settings::user_settings_open_gui_settings(toStdString(classicRoot)));
}

GuiUserSettingsSnapshot GuiUserSettings::publishedDefaults()
{
    return snapshotFrom(classic::settings::user_settings_gui_published_defaults());
}

GuiUserSettingsCommitResult GuiUserSettings::commit(const QString& classicRoot, const QString& expectedRevision,
                                                    const GuiUserSettingsChanges& changes)
{
    const std::string root = toStdString(classicRoot);
    const auto update = updateFrom(changes);
    const auto preview = classic::settings::user_settings_preview_update(root, update);
    if (!preview.accepted) {
        // Rejected previews intentionally omit a base revision, so reopen only on this path to
        // distinguish caller validation errors from an externally deleted or malformed document.
        const auto current = classic::settings::user_settings_open_gui_settings(root);
        const QString currentRevision = classic::toQString(current.update_preferences.revision);
        if (currentRevision != expectedRevision) {
            return revisionConflict(expectedRevision, currentRevision);
        }
        return {QStringLiteral("rejected"), {}, {}, {}, diagnosticsFrom(preview.diagnostics)};
    }
    const QString previewRevision = classic::toQString(preview.base_revision);
    if (previewRevision != expectedRevision) {
        return revisionConflict(expectedRevision, previewRevision);
    }

    const auto committed = classic::settings::user_settings_commit_update(root, preview.base_revision, update);
    return {
        classic::toQString(committed.status),
        classic::toQString(committed.revision),
        classic::toQString(committed.expected_revision),
        classic::toQString(committed.actual_revision),
        diagnosticsFrom(committed.diagnostics),
    };
}

GuiUserSettingsCommitResult GuiUserSettings::commitFrontendTransition(const QString& classicRoot,
                                                                      GuiUserSettingsSnapshot& snapshot,
                                                                      const GuiWindowGeometryChange& transition)
{
    classic::settings::UserSettingsWindowGeometryUpdateDto update{};
    update.tab = windowToken(transition.window);
    update.maximized = transition.geometry.maximized;
    update.width = transition.geometry.width;
    update.height = transition.geometry.height;
    const auto committed = classic::settings::user_settings_commit_frontend_geometry_transition(
        toStdString(classicRoot), toStdString(snapshot.revision), update);
    GuiUserSettingsCommitResult result{
        classic::toQString(committed.status),
        classic::toQString(committed.revision),
        classic::toQString(committed.expected_revision),
        classic::toQString(committed.actual_revision),
        diagnosticsFrom(committed.diagnostics),
    };
    if (result.status == QStringLiteral("committed")) {
        snapshot = open(classicRoot);
    }
    return result;
}

} // namespace classic::gui
