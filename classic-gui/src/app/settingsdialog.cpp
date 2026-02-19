#include "settingsdialog.h"

#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFormLayout>
#include <QGroupBox>
#include <QFileDialog>
#include <QApplication>
#include <QMessageBox>

#include "core/rust_qt_bridge.h"
#include "core/signalhub.h"
#include "widgets/toggleswitch.h"

#include "rust/cxx.h"
#include "classic_cxx_bridge/yaml.h"
#include "classic_cxx_bridge/update.h"
#include "classic_cxx_bridge/registry.h"

// ── Construction ───────────────────────────────────────────────────

SettingsDialog::SettingsDialog(const QString& dataDir,
                               SignalHub* signalHub,
                               QWidget* parent)
    : QDialog(parent)
    , m_dataDir(dataDir)
    , m_signalHub(signalHub)
{
    setWindowTitle(QStringLiteral("Settings"));
    setModal(true);
    setupUi();
    loadSettings();
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
    m_comboGameVersion->addItems({
        QStringLiteral("Auto"),
        QStringLiteral("Original"),
        QStringLiteral("NextGen"),
        QStringLiteral("VR")
    });
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

        auto* helpLabel = new QLabel(
            QStringLiteral("The built-in database is always included.\n"
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

    auto* startupHint = new QLabel(
        QStringLiteral("Startup update checks are configured in the General tab."));
    startupHint->setWordWrap(true);
    layout->addWidget(startupHint);

    {
        auto* row = new QHBoxLayout();
        m_btnCheckNow = new QPushButton(QStringLiteral("Check for Updates Now"));
        connect(m_btnCheckNow, &QPushButton::clicked, this, &SettingsDialog::onCheckForUpdates);
        row->addWidget(m_btnCheckNow);
        row->addStretch();
        layout->addLayout(row);
    }

    m_lblUpdateStatus = new QLabel();
    m_lblUpdateStatus->setWordWrap(true);
    layout->addWidget(m_lblUpdateStatus);

    layout->addStretch();
    tabs->addTab(tab, QStringLiteral("Updates"));
}

// ── Settings persistence ───────────────────────────────────────────

void SettingsDialog::loadSettings()
{
    if (m_dataDir.isEmpty()) return;

    QString settingsPath = m_dataDir + QStringLiteral("/CLASSIC Settings.yaml");
    try {
        auto ops = classic::yaml::yaml_ops_new();
        classic::yaml::yaml_ops_load_file(*ops, std::string(settingsPath.toUtf8().constData()));

        // General - Game Version
        auto gameVersion = classic::yaml::yaml_ops_get_string(
            *ops, "CLASSIC_Settings.Game Version", "auto");
        QString gv = classic::toQString(gameVersion);
        if (gv == QStringLiteral("Original")) m_comboGameVersion->setCurrentIndex(1);
        else if (gv == QStringLiteral("NextGen")) m_comboGameVersion->setCurrentIndex(2);
        else if (gv == QStringLiteral("VR")) m_comboGameVersion->setCurrentIndex(3);
        else m_comboGameVersion->setCurrentIndex(0); // Auto

        // Scanning booleans
        auto getBool = [&](const char* key) -> bool {
            auto val = classic::yaml::yaml_ops_get_setting_value(*ops, key);
            return val.value_type == "bool" && val.value == "true";
        };

        m_chkFcxMode->setChecked(getBool("CLASSIC_Settings.FCX Mode"));
        m_chkSimplifyLogs->setChecked(getBool("CLASSIC_Settings.Simplify Logs"));
        m_chkShowFormIdValues->setChecked(getBool("CLASSIC_Settings.Show FormID Values"));
        m_chkMoveUnsolvedLogs->setChecked(getBool("CLASSIC_Settings.Move Unsolved Logs"));
        m_chkAutoSwitchAfterScan->setChecked(getBool("CLASSIC_Settings.Auto Switch After Scan"));

        // Max Concurrent Scans
        auto maxScans = classic::yaml::yaml_ops_get_setting_value(
            *ops, "CLASSIC_Settings.Max Concurrent Scans");
        if (maxScans.value_type == "integer") {
            bool ok = false;
            int val = QString::fromStdString(std::string(maxScans.value)).toInt(&ok);
            if (ok) m_spinMaxConcurrentScans->setValue(val);
        }

        // Paths - INI Folder
        auto iniFolder = classic::yaml::yaml_ops_get_string(
            *ops, "CLASSIC_Settings.INI Folder Path", "");
        if (!iniFolder.empty()) {
            m_editIniFolder->setText(classic::toQString(iniFolder));
        }

        // FormID Databases (game-specific key)
        auto game = classic::registry::registry_get_game();
        std::string dbKey = "CLASSIC_Settings.FormID Databases." + std::string(game);
        auto dbs = classic::yaml::yaml_ops_get_vec(*ops, dbKey);
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
    if (m_dataDir.isEmpty()) return;

    QString settingsPath = m_dataDir + QStringLiteral("/CLASSIC Settings.yaml");
    try {
        auto ops = classic::yaml::yaml_ops_new();
        classic::yaml::yaml_ops_load_file(*ops, std::string(settingsPath.toUtf8().constData()));

        // General - Game Version
        static const char* gameVersionStrings[] = {"auto", "Original", "NextGen", "VR"};
        int idx = m_comboGameVersion->currentIndex();
        if (idx >= 0 && idx <= 3) {
            classic::yaml::yaml_ops_set_string_setting(
                *ops, "CLASSIC_Settings.Game Version", gameVersionStrings[idx]);
        }

        // Scanning booleans
        classic::yaml::yaml_ops_set_bool_setting(
            *ops, "CLASSIC_Settings.FCX Mode", m_chkFcxMode->isChecked());
        classic::yaml::yaml_ops_set_bool_setting(
            *ops, "CLASSIC_Settings.Simplify Logs", m_chkSimplifyLogs->isChecked());
        classic::yaml::yaml_ops_set_bool_setting(
            *ops, "CLASSIC_Settings.Show FormID Values", m_chkShowFormIdValues->isChecked());
        classic::yaml::yaml_ops_set_bool_setting(
            *ops, "CLASSIC_Settings.Move Unsolved Logs", m_chkMoveUnsolvedLogs->isChecked());
        classic::yaml::yaml_ops_set_bool_setting(
            *ops, "CLASSIC_Settings.Auto Switch After Scan", m_chkAutoSwitchAfterScan->isChecked());

        // Max Concurrent Scans
        classic::yaml::yaml_ops_set_integer_setting(
            *ops, "CLASSIC_Settings.Max Concurrent Scans",
            static_cast<int64_t>(m_spinMaxConcurrentScans->value()));

        // Paths - INI Folder
        auto iniText = m_editIniFolder->text();
        classic::yaml::yaml_ops_set_string_setting(
            *ops, "CLASSIC_Settings.INI Folder Path",
            std::string(iniText.toUtf8().constData()));

        // FormID Databases (game-specific key)
        auto game = classic::registry::registry_get_game();
        std::string dbKey = "CLASSIC_Settings.FormID Databases." + std::string(game);
        rust::Vec<rust::String> dbVec;
        for (int i = 0; i < m_listFormIdDbs->count(); ++i) {
            auto text = m_listFormIdDbs->item(i)->text();
            dbVec.push_back(rust::String(std::string(text.toUtf8().constData())));
        }
        classic::yaml::yaml_ops_set_vec_setting(*ops, dbKey, std::move(dbVec));

        // Updates
        classic::yaml::yaml_ops_set_bool_setting(
            *ops, "CLASSIC_Settings.Update Check", m_chkUpdateCheck->isChecked());

        // Save to disk
        classic::yaml::yaml_ops_save_file(*ops, std::string(settingsPath.toUtf8().constData()));

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
    auto result = QMessageBox::question(
        this,
        QStringLiteral("Reset to Defaults"),
        QStringLiteral("Are you sure you want to reset all settings to their defaults?"),
        QMessageBox::Yes | QMessageBox::No,
        QMessageBox::No);

    if (result != QMessageBox::Yes) return;

    // Reset widgets to default values (no YAML write until OK)
    m_comboGameVersion->setCurrentIndex(0);  // Auto
    m_chkFcxMode->setChecked(false);
    m_chkSimplifyLogs->setChecked(false);
    m_chkShowFormIdValues->setChecked(false);
    m_chkMoveUnsolvedLogs->setChecked(false);
    m_chkAutoSwitchAfterScan->setChecked(true);  // default is true
    m_spinMaxConcurrentScans->setValue(0);
    m_editIniFolder->clear();
    m_listFormIdDbs->clear();
    m_chkUpdateCheck->setChecked(true);  // default is true
    m_lblUpdateStatus->clear();
}

// ── Slot implementations ───────────────────────────────────────────

void SettingsDialog::onBrowseIniFolder()
{
    QString dir = QFileDialog::getExistingDirectory(
        this,
        QStringLiteral("Select INI Folder"),
        m_editIniFolder->text());
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
    QString file = QFileDialog::getOpenFileName(
        this,
        QStringLiteral("Select FormID Database"),
        QString(),
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
        auto result = classic::update::github_check_for_updates(
            "evildarkarchon", "CLASSIC-Fallout4", classic::toRustString(currentVersion));

        if (!result.error_message.empty()) {
            m_lblUpdateStatus->setText(
                QStringLiteral("Error: ") + classic::toQString(result.error_message));
        } else if (result.has_update) {
            m_lblUpdateStatus->setText(
                QStringLiteral("Update available: v") + classic::toQString(result.latest_version));
        } else {
            m_lblUpdateStatus->setText(QStringLiteral("You are up to date."));
        }
    } catch (const std::exception& e) {
        m_lblUpdateStatus->setText(
            QStringLiteral("Update check failed: ") + QString::fromUtf8(e.what()));
    } catch (...) {
        m_lblUpdateStatus->setText(QStringLiteral("Update check failed: unknown error"));
    }

    m_btnCheckNow->setEnabled(true);
}
