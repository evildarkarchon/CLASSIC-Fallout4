// Qt Test coverage for the yaml-update-delivery FFI surface consumed by
// classic-gui. The GUI links classic_cxx_bridge directly (see
// `link_classic_gui_rust_bridge` in tests/CMakeLists.txt) and calls
// `classic::update::yaml_data_check_update` / `yaml_data_apply_update` /
// `yaml_data_rollback_update`; the lower-level generic `yaml_*` compatibility
// functions left the bridge with no frontend caller (#309). These tests prove
// the FFI round-trip works end to end through the Qt harness — same assurance
// the classic-cli-bridge-tests target gives the CLI side.
//
// Running requires the full MSVC + vcpkg + Qt 6 environment via
// `classic-gui/build_gui.ps1 -Test`; Qt Test binaries register with CTest
// via the `add_classic_gui_qt_test` helper.

#include <QtTest/QtTest>

#include "classic_cxx_bridge/update.h"

#include <QStringList>
#include <cstdint>

namespace {

// Tags parallel the `TAG_*` constants in
// `cpp-bindings/classic-cpp-bridge/src/update.rs`. Keep in sync when the
// bridge adds a new status case.
constexpr std::uint32_t kTagDisabled = 0u;

} // namespace

class YamlUpdateBridgeTests : public QObject {
    Q_OBJECT

private slots:
    // Verifies the `Update Check: false` short-circuit: the bridge returns
    // `tag == Disabled` without attempting any HTTP call.
    void yaml_data_check_update_disabled_short_circuits();

    // Verifies the production apply path refuses when Update Check is off, before
    // any HTTP, so an attached decision cannot install anything.
    void yaml_data_apply_update_disabled_installs_nothing();

    // Verifies the first-party rollback reports every shippable file, whether or
    // not the yaml-cache holds a previous generation for it.
    void yaml_data_rollback_update_reports_first_party_files();
};

void YamlUpdateBridgeTests::yaml_data_check_update_disabled_short_circuits()
{
    const auto status = classic::update::yaml_data_check_update(/*enabled=*/false);

    QCOMPARE(status.tag, kTagDisabled);
    QVERIFY(std::string(status.error_message).empty());
    QVERIFY(status.compatible_files.empty());
    QVERIFY(status.incompatible_files.empty());
}

void YamlUpdateBridgeTests::yaml_data_apply_update_disabled_installs_nothing()
{
    classic::update::ApprovedUpdateDto approved{};
    approved.release_tag = "yaml-data-v-test";
    approved.file_names.push_back("CLASSIC Main.yaml");
    approved.file_sha256.push_back("deadbeef");

    const auto report = classic::update::yaml_data_apply_update(/*enabled=*/false, approved);

    QVERIFY(report.installed.empty());
    QVERIFY(report.failed.empty());
    QVERIFY2(std::string(report.error_message).rfind("update check disabled:", 0) == 0,
             "A disabled apply must refuse with the stable `update check disabled:` prefix");
}

void YamlUpdateBridgeTests::yaml_data_rollback_update_reports_first_party_files()
{
    const auto report = classic::update::yaml_data_rollback_update();
    QStringList names;
    for (const auto& fileName : report.rolled_back) {
        names.push_back(QString::fromStdString(std::string(fileName)));
    }
    for (const auto& fileName : report.no_previous_version) {
        names.push_back(QString::fromStdString(std::string(fileName)));
    }
    for (const auto& fileName : report.failed_files) {
        names.push_back(QString::fromStdString(std::string(fileName)));
    }

    QVERIFY2(names.contains(QStringLiteral("CLASSIC Main.yaml")),
             "First-party rollback must include CLASSIC Main.yaml");
    QVERIFY2(names.contains(QStringLiteral("CLASSIC Fallout4.yaml")),
             "First-party rollback must include CLASSIC Fallout4.yaml");
    QCOMPARE(report.failed_files.size(), report.failure_reasons.size());
}

QTEST_MAIN(YamlUpdateBridgeTests)
#include "test_yaml_update_bridge.moc"
