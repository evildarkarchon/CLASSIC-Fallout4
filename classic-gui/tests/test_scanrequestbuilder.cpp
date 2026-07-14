#include "core/guiusersettings.h"
#include "workers/scanrequestbuilder.h"

#include <QFile>
#include <QTemporaryDir>
#include <QtTest>

namespace {

/// Writes one persisted typed settings fixture for the adapter-to-request behavior test.
void writeSettings(const QString& root)
{
    QFile file(root + QStringLiteral("/CLASSIC Settings.yaml"));
    QVERIFY(file.open(QIODevice::WriteOnly | QIODevice::Truncate));
    const QByteArray content = QByteArrayLiteral("schema_version: \"1.0\"\n"
                                                 "CLASSIC_Settings:\n"
                                                 "  Managed Game: Fallout4\n"
                                                 "  Game Version: VR\n"
                                                 "  Game Folder Path: C:/Games/Fallout4VR\n"
                                                 "  Game EXE Path: C:/Games/Fallout4VR/Fallout4VR.exe\n"
                                                 "  Documents Folder Path: C:/Documents/Fallout4VR\n"
                                                 "  FCX Mode: true\n"
                                                 "  Simplify Logs: true\n"
                                                 "  Show FormID Values: true\n"
                                                 "  Move Unsolved Logs: false\n"
                                                 "  Unsolved Logs Destination: E:/Unsolved\n"
                                                 "  SCAN Custom Path: D:/Crash Logs\n"
                                                 "  Max Concurrent Scans: 7\n"
                                                 "  FormID Databases:\n"
                                                 "    Fallout4:\n"
                                                 "      - databases/official.db\n"
                                                 "      - E:/Databases/community.db\n");
    QCOMPARE(file.write(content), content.size());
}

} // namespace

class ScanRequestBuilderTests : public QObject {
    Q_OBJECT

private slots:
    void accepted_typed_values_populate_the_complete_rust_request();
    void persisted_snapshot_values_reach_the_rust_request_without_rereading_yaml();
};

void ScanRequestBuilderTests::accepted_typed_values_populate_the_complete_rust_request()
{
    classic::gui::CrashLogScanLaunchSettings settings;
    settings.game = QStringLiteral("Fallout4");
    settings.gameVersion = QStringLiteral("NextGen");
    settings.formIdValueLookup = true;
    settings.fcxMode = true;
    settings.simplifyLogs = true;
    settings.moveUnsolvedLogs = false;
    settings.unsolvedLogsDestination = QStringLiteral("E:/Unsolved");
    settings.maxConcurrentScans = 8;
    settings.customScanDirectory = QStringLiteral("D:/Crash Logs");
    settings.formIdDatabasePaths = {QStringLiteral("databases/official.db"),
                                    QStringLiteral("E:/Databases/community.db")};
    settings.setupGameRoot = QStringLiteral("C:/Games/Fallout4");
    settings.setupDocumentsRoot = QStringLiteral("C:/Documents/Fallout4");
    settings.setupGameExecutable = QStringLiteral("C:/Games/Fallout4/Fallout4.exe");

    const auto request = classic::gui::buildScanRunRequest(
        {QStringLiteral("D:/Crash Logs/crash-1.log")}, QStringLiteral("C:/CLASSIC"),
        QStringLiteral("C:/CLASSIC/CLASSIC Data"), QStringLiteral("C:/Portable CLASSIC"), settings,
        QStringLiteral("C:/Documents/Fallout4/F4SE/f4se.log"), true, {QStringLiteral("D:/Crash Logs/crash-1.log")});

    QCOMPARE(QString::fromStdString(std::string(request.game)), QStringLiteral("Fallout4"));
    QCOMPARE(QString::fromStdString(std::string(request.game_version)), QStringLiteral("NextGen"));
    QVERIFY(request.show_formid_values);
    QVERIFY(request.fcx_mode);
    QVERIFY(request.simplify_logs);
    QVERIFY(!request.move_unsolved_logs);
    QCOMPARE(QString::fromStdString(std::string(request.unsolved_logs_destination)), QStringLiteral("E:/Unsolved"));
    QCOMPARE(request.max_concurrent, std::uint32_t{8});
    QCOMPARE(QString::fromStdString(std::string(request.custom_scan_directory)), QStringLiteral("D:/Crash Logs"));
    QCOMPARE(request.formid_database_paths.size(), std::size_t{2});
    QCOMPARE(QString::fromStdString(std::string(request.formid_database_paths[1])),
             QStringLiteral("E:/Databases/community.db"));
    QCOMPARE(QString::fromStdString(std::string(request.configured_documents_root)),
             QStringLiteral("C:/Documents/Fallout4"));
    QCOMPARE(QString::fromStdString(std::string(request.setup_game_root)), QStringLiteral("C:/Games/Fallout4"));
    QCOMPARE(QString::fromStdString(std::string(request.setup_game_exe_path)),
             QStringLiteral("C:/Games/Fallout4/Fallout4.exe"));
    QCOMPARE(QString::fromStdString(std::string(request.setup_xse_log_path)),
             QStringLiteral("C:/Documents/Fallout4/F4SE/f4se.log"));
    QVERIFY(request.targeted_mode);
    QCOMPARE(request.targeted_inputs.size(), std::size_t{1});
    QCOMPARE(request.log_paths.size(), std::size_t{1});
}

void ScanRequestBuilderTests::persisted_snapshot_values_reach_the_rust_request_without_rereading_yaml()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    writeSettings(root.path());
    const auto snapshot = classic::gui::GuiUserSettings::open(root.path());
    const auto launch = snapshot.scanLaunchSettings(snapshot.gameSetup.managedGame);

    const auto request = classic::gui::buildScanRunRequest(
        {QStringLiteral("D:/Crash Logs/crash-1.log")}, root.path(), root.filePath(QStringLiteral("CLASSIC Data")),
        QStringLiteral("C:/Portable CLASSIC"), launch, QStringLiteral("C:/Documents/Fallout4VR/F4SE/f4sevr.log"), false,
        {});

    QCOMPARE(QString::fromStdString(std::string(request.game)), QStringLiteral("Fallout4"));
    QCOMPARE(QString::fromStdString(std::string(request.game_version)), QStringLiteral("VR"));
    QVERIFY(request.show_formid_values);
    QVERIFY(request.fcx_mode);
    QVERIFY(request.simplify_logs);
    QVERIFY(!request.move_unsolved_logs);
    QCOMPARE(QString::fromStdString(std::string(request.unsolved_logs_destination)), QStringLiteral("E:/Unsolved"));
    QCOMPARE(request.max_concurrent, std::uint32_t{7});
    QCOMPARE(QString::fromStdString(std::string(request.custom_scan_directory)), QStringLiteral("D:/Crash Logs"));
    QCOMPARE(request.formid_database_paths.size(), std::size_t{2});
    QCOMPARE(QString::fromStdString(std::string(request.formid_database_paths[0])),
             QStringLiteral("databases/official.db"));
    QCOMPARE(QString::fromStdString(std::string(request.configured_documents_root)),
             QStringLiteral("C:/Documents/Fallout4VR"));
    QCOMPARE(QString::fromStdString(std::string(request.setup_game_root)), QStringLiteral("C:/Games/Fallout4VR"));
    QCOMPARE(QString::fromStdString(std::string(request.setup_game_exe_path)),
             QStringLiteral("C:/Games/Fallout4VR/Fallout4VR.exe"));
}

QTEST_MAIN(ScanRequestBuilderTests)
#include "test_scanrequestbuilder.moc"
