// Qt Test coverage for yaml-update-delivery Section 12 — verifies the
// settings-dialog controller wiring for the YAML data-update flow.
//
// Why this is a source-inspection test, not a runtime test:
//   - The live `yaml_data_check_update` / `yaml_data_apply_update` paths hit GitHub
//     Pages over HTTPS; we already cover the FFI round-trip in
//     `test_yaml_update_bridge.cpp` (bridge reachability) and in the
//     Rust-side `update.rs` unit tests (business-logic correctness).
//   - The remaining risk at the GUI layer is *wiring drift* — a later
//     refactor dropping the `Update Check` setting from the `enabled`
//     argument, or accidentally removing the confirm prompt before
//     `yaml_apply_update`, or leaving the Apply button permanently
//     enabled. Those mistakes don't break a unit test of the bridge, but
//     they do change the source. A source-inspection test catches them
//     in the PR where they're introduced.
//
// Running requires the full MSVC + vcpkg + Qt 6 environment via
// `classic-gui/build_gui.ps1 -Test`.

#include <QFile>
#include <QRegularExpression>
#include <QtTest/QtTest>

class YamlUpdateWiringTests : public QObject {
    Q_OBJECT

private slots:
    // 12.1: the Updates tab must build three distinct buttons (check / apply /
    // rollback) and connect each to its dedicated slot. Regression guard
    // against a future refactor that, say, folds apply into the check handler.
    void settings_dialog_wires_yaml_update_buttons_to_dedicated_slots();

    // 12.1: the check slot must call the first-party bridge helper. Protects
    // against reintroducing native Pages URL / tag prefix / schema builders.
    void settings_dialog_check_slot_calls_first_party_bridge_helper();

    // 12.4: the check slot must forward `Update Check: false` by passing
    // `m_chkUpdateCheck->isChecked()` as the `enabled` argument. The bridge
    // itself short-circuits to `tag=Disabled` in that case, so this is the
    // sole wiring point that actually honors the setting in the GUI.
    void settings_dialog_check_slot_forwards_update_check_setting();

    // Both successful check outcomes must use the same incompatible-file
    // population path so their diagnostics cannot drift apart.
    void yaml_update_worker_reuses_incompatible_file_population();

    // 12.1: the apply slot must show a confirm dialog BEFORE calling the
    // bridge. An accidental re-order ("apply then confirm") would make the
    // bridge install files that the user declined.
    void settings_dialog_apply_slot_confirms_before_install();

    // 12.2: the rollback slot must show a confirm dialog and call the bridge.
    // The "disabled when no .prev" UX nuance is deferred (the bridge returns
    // a graceful outcome); at minimum the rollback path must reach the bridge
    // and handle the graceful-no-prev return.
    void settings_dialog_rollback_slot_calls_bridge_and_handles_no_prev();

    // 12.1 + 12.4: the Apply button must start disabled (nothing to apply
    // until a successful Check reveals updates). After a check that returns
    // tag=UpdateAvailable with >=1 compatible file, Apply must be re-enabled.
    // This guards the two places Apply's enabled state changes.
    void settings_dialog_apply_button_starts_disabled_and_re_enables_on_update();

    // 12.3: the CLI must register both flags and dispatch them to the
    // dedicated handlers BEFORE running the scan pipeline. An accidental
    // re-order would run the scan first and never reach the YAML update
    // handlers.
    void cli_registers_yaml_update_flags_and_dispatches_before_scan();

    // 12.4 (CLI): the CLI handler must read `CLASSIC_Settings.Update Check`
    // from the YAML settings file and pass it through to the bridge's
    // `enabled` argument. Without this, the CLI would always hit the network
    // regardless of user opt-out.
    void cli_handler_reads_update_check_setting_and_forwards_to_bridge();

    // Native callers must use first-party bridge helpers instead of duplicating
    // the channel URL, tag namespace, shippable file list, or schema ranges.
    void native_yaml_update_callers_use_first_party_bridge_helpers();
};

namespace {

QString readFile(const QString& relativePath)
{
    const QString path = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../") + relativePath;
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return {};
    }
    return QString::fromUtf8(file.readAll());
}

bool containsNativeYamlRecipeDuplication(const QString& source)
{
    const QStringList forbidden{
        QStringLiteral("YamlClientSchemaEntryDto"),
        QStringLiteral("kYamlPagesUrl"),
        QStringLiteral("kYamlTagPrefix"),
        QStringLiteral("https://evildarkarchon.github.io/CLASSIC-Fallout4/yaml-data/manifest-latest.json"),
        QStringLiteral("\"yaml-data-v\""),
        QStringLiteral("accepted_major"),
        QStringLiteral("accepted_minimum_minor"),
    };
    for (const auto& needle : forbidden) {
        if (source.contains(needle)) {
            return true;
        }
    }
    return false;
}

} // namespace

void YamlUpdateWiringTests::settings_dialog_wires_yaml_update_buttons_to_dedicated_slots()
{
    const QString source = readFile(QStringLiteral("src/app/settingsdialog.cpp"));
    QVERIFY2(!source.isEmpty(), "settingsdialog.cpp must be readable");

    QVERIFY2(source.contains(QStringLiteral("m_btnCheckYamlUpdates = new QPushButton")),
             "SettingsDialog should create a dedicated Check Data Updates button");
    QVERIFY2(source.contains(QStringLiteral("m_btnApplyYamlUpdates = new QPushButton")),
             "SettingsDialog should create a dedicated Apply Data Updates button");
    QVERIFY2(source.contains(QStringLiteral("m_btnRollbackYamlUpdates = new QPushButton")),
             "SettingsDialog should create a dedicated Rollback Data Update button");

    QVERIFY2(source.contains(QStringLiteral("&SettingsDialog::onCheckForYamlUpdates")),
             "Check button should connect to onCheckForYamlUpdates");
    QVERIFY2(source.contains(QStringLiteral("&SettingsDialog::onApplyYamlUpdates")),
             "Apply button should connect to onApplyYamlUpdates");
    QVERIFY2(source.contains(QStringLiteral("&SettingsDialog::onRollbackYamlUpdate")),
             "Rollback button should connect to onRollbackYamlUpdate");
}

void YamlUpdateWiringTests::settings_dialog_check_slot_calls_first_party_bridge_helper()
{
    // Post-async-refactor: the bridge call itself lives in the worker
    // translation unit. The dialog dispatches to the worker via
    // `QMetaObject::invokeMethod` with a named slot. This test covers
    // both halves of the split so regressions in either file surface.
    const QString worker = readFile(QStringLiteral("src/workers/yamlupdateworker.cpp"));
    QVERIFY2(!worker.isEmpty(), "yamlupdateworker.cpp must be readable");

    QVERIFY2(worker.contains(QStringLiteral("classic::update::yaml_data_check_update(")),
             "YamlUpdateWorker::doCheck should call the first-party yaml_data_check_update bridge");
    QVERIFY2(!containsNativeYamlRecipeDuplication(worker),
             "YamlUpdateWorker must not duplicate Pages URL, tag prefix, or schema entries");

    const QString dialog = readFile(QStringLiteral("src/app/settingsdialog.cpp"));
    QVERIFY2(!dialog.isEmpty(), "settingsdialog.cpp must be readable");
    QVERIFY2(dialog.contains(QStringLiteral("invokeMethod(m_yamlUpdateWorker, \"doCheck\"")),
             "onCheckForYamlUpdates should dispatch to the worker's doCheck slot");
}

void YamlUpdateWiringTests::settings_dialog_check_slot_forwards_update_check_setting()
{
    const QString dialog = readFile(QStringLiteral("src/app/settingsdialog.cpp"));
    QVERIFY2(!dialog.isEmpty(), "settingsdialog.cpp must be readable");

    // The check slot must read the checkbox and pass the value as the
    // `enabled` arg to the worker. Regex allows whitespace/reformatting.
    const QRegularExpression gating(
        QStringLiteral(R"(m_chkUpdateCheck\s*&&\s*m_chkUpdateCheck->isChecked\(\))"));
    QVERIFY2(gating.match(dialog).hasMatch(),
             "onCheckForYamlUpdates should derive `enabled` from m_chkUpdateCheck->isChecked()");

    const QRegularExpression invoke(
        QStringLiteral(R"(invokeMethod\(\s*m_yamlUpdateWorker\s*,\s*"doCheck"[^)]*Q_ARG\(\s*bool\s*,\s*enabled\s*\))"));
    QVERIFY2(invoke.match(dialog).hasMatch(),
             "onCheckForYamlUpdates must forward the Update Check setting as the bool arg to doCheck");

    // And the worker must actually pass `enabled` through to the first-party
    // bridge helper.
    const QString worker = readFile(QStringLiteral("src/workers/yamlupdateworker.cpp"));
    const QRegularExpression call(
        QStringLiteral(R"(yaml_data_check_update\(\s*enabled\s*\))"));
    QVERIFY2(call.match(worker).hasMatch(),
             "YamlUpdateWorker::doCheck must pass the enabled flag through to yaml_data_check_update");
}

void YamlUpdateWiringTests::yaml_update_worker_reuses_incompatible_file_population()
{
    const QString worker = readFile(QStringLiteral("src/workers/yamlupdateworker.cpp"));
    QVERIFY2(!worker.isEmpty(), "yamlupdateworker.cpp must be readable");

    QCOMPARE(worker.count(QStringLiteral("populateIncompatibleFiles();")), 2);
    QCOMPARE(worker.count(QStringLiteral("result.incompatibleFileNames.push_back")), 1);
    QCOMPARE(worker.count(QStringLiteral("result.incompatibleReasons.push_back")), 1);
}

void YamlUpdateWiringTests::settings_dialog_apply_slot_confirms_before_install()
{
    const QString source = readFile(QStringLiteral("src/app/settingsdialog.cpp"));
    QVERIFY2(!source.isEmpty(), "settingsdialog.cpp must be readable");

    const qsizetype applyStart = source.indexOf(QStringLiteral("void SettingsDialog::onApplyYamlUpdates()"));
    QVERIFY2(applyStart >= 0, "onApplyYamlUpdates must exist");
    const qsizetype nextFn = source.indexOf(QStringLiteral("\nvoid SettingsDialog::"), applyStart + 1);
    const QString body = source.mid(applyStart, (nextFn < 0 ? source.size() : nextFn) - applyStart);

    // Post-async-refactor: confirm must happen before dispatch to the
    // worker (which is what actually calls the bridge). An accidental
    // reorder would kick off a download before the user confirmed.
    const qsizetype confirmIdx = body.indexOf(QStringLiteral("QMessageBox::question"));
    const qsizetype dispatchIdx = body.indexOf(QStringLiteral("invokeMethod(m_yamlUpdateWorker, \"doApply\""));
    QVERIFY2(confirmIdx >= 0, "onApplyYamlUpdates should show a confirm dialog");
    QVERIFY2(dispatchIdx >= 0, "onApplyYamlUpdates should dispatch the apply work to the worker");
    QVERIFY2(confirmIdx < dispatchIdx,
             "onApplyYamlUpdates must confirm BEFORE dispatching the apply — order matters");

    // And the worker must call the bridge with the approved decision.
    const QString worker = readFile(QStringLiteral("src/workers/yamlupdateworker.cpp"));
    QVERIFY2(worker.contains(QStringLiteral("classic::update::yaml_data_apply_update(")),
             "YamlUpdateWorker::doApply should call the first-party yaml_data_apply_update bridge");
    QVERIFY2(worker.contains(QStringLiteral("approvedTag")) &&
                 worker.contains(QStringLiteral("approvedNames")),
             "YamlUpdateWorker::doApply must forward the approved release tag and file names");
}

void YamlUpdateWiringTests::settings_dialog_rollback_slot_calls_bridge_and_handles_no_prev()
{
    const QString dialog = readFile(QStringLiteral("src/app/settingsdialog.cpp"));
    QVERIFY2(!dialog.isEmpty(), "settingsdialog.cpp must be readable");

    const qsizetype rollbackStart = dialog.indexOf(QStringLiteral("void SettingsDialog::onRollbackYamlUpdate()"));
    QVERIFY2(rollbackStart >= 0, "onRollbackYamlUpdate must exist");
    const qsizetype nextFn = dialog.indexOf(QStringLiteral("\nvoid SettingsDialog::"), rollbackStart + 1);
    const QString body = dialog.mid(rollbackStart,
                                    (nextFn < 0 ? dialog.size() : nextFn) - rollbackStart);

    // The slot dispatches the actual work to the worker; the handler
    // (`onYamlRollbackFinished`) surfaces the "no previous version" text.
    QVERIFY2(body.contains(QStringLiteral("invokeMethod(m_yamlUpdateWorker, \"doRollback\"")),
             "onRollbackYamlUpdate should dispatch to the worker's doRollback slot");
    QVERIFY2(dialog.contains(QStringLiteral("No previous version")),
             "SettingsDialog must surface a \"no previous version\" message for the graceful-no-prev outcome");

    // And the worker does the actual bridge call + categorization.
    const QString worker = readFile(QStringLiteral("src/workers/yamlupdateworker.cpp"));
    QVERIFY2(worker.contains(QStringLiteral("classic::update::yaml_data_rollback_update(")),
             "YamlUpdateWorker::doRollback should call the first-party yaml_data_rollback_update bridge");
    QVERIFY2(worker.contains(QStringLiteral("rolled_back")),
             "YamlUpdateWorker::doRollback should inspect rolled_back results");
    QVERIFY2(worker.contains(QStringLiteral("no_previous_version")),
             "YamlUpdateWorker::doRollback should inspect no_previous_version results");
    QVERIFY2(worker.contains(QStringLiteral("failed_files")),
             "YamlUpdateWorker::doRollback should inspect failed_files results");
    QVERIFY2(worker.contains(QStringLiteral("failure_reasons")),
             "YamlUpdateWorker::doRollback should inspect failure_reasons results");
}

void YamlUpdateWiringTests::settings_dialog_apply_button_starts_disabled_and_re_enables_on_update()
{
    const QString source = readFile(QStringLiteral("src/app/settingsdialog.cpp"));
    QVERIFY2(!source.isEmpty(), "settingsdialog.cpp must be readable");

    // The tab-building code must call setEnabled(false) on the Apply button
    // at construction time — the disabled-by-default UX invariant.
    const QRegularExpression initialDisabled(
        QStringLiteral(R"(m_btnApplyYamlUpdates->setEnabled\(false\))"));
    QVERIFY2(initialDisabled.match(source).hasMatch(),
             "Apply button must start disabled (nothing to apply until Check reveals updates)");

    // Post-async-refactor: the re-enable happens in the queued-result
    // handler, not in the button slot. Anchor the test on the handler.
    const qsizetype handlerStart = source.indexOf(QStringLiteral("void SettingsDialog::onYamlCheckFinished"));
    QVERIFY2(handlerStart >= 0, "onYamlCheckFinished must exist to receive worker results");
    const qsizetype nextFn = source.indexOf(QStringLiteral("\nvoid SettingsDialog::"), handlerStart + 1);
    const QString body = source.mid(handlerStart,
                                    (nextFn < 0 ? source.size() : nextFn) - handlerStart);
    QVERIFY2(body.contains(QStringLiteral("m_btnApplyYamlUpdates->setEnabled(count > 0)")),
             "onYamlCheckFinished must re-enable Apply when compatible files are available");
}

void YamlUpdateWiringTests::cli_registers_yaml_update_flags_and_dispatches_before_scan()
{
    const QString argsSource = readFile(QStringLiteral("../classic-cli/src/cli_args.cpp"));
    QVERIFY2(!argsSource.isEmpty(), "classic-cli/src/cli_args.cpp must be readable");

    QVERIFY2(argsSource.contains(QStringLiteral("--check-yaml-updates")),
             "CLI should register a --check-yaml-updates flag");
    QVERIFY2(argsSource.contains(QStringLiteral("--apply-yaml-updates")),
             "CLI should register an --apply-yaml-updates flag");
    QVERIFY2(argsSource.contains(QStringLiteral("--rollback-yaml-updates")),
             "CLI should register a --rollback-yaml-updates flag");

    const QString mainSource = readFile(QStringLiteral("../classic-cli/src/main.cpp"));
    QVERIFY2(!mainSource.isEmpty(), "classic-cli/src/main.cpp must be readable");

    const qsizetype applyIdx = mainSource.indexOf(QStringLiteral("run_apply_yaml_updates(args)"));
    const qsizetype checkIdx = mainSource.indexOf(QStringLiteral("run_check_yaml_updates(args)"));
    const qsizetype scanIdx = mainSource.indexOf(QStringLiteral("run_scan(args)"));

    QVERIFY2(applyIdx >= 0, "main.cpp should dispatch to run_apply_yaml_updates");
    QVERIFY2(checkIdx >= 0, "main.cpp should dispatch to run_check_yaml_updates");
    QVERIFY2(scanIdx >= 0, "main.cpp should still have the run_scan fallback");
    QVERIFY2(applyIdx < scanIdx && checkIdx < scanIdx,
             "main.cpp must dispatch YAML update handlers BEFORE falling through to run_scan");
}

void YamlUpdateWiringTests::cli_handler_reads_update_check_setting_and_forwards_to_bridge()
{
    const QString handlerSource = readFile(QStringLiteral("../classic-cli/src/yaml_update.cpp"));
    QVERIFY2(!handlerSource.isEmpty(), "classic-cli/src/yaml_update.cpp must be readable");

    QVERIFY2(handlerSource.contains(QStringLiteral("CLASSIC_Settings.Update Check")),
             "CLI YAML update handler must read the CLASSIC_Settings.Update Check setting");
    QVERIFY2(handlerSource.contains(QStringLiteral("read_update_check_setting")),
             "CLI handler should use a dedicated setting-reader helper");

    // The `enabled` variable derived from the setting must be forwarded to
    // the first-party YAML Data check helper.
    const QRegularExpression forward(
        QStringLiteral(R"(yaml_data_check_update\(\s*enabled\s*\))"));
    QVERIFY2(forward.match(handlerSource).hasMatch(),
             "CLI handler must pass the Update Check setting to yaml_data_check_update");
}

void YamlUpdateWiringTests::native_yaml_update_callers_use_first_party_bridge_helpers()
{
    const QString cliSource = readFile(QStringLiteral("../classic-cli/src/yaml_update.cpp"));
    QVERIFY2(!cliSource.isEmpty(), "classic-cli/src/yaml_update.cpp must be readable");
    QVERIFY2(cliSource.contains(QStringLiteral("classic::update::yaml_data_check_update(")),
             "CLI check path should call yaml_data_check_update");
    QVERIFY2(cliSource.contains(QStringLiteral("classic::update::yaml_data_apply_update(")),
             "CLI apply path should call yaml_data_apply_update");
    QVERIFY2(cliSource.contains(QStringLiteral("classic::update::yaml_data_rollback_update(")),
             "CLI rollback path should call yaml_data_rollback_update");
    QVERIFY2(!containsNativeYamlRecipeDuplication(cliSource),
             "CLI must not duplicate YAML Data channel constants or schema entries");

    const QString dialogSource = readFile(QStringLiteral("src/app/settingsdialog.cpp"));
    QVERIFY2(!dialogSource.isEmpty(), "settingsdialog.cpp must be readable");
    QVERIFY2(!containsNativeYamlRecipeDuplication(dialogSource),
             "SettingsDialog must not duplicate YAML Data channel constants or schema entries");

    const QString workerSource = readFile(QStringLiteral("src/workers/yamlupdateworker.cpp"));
    QVERIFY2(!workerSource.isEmpty(), "yamlupdateworker.cpp must be readable");
    QVERIFY2(workerSource.contains(QStringLiteral("classic::update::yaml_data_check_update(")),
             "YamlUpdateWorker check path should call yaml_data_check_update");
    QVERIFY2(workerSource.contains(QStringLiteral("classic::update::yaml_data_apply_update(")),
             "YamlUpdateWorker apply path should call yaml_data_apply_update");
    QVERIFY2(workerSource.contains(QStringLiteral("classic::update::yaml_data_rollback_update(")),
             "YamlUpdateWorker rollback path should call yaml_data_rollback_update");
    QVERIFY2(!containsNativeYamlRecipeDuplication(workerSource),
             "YamlUpdateWorker must not duplicate YAML Data channel constants or schema entries");
}

QTEST_MAIN(YamlUpdateWiringTests)
#include "test_yaml_update_wiring.moc"
