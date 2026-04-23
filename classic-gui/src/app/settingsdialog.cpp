#include "settingsdialog.h"

#include <QApplication>
#include <QCloseEvent>
#include <QDir>
#include <QFile>
#include <QFileDialog>
#include <QFileInfo>
#include <QFormLayout>
#include <QGroupBox>
#include <QHBoxLayout>
#include <QMessageBox>
#include <QMetaType>
#include <QStringList>
#include <QThread>
#include <QVBoxLayout>

#include <cstdint>
#include <string>

#include "core/rust_qt_bridge.h"
#include "core/signalhub.h"
#include "widgets/toggleswitch.h"
#include "workers/yamlupdateworker.h"

#include "classic_cxx_bridge/registry.h"
#include "classic_cxx_bridge/settings.h"
#include "classic_cxx_bridge/update.h"
#include "rust/cxx.h"

// ── Construction ───────────────────────────────────────────────────

SettingsDialog::SettingsDialog(const QString& dataDir, SignalHub* signalHub, QWidget* parent)
    : QDialog(parent)
    , m_dataDir(dataDir)
    , m_signalHub(signalHub)
{
    // Register the YAML update result structs with Qt's meta system so
    // queued signals across the worker thread can marshal them. Safe to
    // call repeatedly — Qt deduplicates internally.
    qRegisterMetaType<YamlCheckResult>("YamlCheckResult");
    qRegisterMetaType<YamlApplyResult>("YamlApplyResult");
    qRegisterMetaType<YamlRollbackResult>("YamlRollbackResult");

    setWindowTitle(QStringLiteral("Settings"));
    setModal(true);
    setupUi();
    loadSettings();
}

SettingsDialog::~SettingsDialog()
{
    // Tear down the worker thread cleanly. `QThread::quit` returns as
    // soon as the current slot finishes, so in-flight check/apply work
    // runs to completion on this thread instead of being interrupted.
    // `wait` blocks briefly on the UI thread during dialog close; the
    // alternative (interrupting a network call mid-flight) is worse.
    if (m_yamlUpdateThread) {
        m_yamlUpdateThread->quit();
        m_yamlUpdateThread->wait();
    }
}

void SettingsDialog::closeEvent(QCloseEvent* event)
{
    if (!canCloseDialog()) {
        event->ignore();
        return;
    }

    QDialog::closeEvent(event);
}

void SettingsDialog::reject()
{
    if (!canCloseDialog()) {
        return;
    }

    QDialog::reject();
}

bool SettingsDialog::canCloseDialog()
{
    if (!m_yamlUpdateBusy) {
        return true;
    }

    QMessageBox::information(
        this, QStringLiteral("Data Update In Progress"),
        QStringLiteral("Please wait for the current data update operation to finish before closing Settings."));
    return false;
}

// ── UI Setup ───────────────────────────────────────────────────────

void SettingsDialog::setupUi()
{
    setMinimumSize(500, 450);

    auto* mainLayout = new QVBoxLayout(this);
    mainLayout->setContentsMargins(16, 16, 16, 16);
    mainLayout->setSpacing(12);

    // Tab widget
    auto* tabs = new QTabWidget();
    setupGeneralTab(tabs);
    setupScanningTab(tabs);
    setupPathsTab(tabs);
    setupUpdatesTab(tabs);
    mainLayout->addWidget(tabs);

    // Button row: [Reset to Defaults] [stretch] [Cancel] [OK]
    {
        auto* btnRow = new QHBoxLayout();

        auto* btnReset = new QPushButton(QStringLiteral("Reset to Defaults"));
        connect(btnReset, &QPushButton::clicked, this, &SettingsDialog::resetToDefaults);
        btnRow->addWidget(btnReset);

        btnRow->addStretch();

        auto* btnCancel = new QPushButton(QStringLiteral("Cancel"));
        connect(btnCancel, &QPushButton::clicked, this, &QDialog::reject);
        btnRow->addWidget(btnCancel);

        auto* btnOk = new QPushButton(QStringLiteral("OK"));
        btnOk->setDefault(true);
        connect(btnOk, &QPushButton::clicked, this, [this]() {
            saveSettings();
            accept();
        });
        btnRow->addWidget(btnOk);

        mainLayout->addLayout(btnRow);
    }
}

void SettingsDialog::setupGeneralTab(QTabWidget* tabs)
{
    auto* tab = new QWidget();
    auto* layout = new QFormLayout(tab);
    layout->setContentsMargins(16, 16, 16, 16);
    layout->setSpacing(8);

    m_comboGameVersion = new QComboBox();
    m_comboGameVersion->addItems({QStringLiteral("Auto"), QStringLiteral("Original"), QStringLiteral("NextGen"),
                                  QStringLiteral("AnniversaryEdition"), QStringLiteral("VR")});
    layout->addRow(QStringLiteral("Game Version:"), m_comboGameVersion);

    // Keep startup update behavior in General so it's easy to find.
    m_chkUpdateCheck = new ToggleSwitch(QStringLiteral("Check for Updates on Startup"));
    layout->addRow(m_chkUpdateCheck);

    tabs->addTab(tab, QStringLiteral("General"));
}

void SettingsDialog::setupScanningTab(QTabWidget* tabs)
{
    auto* tab = new QWidget();
    auto* layout = new QVBoxLayout(tab);
    layout->setContentsMargins(16, 16, 16, 16);
    layout->setSpacing(8);

    m_chkFcxMode = new ToggleSwitch(QStringLiteral("FCX Mode"));
    m_chkSimplifyLogs = new ToggleSwitch(QStringLiteral("Simplify Logs"));
    m_chkShowFormIdValues = new ToggleSwitch(QStringLiteral("Show FormID Values"));
    m_chkMoveUnsolvedLogs = new ToggleSwitch(QStringLiteral("Move Unsolved Logs"));
    m_chkAutoSwitchAfterScan = new ToggleSwitch(QStringLiteral("Auto Switch to Results After Scan"));

    layout->addWidget(m_chkFcxMode);
    layout->addWidget(m_chkSimplifyLogs);
    layout->addWidget(m_chkShowFormIdValues);
    layout->addWidget(m_chkMoveUnsolvedLogs);
    layout->addWidget(m_chkAutoSwitchAfterScan);

    // Max Concurrent Scans
    {
        auto* row = new QHBoxLayout();
        auto* label = new QLabel(QStringLiteral("Max Concurrent Scans (0 = auto):"));
        m_spinMaxConcurrentScans = new QSpinBox();
        m_spinMaxConcurrentScans->setRange(0, 32);
        m_spinMaxConcurrentScans->setValue(0);
        m_spinMaxConcurrentScans->setButtonSymbols(QAbstractSpinBox::UpDownArrows);
        row->addWidget(label);
        row->addWidget(m_spinMaxConcurrentScans);
        row->addStretch();
        layout->addLayout(row);
    }

    layout->addStretch();
    tabs->addTab(tab, QStringLiteral("Scanning"));
}

void SettingsDialog::setupPathsTab(QTabWidget* tabs)
{
    auto* tab = new QWidget();
    auto* layout = new QVBoxLayout(tab);
    layout->setContentsMargins(16, 16, 16, 16);
    layout->setSpacing(8);

    // Game Folder section
    {
        auto* group = new QGroupBox(QStringLiteral("Game Folder"));
        auto* groupLayout = new QHBoxLayout(group);

        m_editGameFolder = new QLineEdit();
        m_editGameFolder->setPlaceholderText(QStringLiteral("Path to game installation folder..."));
        groupLayout->addWidget(m_editGameFolder);

        auto* btnBrowse = new QPushButton(QStringLiteral("Browse"));
        btnBrowse->setFixedWidth(80);
        connect(btnBrowse, &QPushButton::clicked, this, &SettingsDialog::onBrowseGameFolder);
        groupLayout->addWidget(btnBrowse);

        auto* btnReset = new QPushButton(QStringLiteral("Reset"));
        btnReset->setFixedWidth(60);
        connect(btnReset, &QPushButton::clicked, this, &SettingsDialog::onResetGameFolder);
        groupLayout->addWidget(btnReset);

        layout->addWidget(group);
    }

    // INI Folder section
    {
        auto* group = new QGroupBox(QStringLiteral("INI Folder"));
        auto* groupLayout = new QHBoxLayout(group);

        m_editIniFolder = new QLineEdit();
        m_editIniFolder->setPlaceholderText(QStringLiteral("Leave empty for auto-detect..."));
        groupLayout->addWidget(m_editIniFolder);

        auto* btnBrowse = new QPushButton(QStringLiteral("Browse"));
        btnBrowse->setFixedWidth(80);
        connect(btnBrowse, &QPushButton::clicked, this, &SettingsDialog::onBrowseIniFolder);
        groupLayout->addWidget(btnBrowse);

        auto* btnReset = new QPushButton(QStringLiteral("Reset"));
        btnReset->setFixedWidth(60);
        connect(btnReset, &QPushButton::clicked, this, &SettingsDialog::onResetIniFolder);
        groupLayout->addWidget(btnReset);

        layout->addWidget(group);
    }

    // FormID Databases section
    {
        auto* group = new QGroupBox(QStringLiteral("Additional FormID Databases"));
        auto* groupLayout = new QVBoxLayout(group);

        auto* helpLabel = new QLabel(QStringLiteral("The built-in database is always included.\n"
                                                    "Add extra databases here if needed."));
        helpLabel->setWordWrap(true);
        groupLayout->addWidget(helpLabel);

        m_listFormIdDbs = new QListWidget();
        groupLayout->addWidget(m_listFormIdDbs);

        auto* btnRow = new QHBoxLayout();
        auto* btnAdd = new QPushButton(QStringLiteral("Add..."));
        connect(btnAdd, &QPushButton::clicked, this, &SettingsDialog::onAddFormIdDb);
        btnRow->addWidget(btnAdd);

        auto* btnRemove = new QPushButton(QStringLiteral("Remove"));
        connect(btnRemove, &QPushButton::clicked, this, &SettingsDialog::onRemoveFormIdDb);
        btnRow->addWidget(btnRemove);

        btnRow->addStretch();
        groupLayout->addLayout(btnRow);

        layout->addWidget(group);
    }

    tabs->addTab(tab, QStringLiteral("Paths"));
}

void SettingsDialog::setupUpdatesTab(QTabWidget* tabs)
{
    auto* tab = new QWidget();
    auto* layout = new QVBoxLayout(tab);
    layout->setContentsMargins(16, 16, 16, 16);
    layout->setSpacing(8);

    auto* startupHint = new QLabel(QStringLiteral("Startup update checks are configured in the General tab."));
    startupHint->setWordWrap(true);
    layout->addWidget(startupHint);

    // Binary release updates (existing flow)
    {
        auto* group = new QGroupBox(QStringLiteral("Application Updates"));
        auto* groupLayout = new QVBoxLayout(group);

        auto* row = new QHBoxLayout();
        m_btnCheckNow = new QPushButton(QStringLiteral("Check for Updates Now"));
        connect(m_btnCheckNow, &QPushButton::clicked, this, &SettingsDialog::onCheckForUpdates);
        row->addWidget(m_btnCheckNow);
        row->addStretch();
        groupLayout->addLayout(row);

        m_lblUpdateStatus = new QLabel();
        m_lblUpdateStatus->setWordWrap(true);
        groupLayout->addWidget(m_lblUpdateStatus);

        layout->addWidget(group);
    }

    // YAML data updates (yaml-update-delivery Section 12)
    //
    // The three bridge entry points (`yaml_check_update`, `yaml_apply_update`,
    // `yaml_rollback_update`) are called synchronously here — matching the
    // existing binary-update flow above — because each call uses `block_on`
    // on the shared Tokio runtime inside the bridge and returns within a few
    // hundred milliseconds. This dialog is modal; briefly blocking the UI
    // thread is acceptable here.
    {
        auto* group = new QGroupBox(QStringLiteral("Data File Updates"));
        auto* groupLayout = new QVBoxLayout(group);

        auto* helpLabel = new QLabel(
            QStringLiteral("CLASSIC's crash-signature and mod-conflict data evolves faster than the binary. "
                           "Check for and apply data updates here, or roll back the last applied update."));
        helpLabel->setWordWrap(true);
        groupLayout->addWidget(helpLabel);

        auto* btnRow = new QHBoxLayout();
        m_btnCheckYamlUpdates = new QPushButton(QStringLiteral("Check for Data Updates"));
        connect(m_btnCheckYamlUpdates, &QPushButton::clicked, this, &SettingsDialog::onCheckForYamlUpdates);
        btnRow->addWidget(m_btnCheckYamlUpdates);

        m_btnApplyYamlUpdates = new QPushButton(QStringLiteral("Apply Data Updates"));
        m_btnApplyYamlUpdates->setEnabled(false); // Enabled only after a successful check reveals updates.
        connect(m_btnApplyYamlUpdates, &QPushButton::clicked, this, &SettingsDialog::onApplyYamlUpdates);
        btnRow->addWidget(m_btnApplyYamlUpdates);

        m_btnRollbackYamlUpdates = new QPushButton(QStringLiteral("Rollback Data Update"));
        // The bridge returns a graceful "rolled_back=false, empty error" outcome
        // when no `.prev` exists, so we keep the button enabled and surface
        // "No previous version to roll back to" in the status label.
        connect(m_btnRollbackYamlUpdates, &QPushButton::clicked, this, &SettingsDialog::onRollbackYamlUpdate);
        btnRow->addWidget(m_btnRollbackYamlUpdates);

        btnRow->addStretch();
        groupLayout->addLayout(btnRow);

        m_lblYamlUpdateStatus = new QLabel();
        m_lblYamlUpdateStatus->setWordWrap(true);
        groupLayout->addWidget(m_lblYamlUpdateStatus);

        layout->addWidget(group);
    }

    layout->addStretch();
    tabs->addTab(tab, QStringLiteral("Updates"));
}

// ── Settings persistence ───────────────────────────────────────────

void SettingsDialog::loadSettings()
{
    if (m_dataDir.isEmpty())
        return;

    QString settingsPath = m_dataDir + QStringLiteral("/CLASSIC Settings.yaml");
    try {
        auto ops = classic::settings::yaml_ops_new();
        classic::settings::yaml_ops_load_file(*ops, std::string(settingsPath.toUtf8().constData()));

        // General - Game Version
        auto gameVersion = classic::settings::yaml_ops_get_string(*ops, "CLASSIC_Settings.Game Version", "auto");
        QString gv = classic::toQString(gameVersion);
        if (gv == QStringLiteral("Original"))
            m_comboGameVersion->setCurrentIndex(1);
        else if (gv == QStringLiteral("NextGen"))
            m_comboGameVersion->setCurrentIndex(2);
        else if (gv == QStringLiteral("AnniversaryEdition") || gv == QStringLiteral("AE"))
            m_comboGameVersion->setCurrentIndex(3);
        else if (gv == QStringLiteral("VR"))
            m_comboGameVersion->setCurrentIndex(4);
        else
            m_comboGameVersion->setCurrentIndex(0); // Auto

        // Scanning booleans
        auto getBool = [&](const char* key) -> bool {
            auto val = classic::settings::yaml_ops_get_setting_value(*ops, key);
            return val.value_type == "bool" && val.value == "true";
        };

        m_chkFcxMode->setChecked(getBool("CLASSIC_Settings.FCX Mode"));
        m_chkSimplifyLogs->setChecked(getBool("CLASSIC_Settings.Simplify Logs"));
        m_chkShowFormIdValues->setChecked(getBool("CLASSIC_Settings.Show FormID Values"));
        m_chkMoveUnsolvedLogs->setChecked(getBool("CLASSIC_Settings.Move Unsolved Logs"));
        m_chkAutoSwitchAfterScan->setChecked(getBool("CLASSIC_Settings.Auto Switch After Scan"));

        // Max Concurrent Scans
        auto maxScans = classic::settings::yaml_ops_get_setting_value(*ops, "CLASSIC_Settings.Max Concurrent Scans");
        if (maxScans.value_type == "integer") {
            bool ok = false;
            int val = QString::fromStdString(std::string(maxScans.value)).toInt(&ok);
            if (ok)
                m_spinMaxConcurrentScans->setValue(val);
        }

        // Paths - Game Folder + INI Folder
        auto gameFolder = classic::settings::yaml_ops_get_string(*ops, "CLASSIC_Settings.Game Folder Path", "");
        if (!gameFolder.empty() && m_editGameFolder) {
            m_editGameFolder->setText(classic::toQString(gameFolder));
        }

        auto iniFolder = classic::settings::yaml_ops_get_string(*ops, "CLASSIC_Settings.INI Folder Path", "");
        if (!iniFolder.empty()) {
            m_editIniFolder->setText(classic::toQString(iniFolder));
        }

        // FormID Databases (game-specific key)
        auto game = classic::registry::registry_get_game();
        std::string dbKey = "CLASSIC_Settings.FormID Databases." + std::string(game);
        auto dbs = classic::settings::yaml_ops_get_vec(*ops, dbKey);
        m_listFormIdDbs->clear();
        for (const auto& db : dbs) {
            m_listFormIdDbs->addItem(classic::toQString(db));
        }

        // Updates
        m_chkUpdateCheck->setChecked(getBool("CLASSIC_Settings.Update Check"));

    } catch (const std::exception& e) {
        // Settings load failure is not fatal -- widgets keep defaults
        (void)e;
    } catch (...) {
        // Silently use defaults
    }
}

void SettingsDialog::saveSettings()
{
    if (m_dataDir.isEmpty())
        return;

    QString settingsPath = m_dataDir + QStringLiteral("/CLASSIC Settings.yaml");
    try {
        auto ops = classic::settings::yaml_ops_new();
        classic::settings::yaml_ops_load_file(*ops, std::string(settingsPath.toUtf8().constData()));

        // General - Game Version
        static const char* gameVersionStrings[] = {"auto", "Original", "NextGen", "AnniversaryEdition", "VR"};
        int idx = m_comboGameVersion->currentIndex();
        if (idx >= 0 && idx <= 4) {
            classic::settings::yaml_ops_set_string_setting(*ops, "CLASSIC_Settings.Game Version",
                                                           gameVersionStrings[idx]);
        }

        // Scanning booleans
        classic::settings::yaml_ops_set_bool_setting(*ops, "CLASSIC_Settings.FCX Mode", m_chkFcxMode->isChecked());
        classic::settings::yaml_ops_set_bool_setting(*ops, "CLASSIC_Settings.Simplify Logs",
                                                     m_chkSimplifyLogs->isChecked());
        classic::settings::yaml_ops_set_bool_setting(*ops, "CLASSIC_Settings.Show FormID Values",
                                                     m_chkShowFormIdValues->isChecked());
        classic::settings::yaml_ops_set_bool_setting(*ops, "CLASSIC_Settings.Move Unsolved Logs",
                                                     m_chkMoveUnsolvedLogs->isChecked());
        classic::settings::yaml_ops_set_bool_setting(*ops, "CLASSIC_Settings.Auto Switch After Scan",
                                                     m_chkAutoSwitchAfterScan->isChecked());

        // Max Concurrent Scans
        classic::settings::yaml_ops_set_integer_setting(*ops, "CLASSIC_Settings.Max Concurrent Scans",
                                                        static_cast<int64_t>(m_spinMaxConcurrentScans->value()));

        // Paths - Game Folder + INI Folder
        auto gameText = m_editGameFolder ? QDir::cleanPath(m_editGameFolder->text().trimmed()) : QString();
        classic::settings::yaml_ops_set_string_setting(*ops, "CLASSIC_Settings.Game Folder Path",
                                                       std::string(gameText.toUtf8().constData()));

        auto gameExePath = classic::settings::yaml_ops_get_string(*ops, "CLASSIC_Settings.Game EXE Path", "");
        QString exePath = gameExePath.empty() ? QString() : QDir::cleanPath(classic::toQString(gameExePath).trimmed());

        bool shouldResetExePath = false;
        if (!gameText.isEmpty()) {
            if (exePath.isEmpty() || !QFile::exists(exePath)) {
                shouldResetExePath = true;
            } else {
                const QString exeParent = QDir::cleanPath(QFileInfo(exePath).absolutePath());
                if (exeParent.compare(gameText, Qt::CaseInsensitive) != 0) {
                    shouldResetExePath = true;
                }
            }
        }

        if (shouldResetExePath) {
            const QString defaultExe = QDir::cleanPath(gameText + QStringLiteral("/Fallout4.exe"));
            classic::settings::yaml_ops_set_string_setting(*ops, "CLASSIC_Settings.Game EXE Path",
                                                           std::string(defaultExe.toUtf8().constData()));
        }

        auto iniText = m_editIniFolder->text();
        classic::settings::yaml_ops_set_string_setting(*ops, "CLASSIC_Settings.INI Folder Path",
                                                       std::string(iniText.toUtf8().constData()));

        // FormID Databases (game-specific key)
        auto game = classic::registry::registry_get_game();
        std::string dbKey = "CLASSIC_Settings.FormID Databases." + std::string(game);
        rust::Vec<rust::String> dbVec;
        for (int i = 0; i < m_listFormIdDbs->count(); ++i) {
            auto text = m_listFormIdDbs->item(i)->text();
            dbVec.push_back(rust::String(std::string(text.toUtf8().constData())));
        }
        classic::settings::yaml_ops_set_vec_setting(*ops, dbKey, std::move(dbVec));

        // Updates
        classic::settings::yaml_ops_set_bool_setting(*ops, "CLASSIC_Settings.Update Check",
                                                     m_chkUpdateCheck->isChecked());

        // Save to disk
        classic::settings::yaml_ops_save_file(*ops, std::string(settingsPath.toUtf8().constData()));

    } catch (const std::exception& e) {
        QMessageBox::warning(this, QStringLiteral("Settings Error"),
                             QStringLiteral("Failed to save settings: ") + QString::fromUtf8(e.what()));
    } catch (...) {
        QMessageBox::warning(this, QStringLiteral("Settings Error"),
                             QStringLiteral("Failed to save settings: unknown error"));
    }
}

void SettingsDialog::resetToDefaults()
{
    auto result =
        QMessageBox::question(this, QStringLiteral("Reset to Defaults"),
                              QStringLiteral("Are you sure you want to reset all settings to their defaults?"),
                              QMessageBox::Yes | QMessageBox::No, QMessageBox::No);

    if (result != QMessageBox::Yes)
        return;

    // Reset widgets to default values (no YAML write until OK)
    m_comboGameVersion->setCurrentIndex(0); // Auto
    m_chkFcxMode->setChecked(false);
    m_chkSimplifyLogs->setChecked(false);
    m_chkShowFormIdValues->setChecked(false);
    m_chkMoveUnsolvedLogs->setChecked(false);
    m_chkAutoSwitchAfterScan->setChecked(true); // default is true
    m_spinMaxConcurrentScans->setValue(0);
    if (m_editGameFolder) {
        m_editGameFolder->clear();
    }
    m_editIniFolder->clear();
    m_listFormIdDbs->clear();
    m_chkUpdateCheck->setChecked(true); // default is true
    m_lblUpdateStatus->clear();
    m_btnApplyYamlUpdates->setEnabled(false);
    m_lblYamlUpdateStatus->clear();
    m_approvedReleaseTag.clear();
    m_approvedFileNames.clear();
    m_approvedFileSha256.clear();
}

// ── Slot implementations ───────────────────────────────────────────

void SettingsDialog::onBrowseGameFolder()
{
    const QString initial = m_editGameFolder ? m_editGameFolder->text() : QString();
    QString dir = QFileDialog::getExistingDirectory(this, QStringLiteral("Select Game Folder"), initial);
    if (!dir.isEmpty() && m_editGameFolder) {
        m_editGameFolder->setText(dir);
    }
}

void SettingsDialog::onResetGameFolder()
{
    if (m_editGameFolder) {
        m_editGameFolder->clear();
    }
}

void SettingsDialog::onBrowseIniFolder()
{
    QString dir = QFileDialog::getExistingDirectory(this, QStringLiteral("Select INI Folder"), m_editIniFolder->text());
    if (!dir.isEmpty()) {
        m_editIniFolder->setText(dir);
    }
}

void SettingsDialog::onResetIniFolder()
{
    m_editIniFolder->clear();
}

void SettingsDialog::onAddFormIdDb()
{
    QString file = QFileDialog::getOpenFileName(this, QStringLiteral("Select FormID Database"), QString(),
                                                QStringLiteral("Database Files (*.db *.sqlite);;All Files (*)"));
    if (!file.isEmpty()) {
        m_listFormIdDbs->addItem(file);
    }
}

void SettingsDialog::onRemoveFormIdDb()
{
    auto* item = m_listFormIdDbs->currentItem();
    if (item) {
        delete m_listFormIdDbs->takeItem(m_listFormIdDbs->row(item));
    }
}

void SettingsDialog::onCheckForUpdates()
{
    m_btnCheckNow->setEnabled(false);
    m_lblUpdateStatus->setText(QStringLiteral("Checking for updates..."));

    try {
        const QString currentVersion = QApplication::applicationVersion();
        auto status = classic::update::check_app_notification(
            rust::Str("evildarkarchon"),
            rust::Str("CLASSIC-Fallout4"),
            classic::toRustString(currentVersion));

        const std::string classification(status.classification);
        if (classification == "error") {
            const std::string errorMessage(status.error_message);
            m_lblUpdateStatus->setText(QStringLiteral("Error: ") +
                                       (errorMessage.empty() ? QStringLiteral("unknown error")
                                                             : QString::fromUtf8(errorMessage)));
        } else if (classification == "update_available") {
            const std::string title(status.display_title);
            QString text = QStringLiteral("Update available: v") + classic::toQString(status.latest_version);
            if (!title.empty()) {
                text += QStringLiteral(" — ") + QString::fromUtf8(title);
            }
            m_lblUpdateStatus->setText(text);
        } else if (classification == "deprecated_client") {
            m_lblUpdateStatus->setText(QStringLiteral("Deprecated build; upgrade to v") +
                                       classic::toQString(status.latest_version));
        } else if (classification == "unknown") {
            const std::string parseError(status.parse_error);
            m_lblUpdateStatus->setText(QStringLiteral("Update check inconclusive: ") +
                                       (parseError.empty() ? QStringLiteral("unknown reason")
                                                           : QString::fromUtf8(parseError)));
        } else {
            // "up_to_date" or any unexpected classification.
            m_lblUpdateStatus->setText(QStringLiteral("You are up to date."));
        }
    } catch (const std::exception& e) {
        m_lblUpdateStatus->setText(QStringLiteral("Update check failed: ") + QString::fromUtf8(e.what()));
    } catch (...) {
        m_lblUpdateStatus->setText(QStringLiteral("Update check failed: unknown error"));
    }

    m_btnCheckNow->setEnabled(true);
}

// ── YAML data update slots (yaml-update-delivery Section 12) ──────────
//
// Pages URL and tag prefix are the compile-time lookup coordinates from
// `yaml-update-delivery.md`; the repo owner matches the one already hard-coded
// in the Rust bridge `GithubClient::new("evildarkarchon", "CLASSIC-Fallout4")`.
// Kept as local constants instead of ad-hoc literals so the two slots below
// cannot drift from each other.

namespace {

constexpr const char* kYamlPagesUrl =
    "https://evildarkarchon.github.io/CLASSIC-Fallout4/yaml-data/manifest-latest.json";
constexpr const char* kYamlTagPrefix = "yaml-data-v";

// The two shippable files the client knows about today. The accepted ranges
// mirror `client_schemas::MAIN_YAML` and `client_schemas::GAME_FALLOUT4_YAML`
// on the Rust side (`SchemaCompat::new(2, 0)` for Main, `SchemaCompat::new(1, 0)`
// for Fallout4); the schema-version gate in tools/schema_version_gate.py keeps
// them in sync with the bundled YAML.
//
// We deliberately send `has_installed = false` for both entries: the Rust
// orchestrator (`check_yaml_update`) reads each file from the yaml-cache
// directory and fills in the installed schema_version itself, so a repeat
// Check after Apply converges to `UpToDate` instead of treating the just-
// installed bytes as "newer" again (which would rotate `.prev` to the
// already-current bytes and destroy rollback history).
rust::Vec<classic::update::YamlClientSchemaEntryDto> buildYamlSchemaEntries()
{
    rust::Vec<classic::update::YamlClientSchemaEntryDto> entries;

    classic::update::YamlClientSchemaEntryDto main{};
    main.name = "CLASSIC Main.yaml";
    main.accepted_major = 2u;
    main.accepted_minimum_minor = 0u;
    main.has_installed = false;
    entries.push_back(std::move(main));

    classic::update::YamlClientSchemaEntryDto fallout4{};
    fallout4.name = "CLASSIC Fallout4.yaml";
    fallout4.accepted_major = 1u;
    fallout4.accepted_minimum_minor = 0u;
    fallout4.has_installed = false;
    entries.push_back(std::move(fallout4));

    return entries;
}

// Tag discriminator constants — kept in lockstep with the `TAG_*` constants
// in `cpp-bindings/classic-cpp-bridge/src/update.rs`. If the bridge grows a
// new case, update this block and the test_yaml_update_wiring fixtures.
constexpr std::uint32_t kYamlTagDisabled = 0u;
constexpr std::uint32_t kYamlTagUpdateAvailable = 1u;
constexpr std::uint32_t kYamlTagUpToDate = 2u;
constexpr std::uint32_t kYamlTagUnknown = 3u;
constexpr std::uint32_t kYamlTagError = 4u;

} // namespace

void SettingsDialog::ensureYamlUpdateWorker()
{
    if (m_yamlUpdateWorker) {
        return;
    }

    m_yamlUpdateThread = new QThread(this);
    m_yamlUpdateWorker = new YamlUpdateWorker();
    m_yamlUpdateWorker->moveToThread(m_yamlUpdateThread);

    // Delete the worker object when the thread finishes (dialog close).
    // Parented to nullptr above so its lifetime is tied to the thread,
    // not to the QObject tree — otherwise we would race the parent
    // destructor with `moveToThread`.
    connect(m_yamlUpdateThread, &QThread::finished, m_yamlUpdateWorker,
            &QObject::deleteLater);

    // Queued connections (auto across threads) for the three result
    // signals. All UI mutations happen in the slots on the UI thread.
    connect(m_yamlUpdateWorker, &YamlUpdateWorker::checkFinished, this,
            &SettingsDialog::onYamlCheckFinished);
    connect(m_yamlUpdateWorker, &YamlUpdateWorker::applyFinished, this,
            &SettingsDialog::onYamlApplyFinished);
    connect(m_yamlUpdateWorker, &YamlUpdateWorker::rollbackFinished, this,
            &SettingsDialog::onYamlRollbackFinished);

    m_yamlUpdateThread->start();
}

void SettingsDialog::onCheckForYamlUpdates()
{
    ensureYamlUpdateWorker();
    m_yamlUpdateBusy = true;

    m_btnCheckYamlUpdates->setEnabled(false);
    m_btnApplyYamlUpdates->setEnabled(false);
    m_lblYamlUpdateStatus->setText(QStringLiteral("Checking for data updates..."));

    // Any non-UpdateAvailable branch clears the approved decision so a
    // stale Check -> change setting -> Apply sequence cannot install a
    // release the user never confirmed. Populated in the handler when
    // the result lands with status == "updateAvailable".
    m_approvedReleaseTag.clear();
    m_approvedFileNames.clear();
    m_approvedFileSha256.clear();

    const bool enabled = m_chkUpdateCheck && m_chkUpdateCheck->isChecked();

    // Fire-and-forget: the worker serializes the blocking bridge call on
    // its own thread. The UI stays responsive because control returns
    // here immediately. The result comes back via `checkFinished` ->
    // `onYamlCheckFinished` on the UI thread.
    QMetaObject::invokeMethod(m_yamlUpdateWorker, "doCheck", Qt::QueuedConnection,
                              Q_ARG(bool, enabled));
}

void SettingsDialog::onApplyYamlUpdates()
{
    // Refuse apply until a prior Check populated a reviewed decision.
    // This is the UI-layer counterpart to `DecisionStale` in the core —
    // we never want the user clicking Apply without first seeing the
    // exact release tag and file list the install will target.
    if (m_approvedReleaseTag.isEmpty() || m_approvedFileNames.isEmpty() ||
        m_approvedFileSha256.size() != m_approvedFileNames.size()) {
        m_lblYamlUpdateStatus->setText(QStringLiteral(
            "Please run \"Check for Data Updates\" first to review the files that will be installed."));
        return;
    }

    const auto response = QMessageBox::question(
        this, QStringLiteral("Apply Data Updates"),
        QStringLiteral("This will download and install updated CLASSIC data files. "
                       "The previously installed copy is retained for rollback. Proceed?"),
        QMessageBox::Yes | QMessageBox::No, QMessageBox::Yes);
    if (response != QMessageBox::Yes) {
        return;
    }

    ensureYamlUpdateWorker();
    m_yamlUpdateBusy = true;

    m_btnCheckYamlUpdates->setEnabled(false);
    m_btnApplyYamlUpdates->setEnabled(false);
    m_btnRollbackYamlUpdates->setEnabled(false);
    m_lblYamlUpdateStatus->setText(QStringLiteral("Applying data updates..."));

    const bool enabled = m_chkUpdateCheck && m_chkUpdateCheck->isChecked();

    // Hand the reviewed decision to the worker verbatim. The worker
    // performs the download-and-install loop off the UI thread and reports
    // back via `applyFinished` / `onYamlApplyFinished`. We deliberately do
    // NOT clear `m_approved*` here — clearing happens only when the
    // apply result arrives, so a user cancelling mid-flight (closing the
    // dialog) does not leave the next session with a stale half-decision.
    QMetaObject::invokeMethod(m_yamlUpdateWorker, "doApply", Qt::QueuedConnection,
                              Q_ARG(bool, enabled),
                              Q_ARG(QString, m_approvedReleaseTag),
                              Q_ARG(QStringList, m_approvedFileNames),
                              Q_ARG(QStringList, m_approvedFileSha256));
}

void SettingsDialog::onRollbackYamlUpdate()
{
    const auto response = QMessageBox::question(
        this, QStringLiteral("Rollback Data Update"),
        QStringLiteral("Restore the previously installed copy of each data file? "
                       "The current (newer) copy will be swapped out."),
        QMessageBox::Yes | QMessageBox::No, QMessageBox::No);
    if (response != QMessageBox::Yes) {
        return;
    }

    ensureYamlUpdateWorker();
    m_yamlUpdateBusy = true;

    m_btnRollbackYamlUpdates->setEnabled(false);
    m_lblYamlUpdateStatus->setText(QStringLiteral("Rolling back data updates..."));

    // Both shippable files share the same rollback path; the worker
    // iterates and returns the aggregated outcome on
    // `rollbackFinished` / `onYamlRollbackFinished`. Leave the other
    // buttons alone — rollback is independent of the check/apply
    // decision state.
    const QStringList files{QStringLiteral("CLASSIC Main.yaml"),
                            QStringLiteral("CLASSIC Fallout4.yaml")};
    QMetaObject::invokeMethod(m_yamlUpdateWorker, "doRollback", Qt::QueuedConnection,
                              Q_ARG(QStringList, files));
}

void SettingsDialog::onYamlCheckFinished(YamlCheckResult result)
{
    m_yamlUpdateBusy = false;

    if (result.status == QStringLiteral("disabled")) {
        m_lblYamlUpdateStatus->setText(QStringLiteral(
            "Data update check is disabled. Enable \"Check for Updates on Startup\" in the General tab."));
    } else if (result.status == QStringLiteral("updateAvailable")) {
        const auto count = result.compatibleFileNames.size();
        m_lblYamlUpdateStatus->setText(
            QStringLiteral("Update available: %1 compatible file(s) in release %2. Click \"Apply Data Updates\".")
                .arg(static_cast<qulonglong>(count))
                .arg(result.releaseTag));
        m_btnApplyYamlUpdates->setEnabled(count > 0);
        // Capture the decision atomically with the UI update so Apply
        // cannot see a half-populated state via signal/slot reordering.
        m_approvedReleaseTag = result.releaseTag;
        m_approvedFileNames = result.compatibleFileNames;
        m_approvedFileSha256 = result.compatibleFileSha256;
    } else if (result.status == QStringLiteral("upToDate")) {
        // Distinguish "nothing newer" from "newer data exists but this
        // client cannot consume it" (manifest contains only higher-schema
        // files). The second case needs a client upgrade, not a data
        // refresh, so hiding it behind a generic "up to date" label gives
        // the user the wrong remediation signal.
        if (result.incompatibleFileNames.isEmpty()) {
            m_lblYamlUpdateStatus->setText(
                QStringLiteral("Your data files are up to date (release %1).")
                    .arg(result.releaseTag));
        } else {
            const auto incompatibleCount = result.incompatibleFileNames.size();
            m_lblYamlUpdateStatus->setText(
                QStringLiteral(
                    "Your installed data files are current, but release %1 advertises "
                    "%2 file(s) this CLASSIC build cannot install. Upgrade CLASSIC to "
                    "consume the newer data.")
                    .arg(result.releaseTag)
                    .arg(static_cast<qulonglong>(incompatibleCount)));
        }
    } else if (result.status == QStringLiteral("unknown")) {
        m_lblYamlUpdateStatus->setText(QStringLiteral("Update status unknown: ") + result.detail);
    } else if (result.status == QStringLiteral("error")) {
        m_lblYamlUpdateStatus->setText(QStringLiteral("Data update check failed: ") + result.detail);
    } else {
        m_lblYamlUpdateStatus->setText(
            QStringLiteral("Data update check returned an unrecognised status: %1").arg(result.status));
    }

    m_btnCheckYamlUpdates->setEnabled(true);
}

void SettingsDialog::onYamlApplyFinished(YamlApplyResult result)
{
    m_yamlUpdateBusy = false;

    const auto installed = result.installed;
    const auto failed = result.failed;

    if (installed > 0 && failed == 0) {
        m_lblYamlUpdateStatus->setText(
            QStringLiteral("Installed %1 data file(s). Previous versions are retained for rollback.")
                .arg(static_cast<qulonglong>(installed)));
    } else if (installed > 0 && failed > 0) {
        m_lblYamlUpdateStatus->setText(
            QStringLiteral("Installed %1 file(s); %2 failed. Check logs for details.")
                .arg(static_cast<qulonglong>(installed))
                .arg(static_cast<qulonglong>(failed)));
    } else if (failed > 0) {
        QString detail = result.errorMessage.isEmpty() ? result.firstFailureReason : result.errorMessage;
        m_lblYamlUpdateStatus->setText(
            detail.isEmpty()
                ? QStringLiteral("No data files were installed.")
                : QStringLiteral("No data files were installed: ") + detail);
    } else {
        // Empty report: either nothing compatible to apply, or the bridge
        // surfaced a typed error (update check disabled, decision stale).
        m_lblYamlUpdateStatus->setText(
            result.errorMessage.isEmpty()
                ? QStringLiteral("No compatible data updates to apply.")
                : result.errorMessage);
    }

    m_btnCheckYamlUpdates->setEnabled(true);
    m_btnRollbackYamlUpdates->setEnabled(true);
    // Apply button stays disabled until the user runs Check again.
    //
    // Clearing the approved decision here enforces the "one Check per
    // Apply" invariant: if the user clicks Apply a second time without
    // re-checking, `onApplyYamlUpdates` short-circuits on the empty
    // decision guard rather than re-using whatever was last reviewed.
    m_approvedReleaseTag.clear();
    m_approvedFileNames.clear();
    m_approvedFileSha256.clear();
}

void SettingsDialog::onYamlRollbackFinished(YamlRollbackResult result)
{
    m_yamlUpdateBusy = false;

    QStringList summary;
    if (!result.rolledBack.isEmpty()) {
        summary << QStringLiteral("Rolled back %1 file(s).").arg(result.rolledBack.size());
    }
    if (!result.noPreviousVersion.isEmpty()) {
        summary << QStringLiteral("No previous version to roll back to: ") +
                       result.noPreviousVersion.join(QStringLiteral(", "));
    }
    if (!result.errors.isEmpty()) {
        summary << QStringLiteral("Errors: ") + result.errors.join(QStringLiteral("; "));
    }
    if (summary.isEmpty()) {
        summary << QStringLiteral("Rollback completed with no changes.");
    }
    m_lblYamlUpdateStatus->setText(summary.join(QStringLiteral(" ")));

    m_btnRollbackYamlUpdates->setEnabled(true);
}
