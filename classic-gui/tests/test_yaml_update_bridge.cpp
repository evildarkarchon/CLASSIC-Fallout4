// Qt Test coverage for the yaml-update-delivery FFI surface consumed by
// classic-gui. The GUI links classic_cxx_bridge directly (see
// `link_classic_gui_rust_bridge` in tests/CMakeLists.txt) and will call
// `classic::update::yaml_data_check_update` / `yaml_data_apply_update` /
// `yaml_data_rollback_update`; the lower-level generic `yaml_check_update` /
// `yaml_apply_update` / `yaml_rollback_update` functions remain available
// for compatibility callers. These tests prove the FFI round-trip works end
// to end through the Qt harness — same assurance the classic-cli-bridge-tests
// target gives the CLI side.
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

rust::Vec<classic::update::YamlClientSchemaEntryDto> makeEntries()
{
    rust::Vec<classic::update::YamlClientSchemaEntryDto> entries;
    classic::update::YamlClientSchemaEntryDto entry{};
    entry.name = "CLASSIC Main.yaml";
    entry.accepted_major = 1u;
    entry.accepted_minimum_minor = 0u;
    entry.has_installed = false;
    entry.installed_major = 0u;
    entry.installed_minor = 0u;
    entries.push_back(std::move(entry));
    return entries;
}

} // namespace

class YamlUpdateBridgeTests : public QObject {
    Q_OBJECT

private slots:
    // Verifies the `Update Check: false` short-circuit: the bridge returns
    // `tag == Disabled` without attempting any HTTP call. The Pages URL we
    // pass is deliberately unroutable (127.0.0.1:1) so a regressed
    // short-circuit would hang or surface tag == Error instead.
    void yaml_check_update_disabled_short_circuits();
    void yaml_data_check_update_disabled_short_circuits();

    // Verifies the rollback bridge does not panic for a file the yaml-cache
    // has never heard of. Either outcome is acceptable:
    //   - `rolled_back == false` with empty error_message (cache reachable,
    //     file genuinely has no `.prev`), or
    //   - Non-empty error_message (cache dir unresolvable on a dev machine
    //     without %LOCALAPPDATA% / $HOME).
    void yaml_rollback_update_unknown_file_is_not_panic();
    void yaml_data_rollback_update_reports_first_party_files();
};

void YamlUpdateBridgeTests::yaml_check_update_disabled_short_circuits()
{
    auto entries = makeEntries();
    const auto status = classic::update::yaml_check_update(
        "http://127.0.0.1:1/manifest-latest.json",
        "yaml-data-v",
        entries,
        /*enabled=*/false,
        /*bundled_yaml_dir=*/rust::Str(""));

    QCOMPARE(status.tag, kTagDisabled);
    QVERIFY(std::string(status.error_message).empty());
    QVERIFY(status.compatible_files.empty());
    QVERIFY(status.incompatible_files.empty());
}

void YamlUpdateBridgeTests::yaml_data_check_update_disabled_short_circuits()
{
    const auto status = classic::update::yaml_data_check_update(/*enabled=*/false);

    QCOMPARE(status.tag, kTagDisabled);
    QVERIFY(std::string(status.error_message).empty());
    QVERIFY(status.compatible_files.empty());
    QVERIFY(status.incompatible_files.empty());
}

void YamlUpdateBridgeTests::yaml_rollback_update_unknown_file_is_not_panic()
{
    const auto outcome = classic::update::yaml_rollback_update(
        "__gui_bridge_definitely_nonexistent_file_xyzzy__.yaml");

    // We do not assert on the error-vs-no-error axis because a dev machine
    // may legitimately have no resolvable cache root. What we DO assert is
    // that the FFI round-trip returned a well-formed outcome and did not
    // abort the process.
    const std::string fileName(outcome.file_name);
    QVERIFY(!fileName.empty());

    if (std::string(outcome.error_message).empty()) {
        // Cache reachable → NoPreviousVersion must report rolled_back=false.
        QVERIFY(!outcome.rolled_back);
    } else {
        // Cache unreachable → surfaced as a Generic error, which the bridge
        // stringifies but does NOT raise as an exception. This is the
        // contract GUI controllers rely on: every rollback call returns a
        // value the Qt side can display, even on the error path.
        QVERIFY(!outcome.rolled_back);
        const int errorLen = static_cast<int>(std::string(outcome.error_message).size());
        QVERIFY2(errorLen > 0, "Error path must populate error_message");
    }
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
