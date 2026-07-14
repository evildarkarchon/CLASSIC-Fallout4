#include "core/guiusersettings.h"

#include <QFile>
#include <QTemporaryDir>
#include <QtTest>

namespace {

/// Writes one current-schema User Settings fixture into a temporary CLASSIC root.
void writeSettings(const QString& root, const QByteArray& content)
{
    QFile file(root + QStringLiteral("/CLASSIC Settings.yaml"));
    QVERIFY(file.open(QIODevice::WriteOnly | QIODevice::Truncate));
    QCOMPARE(file.write(content), content.size());
}

/// Returns a complete GUI-editable fixture with preservation-sensitive content.
QByteArray completeSettings()
{
    return QByteArrayLiteral("schema_version: \"1.0\"\n"
                             "CLASSIC_Settings:\n"
                             "  Update Check: true\n"
                             "  Update Source: GitHub\n"
                             "  Managed Game: Fallout4\n"
                             "  Game Version: Original\n"
                             "  Game Folder Path: C:/Games/Fallout4\n"
                             "  Game EXE Path: C:/Games/Fallout4/Fallout4.exe\n"
                             "  Documents Folder Path: C:/Users/Test/Documents/My Games/Fallout4\n"
                             "  INI Folder Path: C:/Users/Test/Documents/My Games/Fallout4\n"
                             "  FCX Mode: false\n"
                             "  Simplify Logs: false\n"
                             "  Show Statistics: true\n"
                             "  Show FormID Values: false\n"
                             "  Move Unsolved Logs: true\n"
                             "  Unsolved Logs Destination: null\n"
                             "  SCAN Custom Path: D:/Crash Logs\n"
                             "  Max Concurrent Scans: 2\n"
                             "  Audio Notifications: [preserve, invalid]\n"
                             "  FormID Databases:\n"
                             "    Fallout4:\n"
                             "      - databases/original.db\n"
                             "    Skyrim:\n"
                             "      - databases/skyrim.db\n"
                             "  Future Setting:\n"
                             "    keep: true\n"
                             "UI:\n"
                             "  preferences:\n"
                             "    auto_switch_after_scan: true\n"
                             "  window_geometry:\n"
                             "    main_tab:\n"
                             "      maximized: false\n"
                             "      width: 640\n"
                             "      height: 500\n"
                             "      future_leaf: retained\n"
                             "    results_tab:\n"
                             "      maximized: true\n"
                             "      width: 750\n"
                             "      height: 450\n"
                             "  community_frontend:\n"
                             "    theme: amber\n");
}

} // namespace

class GuiUserSettingsTests : public QObject {
    Q_OBJECT

private slots:
    void open_returns_every_gui_group_from_one_revision();
    void accepted_changes_commit_as_one_preservation_aware_update();
    void invalid_change_rejects_every_requested_field_without_writing();
    void stale_revision_reports_actionable_conflict_without_overwrite();
    void malformed_concurrent_change_still_reports_revision_conflict();
    /// A stale geometry transition replays once in Rust and refreshes the Qt snapshot after commit.
    void frontend_transition_retries_once_and_refreshes_the_consumed_snapshot();
};

void GuiUserSettingsTests::open_returns_every_gui_group_from_one_revision()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    writeSettings(root.path(), completeSettings());

    const auto snapshot = classic::gui::GuiUserSettings::open(root.path());

    QVERIFY(snapshot.update.updateCheck);
    QCOMPARE(snapshot.update.updateSource, QStringLiteral("GitHub"));
    QVERIFY(snapshot.frontend.autoSwitchAfterScan);
    const auto mainGeometry = snapshot.frontend.windowGeometry.value(classic::gui::GuiWindow::Main);
    QCOMPARE(mainGeometry.width, 640);
    QCOMPARE(mainGeometry.height, 500);
    QVERIFY(!mainGeometry.maximized);
    QCOMPARE(snapshot.scan.gameVersion, QStringLiteral("Original"));
    QVERIFY(snapshot.scan.showStatistics);
    QCOMPARE(snapshot.scan.maxConcurrentScans, 2);
    QCOMPARE(snapshot.scan.formIdDatabases.value(QStringLiteral("Fallout4")),
             QStringList{QStringLiteral("databases/original.db")});
    QCOMPARE(snapshot.gameSetup.gameRoot.value(), QStringLiteral("C:/Games/Fallout4"));
    QVERIFY(snapshot.revision.startsWith(QStringLiteral("sha256:")));

    const auto launch = snapshot.scanLaunchSettings(QStringLiteral("Fallout4"));
    QCOMPARE(launch.formIdDatabasePaths, QStringList{QStringLiteral("databases/original.db")});
    QCOMPARE(launch.maxConcurrentScans, 2);
    QCOMPARE(launch.customScanDirectory, QStringLiteral("D:/Crash Logs"));
}

void GuiUserSettingsTests::accepted_changes_commit_as_one_preservation_aware_update()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    writeSettings(root.path(), completeSettings());
    const auto before = classic::gui::GuiUserSettings::open(root.path());

    classic::gui::GuiUserSettingsChanges changes;
    changes.updateCheck = false;
    changes.autoSwitchAfterScan = false;
    changes.windowGeometry =
        classic::gui::GuiWindowGeometryChange{classic::gui::GuiWindow::Results, {false, 1280, 720}};
    changes.gameVersion = QStringLiteral("NextGen");
    changes.fcxMode = true;
    changes.simplifyLogs = true;
    changes.formIdValueLookup = true;
    changes.moveUnsolvedLogs = false;
    changes.unsolvedLogsDestination = {true, QStringLiteral("E:/Unsolved")};
    changes.maxConcurrentScans = 8;
    changes.gameRoot = {true, QStringLiteral("E:/Games/Fallout4")};
    changes.gameExecutable = {true, QStringLiteral("E:/Games/Fallout4/Fallout4.exe")};
    changes.documentsRoot = {true, QStringLiteral("E:/Documents/Fallout4")};
    changes.iniFolder = {true, QStringLiteral("E:/Documents/Fallout4")};
    changes.formIdDatabases = before.scan.formIdDatabases;
    changes.formIdDatabases->insert(QStringLiteral("Fallout4"), {QStringLiteral("databases/replacement.db")});

    const auto outcome = classic::gui::GuiUserSettings::commit(root.path(), before.revision, changes);

    QCOMPARE(outcome.status, QStringLiteral("committed"));
    const auto after = classic::gui::GuiUserSettings::open(root.path());
    QVERIFY(!after.update.updateCheck);
    QVERIFY(!after.frontend.autoSwitchAfterScan);
    const auto resultsGeometry = after.frontend.windowGeometry.value(classic::gui::GuiWindow::Results);
    QCOMPARE(resultsGeometry.width, 1280);
    QCOMPARE(resultsGeometry.height, 720);
    QVERIFY(!resultsGeometry.maximized);
    QCOMPARE(after.scan.gameVersion, QStringLiteral("NextGen"));
    QVERIFY(after.scan.fcxMode);
    QVERIFY(after.scan.simplifyLogs);
    QVERIFY(after.scan.formIdValueLookup);
    QVERIFY(!after.scan.moveUnsolvedLogs);
    QCOMPARE(after.scan.unsolvedLogsDestination.value(), QStringLiteral("E:/Unsolved"));
    QCOMPARE(after.scan.maxConcurrentScans, 8);
    QCOMPARE(after.scan.formIdDatabases.value(QStringLiteral("Fallout4")),
             QStringList{QStringLiteral("databases/replacement.db")});
    QCOMPARE(after.scan.formIdDatabases.value(QStringLiteral("Skyrim")),
             QStringList{QStringLiteral("databases/skyrim.db")});

    QFile persisted(root.filePath(QStringLiteral("CLASSIC Settings.yaml")));
    QVERIFY(persisted.open(QIODevice::ReadOnly));
    const QByteArray content = persisted.readAll();
    QVERIFY(content.contains("Future Setting:"));
    QVERIFY(content.contains("keep: true"));
    QVERIFY(content.contains("Audio Notifications:"));
    QVERIFY(content.contains("- preserve"));
    QVERIFY(content.contains("community_frontend:"));
    QVERIFY(content.contains("theme: amber"));
    QVERIFY(content.contains("future_leaf: retained"));
}

void GuiUserSettingsTests::invalid_change_rejects_every_requested_field_without_writing()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    writeSettings(root.path(), completeSettings());
    const QByteArray bytesBefore = completeSettings();
    const auto snapshot = classic::gui::GuiUserSettings::open(root.path());
    classic::gui::GuiUserSettingsChanges changes;
    changes.updateCheck = false;
    changes.unsolvedLogsDestination = {true, QStringLiteral("relative/path")};

    const auto outcome = classic::gui::GuiUserSettings::commit(root.path(), snapshot.revision, changes);

    QCOMPARE(outcome.status, QStringLiteral("rejected"));
    QCOMPARE(outcome.diagnostics.size(), std::size_t{1});
    QCOMPARE(outcome.diagnostics.front().fieldPath.value(),
             QStringLiteral("/CLASSIC_Settings/Unsolved Logs Destination"));
    QFile persisted(root.filePath(QStringLiteral("CLASSIC Settings.yaml")));
    QVERIFY(persisted.open(QIODevice::ReadOnly));
    QCOMPARE(persisted.readAll(), bytesBefore);
}

void GuiUserSettingsTests::stale_revision_reports_actionable_conflict_without_overwrite()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    writeSettings(root.path(), completeSettings());
    const auto stale = classic::gui::GuiUserSettings::open(root.path());
    classic::gui::GuiUserSettingsChanges first;
    first.maxConcurrentScans = 4;
    QCOMPARE(classic::gui::GuiUserSettings::commit(root.path(), stale.revision, first).status,
             QStringLiteral("committed"));
    const auto newer = classic::gui::GuiUserSettings::open(root.path());

    classic::gui::GuiUserSettingsChanges second;
    second.windowGeometry = classic::gui::GuiWindowGeometryChange{classic::gui::GuiWindow::Main, {true, 1600, 900}};
    const auto outcome = classic::gui::GuiUserSettings::commit(root.path(), stale.revision, second);

    QCOMPARE(outcome.status, QStringLiteral("conflict"));
    QCOMPARE(outcome.expectedRevision, stale.revision);
    QCOMPARE(outcome.actualRevision, newer.revision);
    QCOMPARE(classic::gui::GuiUserSettings::open(root.path()).scan.maxConcurrentScans, 4);
    const auto geometry =
        classic::gui::GuiUserSettings::open(root.path()).frontend.windowGeometry.value(classic::gui::GuiWindow::Main);
    QCOMPARE(geometry.width, 640);
    QCOMPARE(geometry.height, 500);
    QVERIFY(!geometry.maximized);
}

void GuiUserSettingsTests::malformed_concurrent_change_still_reports_revision_conflict()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    writeSettings(root.path(), completeSettings());
    const auto stale = classic::gui::GuiUserSettings::open(root.path());
    writeSettings(root.path(), QByteArrayLiteral("schema_version: [malformed\n"));
    classic::gui::GuiUserSettingsChanges changes;
    changes.maxConcurrentScans = 12;

    const auto outcome = classic::gui::GuiUserSettings::commit(root.path(), stale.revision, changes);

    QCOMPARE(outcome.status, QStringLiteral("conflict"));
    QCOMPARE(outcome.expectedRevision, stale.revision);
    QVERIFY(!outcome.actualRevision.isEmpty());
}

void GuiUserSettingsTests::frontend_transition_retries_once_and_refreshes_the_consumed_snapshot()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    writeSettings(root.path(), completeSettings());
    auto displayed = classic::gui::GuiUserSettings::open(root.path());

    classic::gui::GuiUserSettingsChanges concurrentChange;
    concurrentChange.maxConcurrentScans = 6;
    QCOMPARE(classic::gui::GuiUserSettings::commit(root.path(), displayed.revision, concurrentChange).status,
             QStringLiteral("committed"));

    const classic::gui::GuiWindowGeometryChange acceptedTransition{classic::gui::GuiWindow::Main, {true, 1440, 900}};
    const auto outcome =
        classic::gui::GuiUserSettings::commitFrontendTransition(root.path(), displayed, acceptedTransition);

    QCOMPARE(outcome.status, QStringLiteral("committed"));
    QCOMPARE(displayed.scan.maxConcurrentScans, 6);
    const auto geometry = displayed.frontend.windowGeometry.value(classic::gui::GuiWindow::Main);
    QVERIFY(geometry.maximized);
    QCOMPARE(geometry.width, 1440);
    QCOMPARE(geometry.height, 900);
    QCOMPARE(displayed.revision, classic::gui::GuiUserSettings::open(root.path()).revision);
}

QTEST_MAIN(GuiUserSettingsTests)
#include "test_guiusersettings.moc"
