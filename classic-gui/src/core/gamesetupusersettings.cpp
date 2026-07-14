#include "gamesetupusersettings.h"

#include "core/rust_qt_bridge.h"

#include "classic_cxx_bridge/scangame.h"
#include "classic_cxx_bridge/settings.h"

#include <QByteArray>

#include <cstddef>
#include <string>
#include <utility>

namespace classic::gui {
namespace {

/// Converts a Qt string to an owning UTF-8 string without relying on a temporary C string.
std::string toStdString(const QString& value)
{
    const QByteArray utf8 = value.toUtf8();
    return {utf8.constData(), static_cast<std::size_t>(utf8.size())};
}

/// Converts one explicitly-present CXX optional string into its Qt representation.
std::optional<QString> optionalString(bool hasValue, const rust::String& value)
{
    if (!hasValue) {
        return std::nullopt;
    }
    return classic::toQString(value);
}

/// Copies open-time diagnostics without interpreting their stable domain codes.
std::vector<GameSetupUserSettingsDiagnostic>
diagnosticsFrom(const rust::Vec<classic::settings::UserSettingsDiagnosticDto>& diagnostics)
{
    std::vector<GameSetupUserSettingsDiagnostic> result;
    result.reserve(diagnostics.size());
    for (const auto& diagnostic : diagnostics) {
        result.push_back({classic::toQString(diagnostic.code), classic::toQString(diagnostic.message), std::nullopt});
    }
    return result;
}

/// Copies update diagnostics while preserving their optional canonical field identity.
std::vector<GameSetupUserSettingsDiagnostic>
diagnosticsFrom(const rust::Vec<classic::settings::UserSettingsUpdateDiagnosticDto>& diagnostics)
{
    std::vector<GameSetupUserSettingsDiagnostic> result;
    result.reserve(diagnostics.size());
    for (const auto& diagnostic : diagnostics) {
        result.push_back({classic::toQString(diagnostic.code), classic::toQString(diagnostic.message),
                          optionalString(diagnostic.has_field_path, diagnostic.field_path)});
    }
    return result;
}

/// Applies one caller selection to the explicit optional-string representation used by CXX.
void applySelection(const SelectedGameSetupPath& selection, bool& hasField, bool& hasValue, rust::String& value)
{
    hasField = selection.selected;
    if (!selection.selected) {
        return;
    }

    hasValue = selection.value.has_value();
    value = toStdString(selection.value.value_or(QString{}));
}

/// Converts selected GUI paths into one all-or-nothing User Settings Update.
classic::settings::UserSettingsUpdateDto updateFrom(const GameSetupPathChanges& changes)
{
    classic::settings::UserSettingsUpdateDto update{};
    applySelection(changes.gameRoot, update.has_game_root, update.has_game_root_value, update.game_root);
    applySelection(changes.gameExecutable, update.has_game_executable, update.has_game_executable_value,
                   update.game_executable);
    applySelection(changes.documentsRoot, update.has_documents_root, update.has_documents_root_value,
                   update.documents_root);
    applySelection(changes.iniFolder, update.has_ini_folder, update.has_ini_folder_value, update.ini_folder);
    applySelection(changes.modsRoot, update.has_mods_folder, update.has_mods_folder_value, update.mods_folder);
    applySelection(changes.customScanInput, update.has_custom_scan_input, update.has_custom_scan_input_value,
                   update.custom_scan_input);
    applySelection(changes.papyrusLog, update.has_papyrus_log_path, update.has_papyrus_log_path_value,
                   update.papyrus_log_path);
    return update;
}

/// Returns a caller-visible conflict when the reopened preview no longer matches the expected revision.
GameSetupUserSettingsCommitResult revisionConflict(const QString& expectedRevision, const QString& actualRevision)
{
    return {
        QStringLiteral("conflict"),
        {},
        expectedRevision,
        actualRevision,
        {{QStringLiteral("user_settings_revision_conflict"),
          QStringLiteral("User Settings changed before the selected Game Setup paths could be committed."),
          std::nullopt}},
    };
}

/// Converts an update-preview rejection into the same structured result used for commits.
GameSetupUserSettingsCommitResult rejectedPreview(const classic::settings::UserSettingsUpdatePreviewDto& preview)
{
    return {
        QStringLiteral("rejected"), {}, {}, {}, diagnosticsFrom(preview.diagnostics),
    };
}

/// Previews and commits one update while preserving the caller's expected revision.
GameSetupUserSettingsCommitResult commitUpdate(const QString& classicRoot, const QString& expectedRevision,
                                               const classic::settings::UserSettingsUpdateDto& update, bool bootstrap)
{
    const std::string root = toStdString(classicRoot);
    const auto preview = bootstrap ? classic::settings::user_settings_preview_bootstrap(root, update)
                                   : classic::settings::user_settings_preview_update(root, update);
    if (!preview.accepted) {
        return rejectedPreview(preview);
    }

    const QString previewRevision = classic::toQString(preview.base_revision);
    if (previewRevision != expectedRevision) {
        return revisionConflict(expectedRevision, previewRevision);
    }

    const auto committed = bootstrap
                               ? classic::settings::user_settings_commit_bootstrap(root, preview.base_revision, update)
                               : classic::settings::user_settings_commit_update(root, preview.base_revision, update);
    return {
        classic::toQString(committed.status),
        classic::toQString(committed.revision),
        classic::toQString(committed.expected_revision),
        classic::toQString(committed.actual_revision),
        diagnosticsFrom(committed.diagnostics),
    };
}

} // namespace

GameSetupUserSettingsSnapshot GameSetupUserSettings::open(const QString& classicRoot)
{
    const auto settings = classic::settings::user_settings_open_game_setup_settings(toStdString(classicRoot));
    return {
        classic::toQString(settings.managed_game),
        classic::toQString(settings.managed_game_origin),
        classic::toQString(settings.game_version_selection),
        classic::toQString(settings.game_version_selection_origin),
        optionalString(settings.has_game_root, settings.game_root),
        classic::toQString(settings.game_root_origin),
        optionalString(settings.has_game_executable, settings.game_executable),
        classic::toQString(settings.game_executable_origin),
        optionalString(settings.has_documents_root, settings.documents_root),
        classic::toQString(settings.documents_root_origin),
        optionalString(settings.has_ini_folder, settings.ini_folder),
        classic::toQString(settings.ini_folder_origin),
        optionalString(settings.has_mods_root, settings.mods_root),
        classic::toQString(settings.mods_root_origin),
        optionalString(settings.has_custom_scan_input, settings.custom_scan_input),
        classic::toQString(settings.custom_scan_input_origin),
        optionalString(settings.has_papyrus_log, settings.papyrus_log),
        classic::toQString(settings.papyrus_log_origin),
        classic::toQString(settings.classification),
        classic::toQString(settings.revision),
        classic::toQString(settings.commit_eligibility),
        diagnosticsFrom(settings.diagnostics),
    };
}

GameSetupUserSettingsCommitResult GameSetupUserSettings::bootstrap(const QString& classicRoot)
{
    const classic::settings::UserSettingsUpdateDto defaultsOnly{};
    return commitUpdate(classicRoot, QStringLiteral("missing"), defaultsOnly, true);
}

GameSetupUserSettingsCommitResult GameSetupUserSettings::bootstrapWithSelectedPaths(const QString& classicRoot,
                                                                                    const GameSetupPathChanges& changes)
{
    return commitUpdate(classicRoot, QStringLiteral("missing"), updateFrom(changes), true);
}

GameSetupUserSettingsCommitResult GameSetupUserSettings::commitSelectedPaths(const QString& classicRoot,
                                                                             const QString& expectedRevision,
                                                                             const GameSetupPathChanges& changes)
{
    return commitUpdate(classicRoot, expectedRevision, updateFrom(changes), false);
}

GameSetupUserSettingsIntakeResult GameSetupUserSettings::runIntake(const QString& classicRoot,
                                                                   const QString& xseLogPath)
{
    const auto intake =
        classic::scangame::run_game_setup_intake_from_user_settings(toStdString(classicRoot), toStdString(xseLogPath));

    std::vector<GameSetupPathProposal> pathUpdates;
    pathUpdates.reserve(intake.path_updates.size());
    for (const auto& update : intake.path_updates) {
        pathUpdates.push_back({classic::toQString(update.kind), classic::toQString(update.path)});
    }

    return {
        classic::toQString(intake.rendered_report),
        classic::toQString(intake.status),
        intake.has_errors,
        intake.total_checks,
        intake.failed_checks,
        intake.action_count,
        classic::toQString(intake.game_root),
        classic::toQString(intake.game_executable),
        classic::toQString(intake.docs_root),
        std::move(pathUpdates),
    };
}

} // namespace classic::gui
