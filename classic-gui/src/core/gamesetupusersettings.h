#pragma once

#include <QString>
#include <QtGlobal>

#include <optional>
#include <vector>

namespace classic::gui {

/// One structured diagnostic returned while opening or updating User Settings.
struct GameSetupUserSettingsDiagnostic {
    QString code;
    QString message;
    std::optional<QString> fieldPath;
};

/// Read-only typed Game Setup projection of one User Settings revision.
struct GameSetupUserSettingsSnapshot {
    QString managedGame;
    QString managedGameOrigin;
    QString gameVersionSelection;
    QString gameVersionSelectionOrigin;
    std::optional<QString> gameRoot;
    QString gameRootOrigin;
    std::optional<QString> gameExecutable;
    QString gameExecutableOrigin;
    std::optional<QString> documentsRoot;
    QString documentsRootOrigin;
    std::optional<QString> iniFolder;
    QString iniFolderOrigin;
    std::optional<QString> modsRoot;
    QString modsRootOrigin;
    std::optional<QString> customScanInput;
    QString customScanInputOrigin;
    std::optional<QString> papyrusLog;
    QString papyrusLogOrigin;
    QString classification;
    QString revision;
    QString commitEligibility;
    std::vector<GameSetupUserSettingsDiagnostic> diagnostics;
};

/// One caller-selected optional path change; a selected null value explicitly clears the path.
struct SelectedGameSetupPath {
    bool selected = false;
    std::optional<QString> value;
};

/// Caller-approved Game Setup path changes that must be committed atomically.
struct GameSetupPathChanges {
    SelectedGameSetupPath gameRoot;
    SelectedGameSetupPath gameExecutable;
    SelectedGameSetupPath documentsRoot;
    SelectedGameSetupPath iniFolder;
    SelectedGameSetupPath modsRoot;
    SelectedGameSetupPath customScanInput;
    SelectedGameSetupPath papyrusLog;
};

/// Structured result of an explicit bootstrap or selected-path commit.
struct GameSetupUserSettingsCommitResult {
    QString status;
    QString revision;
    QString expectedRevision;
    QString actualRevision;
    std::vector<GameSetupUserSettingsDiagnostic> diagnostics;
};

/// One caller-consent-gated path proposal discovered by Game Setup Intake.
struct GameSetupPathProposal {
    QString kind;
    QString path;
};

/// Read-only Game Setup Intake result prepared directly from typed User Settings.
struct GameSetupUserSettingsIntakeResult {
    QString renderedReport;
    QString status;
    bool hasErrors = false;
    quint32 totalChecks = 0;
    quint32 failedChecks = 0;
    quint32 actionCount = 0;
    QString gameRoot;
    QString gameExecutable;
    QString documentsRoot;
    std::vector<GameSetupPathProposal> pathUpdates;
};

/// Thin Qt-facing adapter over the Rust-owned User Settings and Game Setup Intake contracts.
class GameSetupUserSettings final {
public:
    /// Opens the typed Game Setup group without creating, migrating, or modifying User Settings.
    ///
    /// `classicRoot` is the directory that may contain `CLASSIC Settings.yaml`. Missing and
    /// untrusted documents return structured snapshot state and diagnostics rather than throwing.
    static GameSetupUserSettingsSnapshot open(const QString& classicRoot);

    /// Explicitly creates a missing User Settings document from Rust-owned published defaults.
    ///
    /// Returns `committed`, `conflict`, or `rejected`; operational publication failures propagate
    /// as bridge exceptions. Calling this for a non-missing revision never overwrites that document.
    static GameSetupUserSettingsCommitResult bootstrap(const QString& classicRoot);

    /// Explicitly creates a missing document from Rust defaults plus caller-approved path changes.
    ///
    /// This is the only adapter operation that can combine bootstrap with selected paths. It
    /// rejects any base other than the trusted missing revision and never overwrites an existing
    /// document.
    static GameSetupUserSettingsCommitResult bootstrapWithSelectedPaths(const QString& classicRoot,
                                                                        const GameSetupPathChanges& changes);

    /// Commits all selected path changes as one revision-anchored User Settings Update.
    ///
    /// Missing documents are rejected; callers that explicitly approve first-run creation must
    /// use `bootstrapWithSelectedPaths`. Any preview revision mismatch is returned as a conflict
    /// without attempting persistence. A selected null path explicitly clears that field;
    /// operational publication failures propagate as bridge exceptions.
    static GameSetupUserSettingsCommitResult commitSelectedPaths(const QString& classicRoot,
                                                                 const QString& expectedRevision,
                                                                 const GameSetupPathChanges& changes);

    /// Runs Game Setup Intake from the typed User Settings group without persisting proposals.
    ///
    /// `xseLogPath` is an optional detection hint not stored in User Settings. The returned path
    /// updates remain caller-consent-gated proposals.
    static GameSetupUserSettingsIntakeResult runIntake(const QString& classicRoot, const QString& xseLogPath = {});
};

} // namespace classic::gui
