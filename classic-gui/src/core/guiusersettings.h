#pragma once

#include <QMap>
#include <QString>
#include <QStringList>

#include <optional>
#include <vector>

namespace classic::gui {

/// One structured diagnostic returned while opening or updating GUI User Settings.
struct GuiUserSettingsDiagnostic {
    QString code;
    QString message;
    std::optional<QString> fieldPath;
};

/// Typed update preferences consumed by the native GUI.
struct GuiUpdatePreferences {
    bool updateCheck{};
    QString updateSource;
};

/// Typed Crash Log Scan User Settings consumed by the native GUI.
struct GuiCrashLogScanSettings {
    bool fcxMode = false;
    bool simplifyLogs = false;
    bool showStatistics = false;
    bool formIdValueLookup = false;
    /// Raw saved FormID rows keyed by stored game key, exactly as persisted.
    ///
    /// Read-only evidence of the stored document; the Settings dialog shows
    /// `scanFormIdDatabases` and saves through `GuiUserSettingsChanges::formIdDatabaseSave`.
    QMap<QString, QStringList> formIdDatabases;
    /// Rust-selected FormID rows that apply to each game's Crash Log Scan.
    ///
    /// Already carries the Fallout 4 VR read rule (shared Fallout4 rows, then legacy
    /// Fallout4VR rows, de-duplicated). The Settings dialog lists this projection; a Crash Log
    /// Scan does not read it, because Crash Log Scan Launch selects the same rows in Rust.
    QMap<QString, QStringList> scanFormIdDatabases;
    bool moveUnsolvedLogs{};
    std::optional<QString> unsolvedLogsDestination;
    std::optional<QString> customScanInput;
    QString gameVersion;
    int maxConcurrentScans{};
};

/// Typed Game Setup User Settings needed by the dialog and scan launch.
struct GuiGameSetupSettings {
    QString managedGame;
    std::optional<QString> gameRoot;
    std::optional<QString> gameExecutable;
    std::optional<QString> documentsRoot;
    std::optional<QString> iniFolder;
    std::optional<QString> modsRoot;
    std::optional<QString> papyrusLog;
};

/// Stable identity for one maintained native GUI window.
enum class GuiWindow {
    Main,
    Backups,
    Articles,
    Results,
};

/// Widget-independent normal-state size and maximized state for one GUI window.
struct GuiWindowGeometry {
    bool maximized{};
    int width{};
    int height{};
};

/// Typed frontend preferences edited or consumed by the native GUI.
struct GuiFrontendPreferences {
    bool autoSwitchAfterScan{};
    QMap<GuiWindow, GuiWindowGeometry> windowGeometry;
};

/// One revision-cohesive projection of every User Settings group used by the native GUI.
struct GuiUserSettingsSnapshot {
    GuiUpdatePreferences update;
    GuiCrashLogScanSettings scan;
    GuiGameSetupSettings gameSetup;
    GuiFrontendPreferences frontend;
    QString classification;
    QString revision;
    QString commitEligibility;
    std::vector<GuiUserSettingsDiagnostic> diagnostics;
};

/// One selected optional-string update; a selected null value explicitly clears the field.
struct SelectedGuiOptionalString {
    bool selected = false;
    std::optional<QString> value;
};

/// One accepted frontend-state transition for a maintained GUI window.
struct GuiWindowGeometryChange {
    GuiWindow window{};
    GuiWindowGeometry geometry;
};

/// One game's FormID database rows, saved through the Rust game-aware save.
///
/// Rust decides which stored key the rows land under: Fallout 4 VR rows are stored under
/// `Fallout4` and a legacy `Fallout4VR` key is removed (reported as a commit diagnostic);
/// every other game replaces only its own rows.
struct GuiFormIdDatabaseSave {
    QString game;
    QStringList paths;
};

/// Caller-authored GUI changes that are previewed and committed as one User Settings Update.
struct GuiUserSettingsChanges {
    std::optional<bool> updateCheck;
    std::optional<QString> updateSource;
    std::optional<bool> autoSwitchAfterScan;
    std::optional<GuiWindowGeometryChange> windowGeometry;
    std::optional<QString> gameVersion;
    SelectedGuiOptionalString gameRoot;
    SelectedGuiOptionalString gameExecutable;
    SelectedGuiOptionalString documentsRoot;
    SelectedGuiOptionalString iniFolder;
    std::optional<bool> fcxMode;
    std::optional<bool> simplifyLogs;
    std::optional<bool> showStatistics;
    std::optional<bool> formIdValueLookup;
    std::optional<GuiFormIdDatabaseSave> formIdDatabaseSave;
    std::optional<bool> moveUnsolvedLogs;
    SelectedGuiOptionalString unsolvedLogsDestination;
    std::optional<int> maxConcurrentScans;
};

/// Structured result of one explicit GUI User Settings commit.
struct GuiUserSettingsCommitResult {
    QString status;
    QString revision;
    QString expectedRevision;
    QString actualRevision;
    std::vector<GuiUserSettingsDiagnostic> diagnostics;
};

/// Thin Qt-facing adapter over the cohesive Rust-owned GUI User Settings contract.
class GuiUserSettings final {
public:
    /// Returns all GUI-consumed Rust-owned published defaults without filesystem access.
    static GuiUserSettingsSnapshot publishedDefaults();

    /// Opens all GUI-consumed typed groups from one source revision without persistence.
    static GuiUserSettingsSnapshot open(const QString& classicRoot);

    /// Previews and atomically bootstraps a missing document with all selected changes.
    ///
    /// Returns `committed`, `conflict`, or `rejected`; this operation only accepts the
    /// canonical `missing` base revision and never overwrites a concurrently created document.
    static GuiUserSettingsCommitResult bootstrap(const QString& classicRoot, const GuiUserSettingsChanges& changes);

    /// Previews and atomically commits all selected changes against `expectedRevision`.
    ///
    /// Returns `committed`, `conflict`, or `rejected`; operational publication failures
    /// propagate as bridge exceptions and never partially persist selected fields. A
    /// `committed` result may carry non-rejecting effect diagnostics (for example
    /// `legacy_formid_databases_key_removed`) that the caller should show the user.
    static GuiUserSettingsCommitResult commit(const QString& classicRoot, const QString& expectedRevision,
                                              const GuiUserSettingsChanges& changes);

    /// Commits one accepted geometry transition through the Rust-owned bounded retry operation.
    ///
    /// The supplied snapshot is refreshed after success so subsequent GUI actions consume the
    /// revision published by this transition.
    static GuiUserSettingsCommitResult commitFrontendTransition(const QString& classicRoot,
                                                                GuiUserSettingsSnapshot& snapshot,
                                                                const GuiWindowGeometryChange& transition);
};

} // namespace classic::gui
