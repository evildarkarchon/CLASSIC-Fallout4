#include "app/settingsdialog.h"
#include "core/guiusersettings.h"

#include <QAbstractButton>
#include <QCheckBox>
#include <QComboBox>
#include <QFile>
#include <QLineEdit>
#include <QListWidget>
#include <QMessageBox>
#include <QPushButton>
#include <QSpinBox>
#include <QTemporaryDir>
#include <QTimer>
#include <QtTest>

namespace {

/// Writes one current-schema User Settings fixture into a temporary CLASSIC root.
void writeSettings(const QString& root, const QByteArray& content)
{
    QFile file(root + QStringLiteral("/CLASSIC Settings.yaml"));
    QVERIFY(file.open(QIODevice::WriteOnly | QIODevice::Truncate));
    QCOMPARE(file.write(content), content.size());
}

/// Returns a minimal current document containing every setting edited by the dialog.
QByteArray dialogSettings()
{
    return QByteArrayLiteral("schema_version: \"1.0\"\n"
                             "CLASSIC_Settings:\n"
                             "  Update Check: true\n"
                             "  Update Source: GitHub\n"
                             "  Managed Game: Fallout4\n"
                             "  Game Version: Original\n"
                             "  Game Folder Path: C:/Games/Fallout4\n"
                             "  Game EXE Path: C:/Games/Fallout4/Fallout4.exe\n"
                             "  Documents Folder Path: C:/Documents/Fallout4\n"
                             "  INI Folder Path: C:/Documents/Fallout4\n"
                             "  FCX Mode: false\n"
                             "  Simplify Logs: false\n"
                             "  Show FormID Values: false\n"
                             "  Move Unsolved Logs: true\n"
                             "  Unsolved Logs Destination: null\n"
                             "  Max Concurrent Scans: 2\n"
                             "  FormID Databases:\n"
                             "    Fallout4: []\n"
                             "  Future Setting: preserve\n"
                             "UI:\n"
                             "  preferences:\n"
                             "    auto_switch_after_scan: true\n");
}

/// Closes the next modal message box and records its user-facing content.
void closeNextMessageBox(QString* title = nullptr, QString* text = nullptr)
{
    QTimer::singleShot(0, [title, text]() {
        for (QWidget* widget : QApplication::topLevelWidgets()) {
            auto* box = qobject_cast<QMessageBox*>(widget);
            if (!box) {
                continue;
            }
            if (title) {
                *title = box->windowTitle();
            }
            if (text) {
                *text = box->text();
            }
            box->accept();
            return;
        }
    });
}

/// Accepts the next modal confirmation with its explicit Yes result.
void acceptNextQuestion()
{
    QTimer::singleShot(0, []() {
        for (QWidget* widget : QApplication::topLevelWidgets()) {
            if (auto* box = qobject_cast<QMessageBox*>(widget)) {
                if (auto* yes = box->button(QMessageBox::Yes)) {
                    QTest::mouseClick(yes, Qt::LeftButton);
                }
                return;
            }
        }
    });
}

/// Finds a dialog button by its stable user-facing action label.
QPushButton* findButton(SettingsDialog& dialog, const QString& text)
{
    const auto buttons = dialog.findChildren<QPushButton*>();
    for (auto* button : buttons) {
        if (button->text() == text) {
            return button;
        }
    }
    return nullptr;
}

/// Settings dialog whose FormID picker returns deterministic files for behavior tests.
class TestableSettingsDialog final : public SettingsDialog {
public:
    explicit TestableSettingsDialog(const QString& dataDir)
        : SettingsDialog(dataDir, nullptr)
    {
    }

    QStringList selectedDatabases;

protected:
    /// Returns the test-authored multi-selection without opening a platform dialog.
    QStringList selectFormIdDatabaseFiles() override { return selectedDatabases; }
};

} // namespace

class SettingsDialogBehaviorTests : public QObject {
    Q_OBJECT

private slots:
    void cancel_discards_widget_changes_without_writing();
    void ok_commits_visible_settings_through_the_typed_update();
    /// Verifies that explicit first-run save bootstraps settings and derives the VR executable.
    void ok_bootstraps_missing_settings_with_the_selected_vr_executable();
    void validation_failure_keeps_the_original_document();
    void concurrent_change_surfaces_conflict_and_preserves_newer_values();
    void formid_add_button_accepts_multiple_files_and_deduplicates_paths();
    void reset_uses_rust_owned_defaults_and_clears_dependent_executable();
    /// Verifies that rollback invalidates the reviewed update decision and disables Apply.
    void rollback_requires_a_fresh_update_check_before_apply();
};

void SettingsDialogBehaviorTests::cancel_discards_widget_changes_without_writing()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    writeSettings(root.path(), dialogSettings());
    SettingsDialog dialog(root.path(), nullptr);
    auto* fcx = dialog.findChild<QCheckBox*>(QStringLiteral("settings.fcxMode"));
    auto* cancel = dialog.findChild<QPushButton*>(QStringLiteral("settings.cancelButton"));
    QVERIFY(fcx);
    QVERIFY(cancel);
    fcx->setChecked(true);

    QTest::mouseClick(cancel, Qt::LeftButton);

    QFile persisted(root.filePath(QStringLiteral("CLASSIC Settings.yaml")));
    QVERIFY(persisted.open(QIODevice::ReadOnly));
    QCOMPARE(persisted.readAll(), dialogSettings());
}

void SettingsDialogBehaviorTests::ok_commits_visible_settings_through_the_typed_update()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    writeSettings(root.path(), dialogSettings());
    SettingsDialog dialog(root.path(), nullptr);
    auto* version = dialog.findChild<QComboBox*>(QStringLiteral("settings.gameVersion"));
    auto* updateSource = dialog.findChild<QComboBox*>(QStringLiteral("settings.updateSource"));
    auto* updateCheck = dialog.findChild<QCheckBox*>(QStringLiteral("settings.updateCheck"));
    auto* fcx = dialog.findChild<QCheckBox*>(QStringLiteral("settings.fcxMode"));
    auto* simplify = dialog.findChild<QCheckBox*>(QStringLiteral("settings.simplifyLogs"));
    auto* showStatistics = dialog.findChild<QCheckBox*>(QStringLiteral("settings.showStatistics"));
    auto* formIdLookup = dialog.findChild<QCheckBox*>(QStringLiteral("settings.formIdValueLookup"));
    auto* moveUnsolved = dialog.findChild<QCheckBox*>(QStringLiteral("settings.moveUnsolvedLogs"));
    auto* autoSwitch = dialog.findChild<QCheckBox*>(QStringLiteral("settings.autoSwitchAfterScan"));
    auto* destination = dialog.findChild<QLineEdit*>(QStringLiteral("settings.unsolvedLogsDestination"));
    auto* gameRoot = dialog.findChild<QLineEdit*>(QStringLiteral("settings.gameRoot"));
    auto* documentsRoot = dialog.findChild<QLineEdit*>(QStringLiteral("settings.documentsRoot"));
    auto* databases = dialog.findChild<QListWidget*>(QStringLiteral("settings.formIdDatabases"));
    auto* concurrency = dialog.findChild<QSpinBox*>(QStringLiteral("settings.maxConcurrentScans"));
    auto* ok = dialog.findChild<QPushButton*>(QStringLiteral("settings.okButton"));
    QVERIFY(version);
    QVERIFY(updateSource);
    QVERIFY(updateCheck);
    QVERIFY(fcx);
    QVERIFY(simplify);
    QVERIFY(showStatistics);
    QVERIFY(formIdLookup);
    QVERIFY(moveUnsolved);
    QVERIFY(autoSwitch);
    QVERIFY(destination);
    QVERIFY(gameRoot);
    QVERIFY(documentsRoot);
    QVERIFY(databases);
    QVERIFY(concurrency);
    QVERIFY(ok);
    version->setCurrentText(QStringLiteral("NextGen"));
    updateSource->setCurrentText(QStringLiteral("Both"));
    updateCheck->setChecked(false);
    fcx->setChecked(true);
    simplify->setChecked(true);
    showStatistics->setChecked(true);
    formIdLookup->setChecked(true);
    moveUnsolved->setChecked(false);
    autoSwitch->setChecked(false);
    destination->setText(QStringLiteral("E:/Unsolved"));
    gameRoot->setText(QStringLiteral("E:/Games/Fallout4"));
    documentsRoot->setText(QStringLiteral("E:/Documents/Fallout4"));
    databases->addItem(QStringLiteral("E:/Databases/community.db"));
    concurrency->setValue(8);

    QTest::mouseClick(ok, Qt::LeftButton);

    QCOMPARE(dialog.result(), static_cast<int>(QDialog::Accepted));
    const auto reopened = classic::gui::GuiUserSettings::open(root.path());
    QVERIFY(!reopened.update.updateCheck);
    QCOMPARE(reopened.update.updateSource, QStringLiteral("Both"));
    QVERIFY(!reopened.frontend.autoSwitchAfterScan);
    QCOMPARE(reopened.scan.gameVersion, QStringLiteral("NextGen"));
    QVERIFY(reopened.scan.fcxMode);
    QVERIFY(reopened.scan.simplifyLogs);
    QVERIFY(reopened.scan.showStatistics);
    QVERIFY(reopened.scan.formIdValueLookup);
    QVERIFY(!reopened.scan.moveUnsolvedLogs);
    QCOMPARE(reopened.scan.unsolvedLogsDestination.value(), QStringLiteral("E:/Unsolved"));
    QCOMPARE(reopened.scan.maxConcurrentScans, 8);
    QCOMPARE(reopened.gameSetup.gameRoot.value(), QStringLiteral("E:/Games/Fallout4"));
    QCOMPARE(reopened.gameSetup.documentsRoot.value(), QStringLiteral("E:/Documents/Fallout4"));
    QCOMPARE(reopened.gameSetup.gameExecutable.value(), QStringLiteral("E:/Games/Fallout4/Fallout4.exe"));
    QCOMPARE(reopened.scan.formIdDatabases.value(QStringLiteral("Fallout4")),
             QStringList({QStringLiteral("E:/Databases/community.db")}));
    QFile persisted(root.filePath(QStringLiteral("CLASSIC Settings.yaml")));
    QVERIFY(persisted.open(QIODevice::ReadOnly));
    QVERIFY(persisted.readAll().contains("Future Setting: preserve"));
}

void SettingsDialogBehaviorTests::ok_bootstraps_missing_settings_with_the_selected_vr_executable()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    SettingsDialog dialog(root.path(), nullptr);
    auto* version = dialog.findChild<QComboBox*>(QStringLiteral("settings.gameVersion"));
    auto* gameRoot = dialog.findChild<QLineEdit*>(QStringLiteral("settings.gameRoot"));
    auto* documentsRoot = dialog.findChild<QLineEdit*>(QStringLiteral("settings.documentsRoot"));
    auto* ok = dialog.findChild<QPushButton*>(QStringLiteral("settings.okButton"));
    QVERIFY(version);
    QVERIFY(gameRoot);
    QVERIFY(documentsRoot);
    QVERIFY(ok);
    version->setCurrentText(QStringLiteral("VR"));
    gameRoot->setText(QStringLiteral("E:/Games/Fallout4VR"));
    documentsRoot->setText(QStringLiteral("E:/Documents/Fallout4VR"));

    QTest::mouseClick(ok, Qt::LeftButton);

    QCOMPARE(dialog.result(), static_cast<int>(QDialog::Accepted));
    const auto reopened = classic::gui::GuiUserSettings::open(root.path());
    QCOMPARE(reopened.revision.startsWith(QStringLiteral("sha256:")), true);
    QCOMPARE(reopened.scan.gameVersion, QStringLiteral("VR"));
    QCOMPARE(reopened.gameSetup.gameExecutable.value(), QStringLiteral("E:/Games/Fallout4VR/Fallout4VR.exe"));
}

void SettingsDialogBehaviorTests::validation_failure_keeps_the_original_document()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    writeSettings(root.path(), dialogSettings());
    SettingsDialog dialog(root.path(), nullptr);
    auto* destination = dialog.findChild<QLineEdit*>(QStringLiteral("settings.unsolvedLogsDestination"));
    auto* updateCheck = dialog.findChild<QCheckBox*>(QStringLiteral("settings.updateCheck"));
    auto* ok = dialog.findChild<QPushButton*>(QStringLiteral("settings.okButton"));
    QVERIFY(destination);
    QVERIFY(updateCheck);
    QVERIFY(ok);
    destination->setText(QStringLiteral("relative/path"));
    updateCheck->setChecked(false);
    closeNextMessageBox();

    QTest::mouseClick(ok, Qt::LeftButton);

    QVERIFY(dialog.result() != static_cast<int>(QDialog::Accepted));
    QFile persisted(root.filePath(QStringLiteral("CLASSIC Settings.yaml")));
    QVERIFY(persisted.open(QIODevice::ReadOnly));
    QCOMPARE(persisted.readAll(), dialogSettings());
}

void SettingsDialogBehaviorTests::concurrent_change_surfaces_conflict_and_preserves_newer_values()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    writeSettings(root.path(), dialogSettings());
    SettingsDialog dialog(root.path(), nullptr);
    const auto opened = classic::gui::GuiUserSettings::open(root.path());
    classic::gui::GuiUserSettingsChanges external;
    external.maxConcurrentScans = 4;
    QCOMPARE(classic::gui::GuiUserSettings::commit(root.path(), opened.revision, external).status,
             QStringLiteral("committed"));
    auto* concurrency = dialog.findChild<QSpinBox*>(QStringLiteral("settings.maxConcurrentScans"));
    auto* ok = dialog.findChild<QPushButton*>(QStringLiteral("settings.okButton"));
    QVERIFY(concurrency);
    QVERIFY(ok);
    concurrency->setValue(12);
    QString title;
    QString message;
    closeNextMessageBox(&title, &message);

    QTest::mouseClick(ok, Qt::LeftButton);

    QCOMPARE(title, QStringLiteral("User Settings Changed"));
    QVERIFY(message.contains(QStringLiteral("Reload Settings and try again")));
    QCOMPARE(classic::gui::GuiUserSettings::open(root.path()).scan.maxConcurrentScans, 4);
}

void SettingsDialogBehaviorTests::formid_add_button_accepts_multiple_files_and_deduplicates_paths()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    writeSettings(root.path(), dialogSettings());
    TestableSettingsDialog dialog(root.path());
    dialog.selectedDatabases = {QStringLiteral("E:/Databases/one.db"), QStringLiteral("E:/Databases/./one.db"),
                                QStringLiteral("E:/Databases/two.sqlite")};
    auto* add = dialog.findChild<QPushButton*>(QStringLiteral("settings.addFormIdDatabases"));
    auto* databases = dialog.findChild<QListWidget*>(QStringLiteral("settings.formIdDatabases"));
    QVERIFY(add);
    QVERIFY(databases);

    QTest::mouseClick(add, Qt::LeftButton);
    QTest::mouseClick(add, Qt::LeftButton);

    QCOMPARE(databases->count(), 2);
    QCOMPARE(databases->item(0)->text(), QStringLiteral("E:/Databases/one.db"));
    QCOMPARE(databases->item(1)->text(), QStringLiteral("E:/Databases/two.sqlite"));
}

void SettingsDialogBehaviorTests::reset_uses_rust_owned_defaults_and_clears_dependent_executable()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    writeSettings(root.path(), dialogSettings());
    SettingsDialog dialog(root.path(), nullptr);
    auto* reset = dialog.findChild<QPushButton*>(QStringLiteral("settings.resetButton"));
    auto* ok = dialog.findChild<QPushButton*>(QStringLiteral("settings.okButton"));
    auto* moveUnsolved = dialog.findChild<QCheckBox*>(QStringLiteral("settings.moveUnsolvedLogs"));
    QVERIFY(reset);
    QVERIFY(ok);
    QVERIFY(moveUnsolved);
    acceptNextQuestion();

    QTest::mouseClick(reset, Qt::LeftButton);
    QVERIFY(moveUnsolved->isChecked());
    auto* gameRoot = dialog.findChild<QLineEdit*>(QStringLiteral("settings.gameRoot"));
    QVERIFY(gameRoot);
    QVERIFY(gameRoot->text().isEmpty());
    QTest::mouseClick(ok, Qt::LeftButton);

    const auto defaults = classic::gui::GuiUserSettings::publishedDefaults();
    const auto reopened = classic::gui::GuiUserSettings::open(root.path());
    QCOMPARE(reopened.update.updateCheck, defaults.update.updateCheck);
    QCOMPARE(reopened.update.updateSource, defaults.update.updateSource);
    QCOMPARE(reopened.frontend.autoSwitchAfterScan, defaults.frontend.autoSwitchAfterScan);
    QCOMPARE(reopened.scan.gameVersion, defaults.scan.gameVersion);
    QCOMPARE(reopened.scan.fcxMode, defaults.scan.fcxMode);
    QCOMPARE(reopened.scan.simplifyLogs, defaults.scan.simplifyLogs);
    QCOMPARE(reopened.scan.showStatistics, defaults.scan.showStatistics);
    QCOMPARE(reopened.scan.formIdValueLookup, defaults.scan.formIdValueLookup);
    QCOMPARE(reopened.scan.moveUnsolvedLogs, defaults.scan.moveUnsolvedLogs);
    QCOMPARE(reopened.scan.unsolvedLogsDestination, defaults.scan.unsolvedLogsDestination);
    QCOMPARE(reopened.scan.maxConcurrentScans, defaults.scan.maxConcurrentScans);
    QVERIFY(reopened.scan.formIdDatabases.value(reopened.gameSetup.managedGame).isEmpty());
    QCOMPARE(reopened.gameSetup.gameRoot, defaults.gameSetup.gameRoot);
    QCOMPARE(reopened.gameSetup.gameExecutable, defaults.gameSetup.gameExecutable);
    QCOMPARE(reopened.gameSetup.documentsRoot, defaults.gameSetup.documentsRoot);
}

void SettingsDialogBehaviorTests::rollback_requires_a_fresh_update_check_before_apply()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    writeSettings(root.path(), dialogSettings());
    SettingsDialog dialog(root.path(), nullptr);
    auto* apply = findButton(dialog, QStringLiteral("Apply Data Updates"));
    QVERIFY(apply);

    YamlCheckResult check;
    check.status = QStringLiteral("updateAvailable");
    check.releaseTag = QStringLiteral("yaml-data-v2");
    check.compatibleFileNames = {QStringLiteral("CLASSIC Fallout4.yaml")};
    check.compatibleFileSha256 = {QString(64, QLatin1Char('a'))};
    QVERIFY(QMetaObject::invokeMethod(&dialog, "onYamlCheckFinished", Qt::DirectConnection,
                                      Q_ARG(YamlCheckResult, check)));
    QVERIFY(apply->isEnabled());

    YamlRollbackResult rollback;
    rollback.rolledBack = check.compatibleFileNames;
    QVERIFY(QMetaObject::invokeMethod(&dialog, "onYamlRollbackFinished", Qt::DirectConnection,
                                      Q_ARG(YamlRollbackResult, rollback)));

    QVERIFY(!apply->isEnabled());
}

QTEST_MAIN(SettingsDialogBehaviorTests)
#include "test_settingsdialog_behavior.moc"
