#include "core/gamesetupusersettings.h"

#include <QDir>
#include <QFile>
#include <QTemporaryDir>
#include <QtTest/QtTest>

namespace {

/// Writes one current-schema User Settings fixture into a temporary CLASSIC root.
void writeSettings(const QString& root, const QByteArray& content)
{
    QFile file(root + QStringLiteral("/CLASSIC Settings.yaml"));
    QVERIFY2(file.open(QIODevice::WriteOnly | QIODevice::Truncate), qPrintable(file.errorString()));
    QCOMPARE(file.write(content), static_cast<qint64>(content.size()));
}

/// Returns a complete current-schema fixture with every Game Setup path populated.
QByteArray completeSettings()
{
    return QByteArrayLiteral("schema_version: \"1.0\"\n"
                             "CLASSIC_Settings:\n"
                             "  Managed Game: Fallout 4\n"
                             "  Game Version: NextGen\n"
                             "  Game Folder Path: 'D:/Games/Fallout 4'\n"
                             "  Game EXE Path: 'D:/Games/Fallout 4/Fallout4.exe'\n"
                             "  Documents Folder Path: 'D:/Documents/My Games/Fallout4'\n"
                             "  INI Folder Path: 'D:/Documents/My Games/Fallout4'\n"
                             "  MODS Folder Path: 'D:/Mod Organizer 2/mods'\n"
                             "  SCAN Custom Path: 'D:/CLASSIC/Crash Logs'\n"
                             "  Papyrus Log Path: 'D:/Documents/My Games/Fallout4/Logs/Script/Papyrus.0.log'\n");
}

} // namespace

class GameSetupUserSettingsTests : public QObject {
    Q_OBJECT

private slots:
    /// Opening a missing document reports missing state without creating a file.
    void missing_open_is_read_only();
    /// Explicit bootstrap creates a current document from Rust-owned complete defaults.
    void explicit_bootstrap_commits_rust_defaults();
    /// Selected paths cannot create a missing document unless the caller names bootstrap explicitly.
    void missing_selected_paths_require_explicit_bootstrap_operation();
    /// Opening a current document projects every saved Game Setup path byte-for-byte.
    void open_projects_every_saved_setup_path();
    /// Typed intake preserves an existing saved executable without writing User Settings.
    void read_only_intake_uses_the_saved_executable();
    /// Accepting multiple paths persists them through one atomic User Settings Update.
    void accepted_paths_commit_as_one_user_settings_update();
    /// A stale expected revision reports conflict without overwriting a newer commit.
    void stale_revision_reports_conflict_without_overwriting_newer_settings();
    /// One explicit remembered-path action leaves every unselected path unchanged.
    void one_remembered_path_action_preserves_the_other_displayed_path();
    /// Rejected path updates retain the canonical field identity for GUI feedback.
    void rejected_path_update_preserves_its_field_diagnostic();
    /// Malformed settings expose degraded state and diagnostics without rewriting bytes.
    void malformed_settings_expose_degraded_diagnostics_without_writing();
};

void GameSetupUserSettingsTests::missing_open_is_read_only()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());

    const auto snapshot = classic::gui::GameSetupUserSettings::open(root.path());

    QCOMPARE(snapshot.classification, QStringLiteral("missing"));
    QCOMPARE(snapshot.revision, QStringLiteral("missing"));
    QVERIFY(!QFile::exists(root.filePath(QStringLiteral("CLASSIC Settings.yaml"))));
}

void GameSetupUserSettingsTests::explicit_bootstrap_commits_rust_defaults()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());

    const auto outcome = classic::gui::GameSetupUserSettings::bootstrap(root.path());
    QCOMPARE(outcome.status, QStringLiteral("committed"));
    QFile persisted(root.filePath(QStringLiteral("CLASSIC Settings.yaml")));
    QVERIFY(persisted.open(QIODevice::ReadOnly));
    const QByteArray publishedDefaults = persisted.readAll();
    QVERIFY(publishedDefaults.contains("Update Check"));
    QVERIFY(publishedDefaults.contains("FCX Mode"));
    QVERIFY(publishedDefaults.contains("window_geometry"));
    QVERIFY(publishedDefaults.contains("auto_refresh_interval_ms"));

    const auto snapshot = classic::gui::GameSetupUserSettings::open(root.path());
    QCOMPARE(snapshot.classification, QStringLiteral("current"));
    QCOMPARE(snapshot.managedGame, QStringLiteral("Fallout4"));
    QCOMPARE(snapshot.gameVersionSelection, QStringLiteral("auto"));
    QVERIFY(!snapshot.gameRoot.has_value());
    QVERIFY(!snapshot.gameExecutable.has_value());
    QVERIFY(!snapshot.documentsRoot.has_value());
    QVERIFY(!snapshot.modsRoot.has_value());
    QVERIFY(!snapshot.customScanInput.has_value());
    QVERIFY(!snapshot.papyrusLog.has_value());
}

void GameSetupUserSettingsTests::missing_selected_paths_require_explicit_bootstrap_operation()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());

    classic::gui::GameSetupPathChanges changes;
    changes.gameRoot = {true, QStringLiteral("D:/Games/Fallout 4")};

    const auto ordinary =
        classic::gui::GameSetupUserSettings::commitSelectedPaths(root.path(), QStringLiteral("missing"), changes);
    QCOMPARE(ordinary.status, QStringLiteral("rejected"));
    QVERIFY(!QFile::exists(root.filePath(QStringLiteral("CLASSIC Settings.yaml"))));

    const auto bootstrapped = classic::gui::GameSetupUserSettings::bootstrapWithSelectedPaths(root.path(), changes);
    QCOMPARE(bootstrapped.status, QStringLiteral("committed"));
    const auto snapshot = classic::gui::GameSetupUserSettings::open(root.path());
    QCOMPARE(snapshot.gameRoot.value_or(QString{}), QStringLiteral("D:/Games/Fallout 4"));
}

void GameSetupUserSettingsTests::open_projects_every_saved_setup_path()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    writeSettings(root.path(), completeSettings());

    const auto snapshot = classic::gui::GameSetupUserSettings::open(root.path());

    QCOMPARE(snapshot.managedGame, QStringLiteral("Fallout4"));
    QCOMPARE(snapshot.gameVersionSelection, QStringLiteral("NextGen"));
    QVERIFY(snapshot.gameRoot.has_value());
    QVERIFY(snapshot.gameExecutable.has_value());
    QVERIFY(snapshot.documentsRoot.has_value());
    QVERIFY(snapshot.iniFolder.has_value());
    QVERIFY(snapshot.modsRoot.has_value());
    QVERIFY(snapshot.customScanInput.has_value());
    QVERIFY(snapshot.papyrusLog.has_value());
    QCOMPARE(snapshot.gameRoot.value(), QStringLiteral("D:/Games/Fallout 4"));
    QCOMPARE(snapshot.gameExecutable.value(), QStringLiteral("D:/Games/Fallout 4/Fallout4.exe"));
    QCOMPARE(snapshot.documentsRoot.value(), QStringLiteral("D:/Documents/My Games/Fallout4"));
    QCOMPARE(snapshot.iniFolder.value(), QStringLiteral("D:/Documents/My Games/Fallout4"));
    QCOMPARE(snapshot.modsRoot.value(), QStringLiteral("D:/Mod Organizer 2/mods"));
    QCOMPARE(snapshot.customScanInput.value(), QStringLiteral("D:/CLASSIC/Crash Logs"));
    QCOMPARE(snapshot.papyrusLog.value(), QStringLiteral("D:/Documents/My Games/Fallout4/Logs/Script/Papyrus.0.log"));
    QVERIFY(snapshot.diagnostics.empty());
}

void GameSetupUserSettingsTests::read_only_intake_uses_the_saved_executable()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    const QString gameRoot = root.filePath(QStringLiteral("Fallout 4"));
    const QString documentsRoot = root.filePath(QStringLiteral("Documents/Fallout4"));
    QVERIFY(QDir().mkpath(gameRoot));
    QVERIFY(QDir().mkpath(documentsRoot));
    const QString executable = QDir(gameRoot).filePath(QStringLiteral("Fallout4.exe"));
    QFile executableFile(executable);
    QVERIFY(executableFile.open(QIODevice::WriteOnly));
    executableFile.close();

    const QByteArray settings = QStringLiteral("schema_version: \"1.0\"\n"
                                               "CLASSIC_Settings:\n"
                                               "  Managed Game: Fallout 4\n"
                                               "  Game Version: auto\n"
                                               "  Game Folder Path: '%1'\n"
                                               "  Game EXE Path: '%2'\n"
                                               "  Documents Folder Path: '%3'\n")
                                    .arg(gameRoot, executable, documentsRoot)
                                    .toUtf8();
    writeSettings(root.path(), settings);

    const auto intake = classic::gui::GameSetupUserSettings::runIntake(root.path());

    QCOMPARE(QDir::cleanPath(QDir::fromNativeSeparators(intake.gameExecutable)),
             QDir::cleanPath(QDir::fromNativeSeparators(executable)));
    QFile persisted(root.filePath(QStringLiteral("CLASSIC Settings.yaml")));
    QVERIFY(persisted.open(QIODevice::ReadOnly));
    QCOMPARE(persisted.readAll(), settings);
}

void GameSetupUserSettingsTests::accepted_paths_commit_as_one_user_settings_update()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    writeSettings(root.path(), completeSettings());
    const auto before = classic::gui::GameSetupUserSettings::open(root.path());

    classic::gui::GameSetupPathChanges accepted;
    accepted.gameRoot = {true, QStringLiteral("E:/Games/Fallout 4 VR")};
    accepted.gameExecutable = {true, QStringLiteral("E:/Games/Fallout 4 VR/Fallout4VR.exe")};
    accepted.documentsRoot = {true, QStringLiteral("E:/Documents/My Games/Fallout4VR")};
    accepted.iniFolder = {true, QStringLiteral("E:/Documents/My Games/Fallout4VR")};
    accepted.modsRoot = {true, QStringLiteral("E:/Mod Organizer 2/mods")};
    accepted.customScanInput = {true, QStringLiteral("E:/CLASSIC/Crash Logs")};
    accepted.papyrusLog = {true, QStringLiteral("E:/Documents/My Games/Fallout4VR/Logs/Script/Papyrus.0.log")};

    const auto outcome =
        classic::gui::GameSetupUserSettings::commitSelectedPaths(root.path(), before.revision, accepted);
    QCOMPARE(outcome.status, QStringLiteral("committed"));

    const auto after = classic::gui::GameSetupUserSettings::open(root.path());
    QVERIFY(after.gameRoot.has_value());
    QVERIFY(after.gameExecutable.has_value());
    QVERIFY(after.documentsRoot.has_value());
    QVERIFY(after.iniFolder.has_value());
    QVERIFY(after.modsRoot.has_value());
    QVERIFY(after.customScanInput.has_value());
    QVERIFY(after.papyrusLog.has_value());
    QCOMPARE(after.gameRoot.value(), QStringLiteral("E:/Games/Fallout 4 VR"));
    QCOMPARE(after.gameExecutable.value(), QStringLiteral("E:/Games/Fallout 4 VR/Fallout4VR.exe"));
    QCOMPARE(after.documentsRoot.value(), QStringLiteral("E:/Documents/My Games/Fallout4VR"));
    QCOMPARE(after.iniFolder.value(), QStringLiteral("E:/Documents/My Games/Fallout4VR"));
    QCOMPARE(after.modsRoot.value(), QStringLiteral("E:/Mod Organizer 2/mods"));
    QCOMPARE(after.customScanInput.value(), QStringLiteral("E:/CLASSIC/Crash Logs"));
    QCOMPARE(after.papyrusLog.value(), QStringLiteral("E:/Documents/My Games/Fallout4VR/Logs/Script/Papyrus.0.log"));
}

void GameSetupUserSettingsTests::stale_revision_reports_conflict_without_overwriting_newer_settings()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    writeSettings(root.path(), completeSettings());
    const auto stale = classic::gui::GameSetupUserSettings::open(root.path());

    classic::gui::GameSetupPathChanges first;
    first.customScanInput = {true, QStringLiteral("E:/Newer Crash Logs")};
    const auto firstOutcome =
        classic::gui::GameSetupUserSettings::commitSelectedPaths(root.path(), stale.revision, first);
    QCOMPARE(firstOutcome.status, QStringLiteral("committed"));

    classic::gui::GameSetupPathChanges second;
    second.documentsRoot = {true, QStringLiteral("F:/Stale Documents")};
    const auto staleOutcome =
        classic::gui::GameSetupUserSettings::commitSelectedPaths(root.path(), stale.revision, second);
    QCOMPARE(staleOutcome.status, QStringLiteral("conflict"));
    QCOMPARE(staleOutcome.expectedRevision, stale.revision);
    QVERIFY(!staleOutcome.actualRevision.isEmpty());

    const auto current = classic::gui::GameSetupUserSettings::open(root.path());
    QVERIFY(current.customScanInput.has_value());
    QVERIFY(current.documentsRoot.has_value());
    QCOMPARE(current.customScanInput.value(), QStringLiteral("E:/Newer Crash Logs"));
    QCOMPARE(current.documentsRoot.value(), QStringLiteral("D:/Documents/My Games/Fallout4"));
}

void GameSetupUserSettingsTests::one_remembered_path_action_preserves_the_other_displayed_path()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    writeSettings(root.path(), completeSettings());
    const auto displayed = classic::gui::GameSetupUserSettings::open(root.path());

    classic::gui::GameSetupPathChanges stagingAction;
    stagingAction.modsRoot = {true, QStringLiteral("E:/Updated Mods")};
    const auto outcome =
        classic::gui::GameSetupUserSettings::commitSelectedPaths(root.path(), displayed.revision, stagingAction);

    QCOMPARE(outcome.status, QStringLiteral("committed"));
    const auto current = classic::gui::GameSetupUserSettings::open(root.path());
    QCOMPARE(current.modsRoot.value(), QStringLiteral("E:/Updated Mods"));
    QCOMPARE(current.customScanInput, displayed.customScanInput);
}

void GameSetupUserSettingsTests::rejected_path_update_preserves_its_field_diagnostic()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    writeSettings(root.path(), completeSettings());
    const auto snapshot = classic::gui::GameSetupUserSettings::open(root.path());
    classic::gui::GameSetupPathChanges invalid;
    invalid.gameRoot = {true, QStringLiteral("relative/game")};

    const auto outcome =
        classic::gui::GameSetupUserSettings::commitSelectedPaths(root.path(), snapshot.revision, invalid);

    QCOMPARE(outcome.status, QStringLiteral("rejected"));
    QVERIFY(!outcome.diagnostics.empty());
    QVERIFY(outcome.diagnostics.front().fieldPath.has_value());
    QCOMPARE(outcome.diagnostics.front().fieldPath.value(), QStringLiteral("/CLASSIC_Settings/Game Folder Path"));
}

void GameSetupUserSettingsTests::malformed_settings_expose_degraded_diagnostics_without_writing()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    const QByteArray malformed = QByteArrayLiteral("CLASSIC_Settings: [\n");
    writeSettings(root.path(), malformed);

    const auto snapshot = classic::gui::GameSetupUserSettings::open(root.path());

    QCOMPARE(snapshot.classification, QStringLiteral("malformed"));
    QCOMPARE(snapshot.commitEligibility, QStringLiteral("blocked_untrusted"));
    QVERIFY(!snapshot.diagnostics.empty());
    QFile persisted(root.filePath(QStringLiteral("CLASSIC Settings.yaml")));
    QVERIFY(persisted.open(QIODevice::ReadOnly));
    QCOMPARE(persisted.readAll(), malformed);
}

QTEST_MAIN(GameSetupUserSettingsTests)
#include "test_gamesetupusersettings.moc"
