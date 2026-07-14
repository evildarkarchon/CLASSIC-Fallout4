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
    QMap<QString, QStringList> formIdDatabases;
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

/// Revision-approved values passed from the GUI settings snapshot into one Crash Log Scan launch.
struct CrashLogScanLaunchSettings {
    QString game;
    QString gameVersion;
    bool formIdValueLookup = false;
    bool fcxMode = false;
    bool simplifyLogs = false;
    bool moveUnsolvedLogs{};
    QString unsolvedLogsDestination;
    int maxConcurrentScans{};
    QString customScanDirectory;
    QStringList formIdDatabasePaths;
    QString setupGameRoot;
    QString setupDocumentsRoot;
    QString setupGameExecutable;
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

    /// Builds an immutable scan-launch value object from this accepted typed snapshot.
    ///
    /// `game` selects the corresponding FormID database list without rereading User Settings.
    CrashLogScanLaunchSettings scanLaunchSettings(const QString& game) const;
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
    std::optional<QMap<QString, QStringList>> formIdDatabases;
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

    /// Previews and atomically commits all selected changes against `expectedRevision`.
    ///
    /// Returns `committed`, `conflict`, or `rejected`; operational publication failures
    /// propagate as bridge exceptions and never partially persist selected fields.
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
